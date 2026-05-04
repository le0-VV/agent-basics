from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DISPATCHER = ROOT / "agent-basics"


class AgentBasicsDispatcherTest(unittest.TestCase):
    def test_ov_doctor_uses_openviking_helper(self) -> None:
        completed = subprocess.run(
            [str(DISPATCHER), "ov", "doctor"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertIn(completed.returncode, {0, 1})
        self.assertIn("openviking", completed.stdout.lower())
        self.assertNotIn("not implemented", completed.stderr.lower())

    def test_root_doctor_uses_openviking_helper(self) -> None:
        completed = subprocess.run(
            [str(DISPATCHER), "doctor"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertIn(completed.returncode, {0, 1})
        self.assertIn("repo_scoped_gateway", completed.stdout)
        self.assertNotIn("memory layout", completed.stdout.lower())

    def test_lmstudio_plan_is_available_without_lms_cli(self) -> None:
        completed = subprocess.run(
            [str(DISPATCHER), "lmstudio", "plan"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertIn(completed.returncode, {0, 1})
        self.assertIn("google/gemma-4-e2b", completed.stdout)
        self.assertIn("load_request", completed.stdout)
        self.assertIn("persistent_default_config", completed.stdout)

    def test_mcp_uses_openviking_gateway(self) -> None:
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-11-25"},
        }
        completed = subprocess.run(
            [str(DISPATCHER), "mcp"],
            input=json.dumps(request) + "\n",
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )

        response = json.loads(completed.stdout)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(response["result"]["serverInfo"]["name"], "agent-basics-openviking")
        self.assertIn("OpenViking", response["result"]["serverInfo"]["title"])


if __name__ == "__main__":
    unittest.main()
