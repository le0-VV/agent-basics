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


if __name__ == "__main__":
    unittest.main()
