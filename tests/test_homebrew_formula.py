from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORMULA = ROOT / "Formula" / "agent-basics.rb"


class HomebrewFormulaTest(unittest.TestCase):
    def test_post_install_bootstraps_openviking(self) -> None:
        text = FORMULA.read_text(encoding="utf-8")

        self.assertIn("def post_install", text)
        self.assertIn('depends_on "uv"', text)
        self.assertNotIn('depends_on "ollama"', text)
        self.assertIn('"ov", "bootstrap-system"', text)
        self.assertIn('"--service-best-effort"', text)
        self.assertIn('"--runtime", "mlx"', text)
        self.assertIn('"--runtime-best-effort"', text)
        self.assertIn('bin/"agent-basics-mlx"', text)


if __name__ == "__main__":
    unittest.main()
