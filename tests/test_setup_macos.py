from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "setup-macos.sh"


class SetupMacosTest(unittest.TestCase):
    def run_setup(self, repo: Path, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env.update(
            {
                "AGENT_BASICS_OPEN_MERGE_UI": "0",
                "AGENT_BASICS_PROJECT_NAME": "setup-test",
            }
        )
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            ["bash", str(SETUP), str(repo)],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=60,
        )

    def test_fresh_setup_creates_ov_source_store_without_legacy_minirag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.run_setup(repo)

            memory_root = repo / ".agents" / "memory"
            self.assertTrue((memory_root / "SCHEMA.md").is_file())
            self.assertTrue((memory_root / "ADAPTATION.md").is_file())
            self.assertTrue((memory_root / "memories" / "preferences" / ".gitkeep").is_file())
            self.assertTrue((memory_root / "resources" / "sources" / ".gitkeep").is_file())
            self.assertTrue((repo / ".agents" / "openviking" / "repo.json").is_file())
            self.assertTrue((repo / ".agents" / "backups").is_dir())
            self.assertTrue((repo / ".agents" / "merge-sessions").is_dir())

            self.assertFalse((memory_root / "memory").exists())
            self.assertFalse((memory_root / "documentations").exists())
            self.assertFalse((memory_root / "templates").exists())
            self.assertFalse((memory_root / "rag").exists())

    def test_setup_snapshots_existing_legacy_memory_without_generated_rag_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            legacy_fact = repo / ".agents" / "memory" / "memory" / "facts" / "old.md"
            legacy_fact.parent.mkdir(parents=True)
            legacy_fact.write_text("# Old fact\n", encoding="utf-8")
            rag_dir = repo / ".agents" / "memory" / "rag"
            rag_dir.mkdir(parents=True)
            (rag_dir / "config.json").write_text("{}\n", encoding="utf-8")
            (rag_dir / "index.sqlite").write_text("generated cache\n", encoding="utf-8")

            self.run_setup(repo)

            snapshots = sorted((repo / ".agents" / "openviking" / "legacy-memory").iterdir())
            self.assertEqual(len(snapshots), 1)
            snapshot = snapshots[0]
            self.assertTrue((snapshot / "memory" / "facts" / "old.md").is_file())
            self.assertTrue((snapshot / "rag" / "config.json").is_file())
            self.assertFalse((snapshot / "rag" / "index.sqlite").exists())


if __name__ == "__main__":
    unittest.main()
