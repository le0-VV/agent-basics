from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "scripts" / "agent_basics_mlx_server.py"


class _BaseModel:
    def __init__(self, **kwargs: object) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

    def model_dump(self) -> dict[str, object]:
        return dict(self.__dict__)


def _field(*, default: object = None, default_factory: object = None) -> object:
    if callable(default_factory):
        return default_factory()
    return default


def _load_server_module() -> types.ModuleType:
    fastapi = types.ModuleType("fastapi")
    fastapi.FastAPI = object
    fastapi.HTTPException = Exception
    responses = types.ModuleType("fastapi.responses")
    responses.JSONResponse = dict
    pydantic = types.ModuleType("pydantic")
    pydantic.BaseModel = _BaseModel
    pydantic.Field = _field

    previous = {name: sys.modules.get(name) for name in ["fastapi", "fastapi.responses", "pydantic"]}
    sys.modules["fastapi"] = fastapi
    sys.modules["fastapi.responses"] = responses
    sys.modules["pydantic"] = pydantic
    try:
        spec = importlib.util.spec_from_file_location("agent_basics_mlx_server_test", SERVER)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for name, value in previous.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


class AgentBasicsMlxServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = _load_server_module()

    def test_response_format_instruction_describes_json_schema(self) -> None:
        instruction = self.server.response_format_instruction(
            {
                "type": "json_schema",
                "json_schema": {
                    "name": "route",
                    "schema": {
                        "type": "object",
                        "required": ["ok"],
                        "properties": {"ok": {"type": "boolean"}},
                    },
                },
            }
        )

        self.assertIn("Return only valid JSON", instruction)
        self.assertIn('"required":["ok"]', instruction)

    def test_normalize_response_text_strips_json_fences(self) -> None:
        text = '```json\n{"ok":true,"runtime":"mlx"}\n```'

        self.assertEqual(
            self.server.normalize_response_text(text, {"type": "json_object"}),
            '{"ok":true,"runtime":"mlx"}',
        )

    def test_normalize_response_text_extracts_json_from_prose(self) -> None:
        text = 'Sure:\n{"ok":true,"items":[{"name":"mlx"}]}\nDone.'

        self.assertEqual(
            self.server.normalize_response_text(text, {"type": "json_schema", "json_schema": {}}),
            '{"ok":true,"items":[{"name":"mlx"}]}',
        )

    def test_normalize_response_text_ignores_unstructured_requests(self) -> None:
        text = '```json\n{"ok":true}\n```'

        self.assertEqual(self.server.normalize_response_text(text, None), text)

    def test_routes_refresh_idle_timer_after_slow_inference(self) -> None:
        source = SERVER.read_text(encoding="utf-8")

        self.assertIn("data = vectors.tolist()\n                state.touch()", source)
        self.assertIn("text = normalize_response_text(text, request.response_format)\n                state.touch()", source)

    def test_routes_clear_runtime_cache_after_inference(self) -> None:
        source = SERVER.read_text(encoding="utf-8")

        self.assertIn("def clear_runtime_cache(self) -> None:", source)
        self.assertEqual(source.count("finally:\n                state.clear_runtime_cache()"), 2)

    def test_generation_disables_padding_for_single_prompt_requests(self) -> None:
        source = SERVER.read_text(encoding="utf-8")

        self.assertIn('"padding": False', source)

    def test_startup_preloads_models_and_checks_router_schema(self) -> None:
        source = SERVER.read_text(encoding="utf-8")

        self.assertIn("def router_response_format() -> dict[str, Any]:", source)
        self.assertIn("def startup_router_prompt(response_format: dict[str, Any]) -> str:", source)
        self.assertIn("def validate_router_payload(payload: Any, *, require_items: bool)", source)
        self.assertIn("def preload(self, mode: str, structured_output_check: str)", source)
        self.assertIn("target=lambda: state.run_mlx(lambda: state.preload(", source)
        self.assertIn("--preload-models", source)
        self.assertIn("--startup-structured-output-check", source)

    def test_startup_router_prompt_requires_top_level_items_object(self) -> None:
        prompt = self.server.startup_router_prompt(self.server.router_response_format())

        self.assertIn("Return exactly one item inside a top-level JSON object", prompt)
        self.assertIn("input_id: startup_check", prompt)

    def test_validate_router_payload_rejects_top_level_array(self) -> None:
        ok, error, count = self.server.validate_router_payload([], require_items=True)

        self.assertFalse(ok)
        self.assertEqual(error, "top-level JSON is not an object")
        self.assertEqual(count, 0)

    def test_validate_router_payload_accepts_complete_router_item(self) -> None:
        item = {
            "input_id": "startup_check",
            "action": "create",
            "record_kind": "memory",
            "ov_category": "preferences",
            "facet": "runtime",
            "title": "Preload MLX runtime at login",
            "abstract": "The user wants the MLX runtime loaded at macOS login.",
            "overview": "agent-basics should keep the configured chat and embedding models warm.",
            "content": "The MLX runtime should preload both models and use router structured output checks.",
            "tags": ["agent-basics", "mlx"],
            "certainty": "high",
            "requires_human_review": False,
            "reason": "The candidate states a durable user preference.",
        }

        ok, error, count = self.server.validate_router_payload({"items": [item]}, require_items=True)

        self.assertTrue(ok)
        self.assertIsNone(error)
        self.assertEqual(count, 1)

    def test_mlx_routes_run_on_event_loop_thread(self) -> None:
        source = SERVER.read_text(encoding="utf-8")

        self.assertIn("async def embeddings(request: EmbeddingRequest)", source)
        self.assertIn("async def chat_completions(request: ChatCompletionRequest)", source)
        self.assertIn("async def run_mlx_async(state: RuntimeState, func: Callable[[], Any])", source)
        self.assertIn("data = await run_mlx_async(state, compute_embeddings)", source)
        self.assertIn("text = await run_mlx_async(state, compute_completion)", source)

    def test_runtime_state_runs_submitted_mlx_work_on_one_worker_thread(self) -> None:
        state = self.server.RuntimeState("chat", "embedding", 0)
        try:
            first = state.run_mlx(threading.get_ident)
            second = state.run_mlx(threading.get_ident)

            self.assertEqual(first, second)
            self.assertNotEqual(first, threading.get_ident())
            self.assertEqual(first, state.worker_thread_id)
        finally:
            state.close()

    def test_cached_hf_snapshot_path_prefers_hf_home_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hf_home = Path(tmp)
            repo = hf_home / "hub" / "models--owner--model"
            snapshot = repo / "snapshots" / "abc123"
            snapshot.mkdir(parents=True)
            (repo / "refs").mkdir()
            (repo / "refs" / "main").write_text("abc123\n", encoding="utf-8")

            with mock.patch.dict(os.environ, {"HF_HOME": str(hf_home)}, clear=False):
                self.assertEqual(self.server.cached_hf_snapshot_path("owner/model"), str(snapshot))


if __name__ == "__main__":
    unittest.main()
