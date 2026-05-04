from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
