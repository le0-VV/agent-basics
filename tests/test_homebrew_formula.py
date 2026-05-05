from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORMULA = ROOT / "Formula" / "agent-basics.rb"


class HomebrewFormulaTest(unittest.TestCase):
    def test_post_install_bootstraps_openviking(self) -> None:
        text = FORMULA.read_text(encoding="utf-8")

        self.assertIn("def post_install", text)
        self.assertIn('"ov", "bootstrap-system"', text)
        self.assertIn('"--service-best-effort"', text)
        self.assertIn('"--lmstudio", "auto"', text)
        self.assertIn('"--lmstudio-best-effort"', text)


if __name__ == "__main__":
    unittest.main()
