from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DISPATCHER = ROOT / "agent-basics"


class AgentBasicsDispatcherTest(unittest.TestCase):
    def test_ov_command_fails_fast_until_gateway_exists(self) -> None:
        completed = subprocess.run(
            [str(DISPATCHER), "ov", "doctor"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(completed.returncode, 2)
        self.assertIn("OpenViking gateway", completed.stderr)
        self.assertIn("not implemented", completed.stderr)


if __name__ == "__main__":
    unittest.main()
