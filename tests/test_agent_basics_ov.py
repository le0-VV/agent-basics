from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "agent_basics_ov.py"

spec = importlib.util.spec_from_file_location("agent_basics_ov", HELPER)
assert spec and spec.loader
agent_basics_ov = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_basics_ov)


class AgentBasicsOpenVikingHelperTest(unittest.TestCase):
    def test_preingest_splits_and_hints_ownership_statements(self) -> None:
        candidates = agent_basics_ov.preingest_candidates(
            "harness_direction",
            "The user wants agent-basics to be a thin harness layer over OpenViking. "
            "agent-basics owns setup, config, MCP, hooks, migration UX, and run state. "
            "OpenViking owns durable context storage, resources, summaries, vector indexes, and retrieval.",
        )

        self.assertEqual(len(candidates), 3)
        self.assertEqual(candidates[0]["suggested_ov_category"], "preferences")
        self.assertEqual(candidates[1]["suggested_ov_category"], "entities")
        self.assertEqual(candidates[2]["suggested_ov_category"], "entities")

    def test_lmstudio_config_mismatches_only_checks_reported_load_keys(self) -> None:
        mismatches = agent_basics_ov.lmstudio_config_mismatches(
            {
                "context_length": 131072,
                "eval_batch_size": 256,
                "flash_attention": True,
                "offload_kv_cache_to_gpu": True,
                "parallel": 4,
            },
            {
                "model": "google/gemma-4-e2b",
                "context_length": 131072,
                "eval_batch_size": 512,
                "flash_attention": True,
                "offload_kv_cache_to_gpu": True,
                "parallel": 1,
                "llama_k_cache_quantization_type": "q4_0",
            },
        )

        self.assertEqual(mismatches, [{"key": "eval_batch_size", "actual": 256, "desired": 512}])

    def test_lmstudio_default_config_keeps_router_schema_request_time_only(self) -> None:
        config = agent_basics_ov.lmstudio_desired_chat_config(
            cpu_threads=8,
            parallel=1,
            context_length=131072,
            kv_cache_quantization="q4_0",
            gpu_offload_ratio=1.0,
            temperature=0,
        )

        operation = {field["key"]: field["value"] for field in config["operation"]["fields"]}
        load = {field["key"]: field["value"] for field in config["load"]["fields"]}

        self.assertNotIn("llm.prediction.systemPrompt", operation)
        self.assertNotIn("llm.prediction.structured", operation)
        self.assertEqual(operation["llm.prediction.temperature"], 0)
        self.assertEqual(load["llm.load.numParallelSessions"], 1)
        self.assertEqual(load["llm.load.contextLength"], 131072)
        self.assertEqual(load["llm.load.llama.kCacheQuantizationType"], {"checked": True, "value": "q4_0"})
        self.assertEqual(load["llm.load.llama.vCacheQuantizationType"], {"checked": True, "value": "q4_0"})

    def test_lmstudio_config_merge_clears_stale_router_defaults(self) -> None:
        existing = {
            "preset": "",
            "operation": {
                "fields": [
                    {"key": "llm.prediction.structured", "value": {"type": "json"}},
                    {"key": "llm.prediction.systemPrompt", "value": "old router prompt"},
                    {"key": "custom.operation", "value": True},
                ]
            },
            "load": {"fields": []},
        }
        desired = {"preset": "", "operation": {"fields": []}, "load": {"fields": []}}

        merged = agent_basics_ov.merge_lmstudio_config(
            existing,
            desired,
            remove_operation_keys=agent_basics_ov.LMSTUDIO_ROUTING_DEFAULT_KEYS,
        )
        operation = {field["key"]: field["value"] for field in merged["operation"]["fields"]}

        self.assertNotIn("llm.prediction.structured", operation)
        self.assertNotIn("llm.prediction.systemPrompt", operation)
        self.assertEqual(operation["custom.operation"], True)

    def test_lmstudio_config_merge_preserves_unrelated_fields(self) -> None:
        existing = {
            "preset": "",
            "operation": {"fields": [{"key": "custom.operation", "value": True}]},
            "load": {
                "fields": [
                    {"key": "llm.load.numParallelSessions", "value": 4},
                    {"key": "custom.load", "value": "preserve"},
                ]
            },
        }
        desired = {
            "preset": "",
            "operation": {"fields": [{"key": "llm.prediction.temperature", "value": 0}]},
            "load": {"fields": [{"key": "llm.load.numParallelSessions", "value": 1}]},
        }

        merged = agent_basics_ov.merge_lmstudio_config(existing, desired)
        operation = {field["key"]: field["value"] for field in merged["operation"]["fields"]}
        load = {field["key"]: field["value"] for field in merged["load"]["fields"]}

        self.assertEqual(operation["custom.operation"], True)
        self.assertEqual(operation["llm.prediction.temperature"], 0)
        self.assertEqual(load["llm.load.numParallelSessions"], 1)
        self.assertEqual(load["custom.load"], "preserve")

    def test_ov_native_import_files_selects_source_store_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            memory_root = repo / ".agents" / "memory"
            (memory_root / "memories" / "preferences").mkdir(parents=True)
            (memory_root / "resources" / "sources").mkdir(parents=True)
            (memory_root / "memory" / "facts").mkdir(parents=True)
            (memory_root / "SCHEMA.md").write_text("# Schema\n", encoding="utf-8")
            (memory_root / "ADAPTATION.md").write_text("# Adapt\n", encoding="utf-8")
            (memory_root / "memories" / "preferences" / "keep.md").write_text("# Keep\n", encoding="utf-8")
            (memory_root / "resources" / "sources" / "docs.md").write_text("# Docs\n", encoding="utf-8")
            (memory_root / "memory" / "facts" / "legacy.md").write_text("# Legacy\n", encoding="utf-8")

            selected = agent_basics_ov.ov_native_import_files(repo)

        self.assertEqual(
            [path.relative_to(repo).as_posix() for path in selected["memories"]],
            [".agents/memory/memories/preferences/keep.md"],
        )
        self.assertEqual(
            [path.relative_to(repo).as_posix() for path in selected["resources"]],
            [
                ".agents/memory/ADAPTATION.md",
                ".agents/memory/SCHEMA.md",
                ".agents/memory/resources/sources/docs.md",
            ],
        )

    def test_ov_mkdir_p_builds_valid_viking_uris(self) -> None:
        commands: list[list[str]] = []

        def fake_run(command: list[str], timeout: float | None = 30) -> dict[str, object]:
            commands.append(command)
            return {"ok": True, "stderr": ""}

        original = agent_basics_ov.run_command
        try:
            agent_basics_ov.run_command = fake_run
            agent_basics_ov.ov_mkdir_p(Path("/tmp/ov"), "viking://resources/projects/agent-basics")
        finally:
            agent_basics_ov.run_command = original

        self.assertEqual(
            [command[2] for command in commands],
            ["viking://resources", "viking://resources/projects", "viking://resources/projects/agent-basics"],
        )

    def test_ov_memory_target_uri_uses_openviking_category_and_project_slug(self) -> None:
        repo = Path("/tmp/Agent Basics")
        path = repo / ".agents" / "memory" / "memories" / "cases" / "example.md"
        target = agent_basics_ov.ov_memory_target_uri(
            "viking://user/default/memories",
            repo,
            path,
            "cases",
        )

        self.assertEqual(
            target,
            "viking://user/default/memories/cases/projects/agent-basics/example.md",
        )

    def test_ov_import_repo_memory_dry_run_writes_native_memory_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "agent-basics"
            memory_path = repo / ".agents" / "memory" / "memories" / "cases" / "case.md"
            memory_path.parent.mkdir(parents=True)
            memory_path.write_text(
                "---\n"
                "record_kind: memory\n"
                "ov_category: cases\n"
                "title: Example case\n"
                "requires_human_review: false\n"
                "---\n"
                "\n"
                "# Example case\n",
                encoding="utf-8",
            )

            original_find_ov_bin = agent_basics_ov.find_ov_bin
            original_run_command = agent_basics_ov.run_command
            try:
                agent_basics_ov.find_ov_bin = lambda: Path("/tmp/ov")
                agent_basics_ov.run_command = lambda command, timeout=30: {"ok": True, "command": command, "stdout": "{}", "stderr": ""}
                output = io.StringIO()
                with redirect_stdout(output):
                    result = agent_basics_ov.command_ov_import_repo_memory(
                        SimpleNamespace(
                            repo=str(repo),
                            target=None,
                            memory_target=agent_basics_ov.DEFAULT_OV_MEMORY_TARGET,
                            timeout=agent_basics_ov.DEFAULT_OV_VLM_TIMEOUT_SECONDS,
                            include_review=False,
                            force=False,
                            dry_run=True,
                            wait=False,
                            wait_memory=False,
                            wait_resources=False,
                            busy_retries=0,
                            busy_delay=0,
                            write=False,
                        )
                    )
            finally:
                agent_basics_ov.find_ov_bin = original_find_ov_bin
                agent_basics_ov.run_command = original_run_command

        payload = json.loads(output.getvalue())
        memory_command = payload["results"][0]["command"]

        self.assertEqual(result, 0)
        self.assertEqual(memory_command[1], "write")
        self.assertIn("viking://user/default/memories/cases/projects/agent-basics/case.md", memory_command)

    def test_ov_existing_content_result_verifies_matching_target(self) -> None:
        original = agent_basics_ov.run_command
        try:
            agent_basics_ov.run_command = lambda command, timeout=30: {
                "ok": True,
                "command": command,
                "returncode": 0,
                "stdout": "hello\n",
                "stderr": "",
            }

            result = agent_basics_ov.ov_existing_content_result(Path("/tmp/ov"), "viking://target", "hello\n")
        finally:
            agent_basics_ov.run_command = original

        assert result is not None
        self.assertTrue(result["ok"])
        self.assertTrue(result["verified_existing"])

    def test_ov_search_payload_scopes_every_category_to_repo(self) -> None:
        commands: list[list[str]] = []

        def fake_run(command: list[str], timeout: float | None = 30) -> dict[str, object]:
            commands.append(command)
            scope = command[command.index("--uri") + 1]
            result = {"memories": [], "resources": [], "skills": [], "total": 0}
            if scope.endswith("/preferences/projects/agent-basics"):
                result["memories"] = [
                    {
                        "context_type": "memory",
                        "uri": "viking://user/default/memories/preferences/projects/agent-basics/example.md",
                        "score": 0.9,
                    }
                ]
                result["total"] = 1
            if scope == "viking://resources/projects/agent-basics":
                result["resources"] = [
                    {
                        "context_type": "resource",
                        "uri": "viking://resources/projects/agent-basics/README.md",
                        "score": 0.8,
                    }
                ]
                result["total"] = 1
            return {
                "ok": True,
                "command": command,
                "returncode": 0,
                "stdout": json.dumps({"ok": True, "result": result}),
                "stderr": "",
                "elapsed_seconds": 0.01,
            }

        original_find_ov_bin = agent_basics_ov.find_ov_bin
        original_run_command = agent_basics_ov.run_command
        try:
            agent_basics_ov.find_ov_bin = lambda: Path("/tmp/ov")
            agent_basics_ov.run_command = fake_run
            payload = agent_basics_ov.ov_search_payload(
                Path("/tmp/agent-basics"),
                query="repo memory",
                limit=5,
            )
        finally:
            agent_basics_ov.find_ov_bin = original_find_ov_bin
            agent_basics_ov.run_command = original_run_command

        scopes = [command[command.index("--uri") + 1] for command in commands]
        self.assertTrue(payload["ok"])
        self.assertIn("viking://resources/projects/agent-basics", scopes)
        self.assertIn("viking://user/default/memories/preferences/projects/agent-basics", scopes)
        self.assertEqual(
            payload["result"]["memories"][0]["uri"],
            "viking://user/default/memories/preferences/projects/agent-basics/example.md",
        )
        self.assertNotIn("stdout", payload["commands"][0])

    def test_ov_read_rejects_global_uri_without_explicit_opt_in(self) -> None:
        payload = agent_basics_ov.ov_read_payload(
            Path("/tmp/agent-basics"),
            uri="viking://resources/projects/other-repo/README.md",
        )

        self.assertFalse(payload["ok"])
        self.assertIn("--allow-global", payload["error"])

    def test_ov_record_dry_run_uses_source_store_and_openviking_project_namespace(self) -> None:
        payload = agent_basics_ov.ov_record_payload(
            Path("/tmp/Agent Basics"),
            category="preferences",
            title="Prefer repo scoped OV writes",
            content="Record through agent-basics so repo source files and OV stay aligned.",
            dry_run=True,
        )

        self.assertTrue(payload["ok"])
        self.assertIn(
            "/.agents/memory/memories/preferences/",
            payload["source_path"],
        )
        self.assertIn(
            "viking://user/default/memories/preferences/projects/agent-basics/",
            payload["target"],
        )

    def test_ov_add_resource_dry_run_defaults_to_repo_resource_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "agent-basics"
            resource = repo / "docs" / "api.md"
            resource.parent.mkdir(parents=True)
            resource.write_text("# API\n", encoding="utf-8")

            payload = agent_basics_ov.ov_add_resource_payload(
                repo,
                source="docs/api.md",
                dry_run=True,
            )

        self.assertTrue(payload["ok"])
        self.assertEqual(
            payload["target"],
            "viking://resources/projects/agent-basics/resources/docs/api.md",
        )

    def test_ov_default_config_uses_positive_vlm_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "ov.conf"
            result = agent_basics_ov.command_ov_write_default_config(
                SimpleNamespace(
                    config=str(config_path),
                    home=str(Path(tmp) / "openviking"),
                    lmstudio_base="http://127.0.0.1:1234",
                    chat_model=agent_basics_ov.DEFAULT_CHAT_MODEL,
                    embedding_model=agent_basics_ov.DEFAULT_EMBEDDING_MODEL,
                    embedding_dimension=768,
                    vlm_timeout=agent_basics_ov.DEFAULT_OV_VLM_TIMEOUT_SECONDS,
                    force=False,
                )
            )
            payload = agent_basics_ov.load_json_file(config_path)

        self.assertEqual(result, 0)
        assert payload is not None
        self.assertGreater(payload["vlm"]["timeout"], 0)

    def test_ov_native_memory_paths_map_to_openviking_categories(self) -> None:
        category, reason, review = agent_basics_ov.legacy_to_ov_category(
            Path(".agents/memory/memories/preferences/example.md"),
            "",
            "The user wants .agents/memory to stay as the OV source store.",
        )
        self.assertEqual(category, "preferences")
        self.assertEqual(reason, "OV-native preference memory")
        self.assertFalse(review)

        category, reason, review = agent_basics_ov.legacy_to_ov_category(
            Path(".agents/memory/resources/sources/example.md"),
            "",
            "https://example.com",
        )
        self.assertEqual(category, "none")
        self.assertEqual(reason, "OV-native resource, not memory")
        self.assertFalse(review)

        category, reason, review = agent_basics_ov.legacy_to_ov_category(
            Path(".agents/memory/imports/legacy-memory.md"),
            "",
            "Raw copied material.",
        )
        self.assertEqual(category, "none")
        self.assertEqual(reason, "copied source material awaiting adaptation")
        self.assertTrue(review)


if __name__ == "__main__":
    unittest.main()
