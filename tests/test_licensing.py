from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LicensingTest(unittest.TestCase):
    def test_project_license_matches_cargo_metadata(self) -> None:
        cargo = (ROOT / "Cargo.toml").read_text(encoding="utf-8")
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")

        self.assertIn('license = "MIT"', cargo)
        self.assertIn("MIT License", license_text)

    def test_cargo_lock_has_no_third_party_rust_dependencies(self) -> None:
        lock_text = (ROOT / "Cargo.lock").read_text(encoding="utf-8")
        package_names = [
            line.split('"', 2)[1]
            for line in lock_text.splitlines()
            if line.startswith("name = ")
        ]

        self.assertEqual(package_names, ["agent-basics"])

    def test_third_party_notices_cover_runtime_integrations(self) -> None:
        notices = (ROOT / "THIRD-PARTY-NOTICES.md").read_text(encoding="utf-8").lower()

        for token in [
            "openviking",
            "agpl-3.0",
            "mlx",
            "mlx-vlm",
            "mlx-embeddings",
            "gpl-3.0",
            "pyinstaller",
            "ollama",
            "gemma",
            "embeddinggemma",
            "uv",
            "fastapi",
            "sentence-transformers",
            "uvicorn",
        ]:
            with self.subTest(token=token):
                self.assertIn(token, notices)

    def test_licenses_command_prints_project_and_third_party_notices(self) -> None:
        completed = subprocess.run(
            [str(ROOT / "agent-basics"), "licenses"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("MIT License", completed.stdout)
        self.assertIn("Third-Party Notices", completed.stdout)
        self.assertIn("OpenViking", completed.stdout)


if __name__ == "__main__":
    unittest.main()
