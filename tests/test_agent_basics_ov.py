from __future__ import annotations

import importlib.util
import unittest
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

    def test_lmstudio_default_config_uses_ov_router_schema(self) -> None:
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

        self.assertIn("OpenViking memory routing assistant", operation["llm.prediction.systemPrompt"])
        self.assertEqual(operation["llm.prediction.temperature"], 0)
        self.assertEqual(
            operation["llm.prediction.structured"]["jsonSchema"],
            agent_basics_ov.ROUTER_OUTPUT_SCHEMA,
        )
        self.assertEqual(load["llm.load.numParallelSessions"], 1)
        self.assertEqual(load["llm.load.contextLength"], 131072)
        self.assertEqual(load["llm.load.llama.kCacheQuantizationType"], {"checked": True, "value": "q4_0"})
        self.assertEqual(load["llm.load.llama.vCacheQuantizationType"], {"checked": True, "value": "q4_0"})

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
