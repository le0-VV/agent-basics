from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEMORY_CLI = ROOT / ".agents" / "memory" / "rag" / "agent-memory.py"


class AgentMemoryRecordTest(unittest.TestCase):
    def test_decision_record_renders_structured_sections_and_preserves_index_spacing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            memory_root = repo / ".agents" / "memory"
            memory_root.mkdir(parents=True)
            (memory_root / "INDEX.md").write_text(
                """# Memory Index

## Decisions

- None yet.

## Facts

- None yet.
""",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(MEMORY_CLI),
                    "record",
                    "decision",
                    "Use Rust binary",
                    "--content",
                    "Use Rust as the distributed entrypoint.",
                    "--rationale",
                    "It gives agent-basics one installable command.",
                    "--consequences",
                    "Homebrew builds with Cargo.",
                    "--related",
                    "memory/decisions/repo-local-memory-rag.md",
                    "--no-rebuild",
                ],
                cwd=repo,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            decision_files = sorted((memory_root / "memory" / "decisions").glob("*.md"))
            self.assertEqual(len(decision_files), 1)
            decision_text = decision_files[0].read_text(encoding="utf-8")
            self.assertIn("## Decision\n\nUse Rust as the distributed entrypoint.", decision_text)
            self.assertIn("## Rationale\n\nIt gives agent-basics one installable command.", decision_text)
            self.assertIn("## Consequences\n\nHomebrew builds with Cargo.", decision_text)
            self.assertIn("## Related\n\n- memory/decisions/repo-local-memory-rag.md", decision_text)
            self.assertFalse(decision_text.endswith("\n\n"))

            index_text = (memory_root / "INDEX.md").read_text(encoding="utf-8")
            self.assertIn("- [Use Rust binary](memory/decisions/", index_text)
            self.assertIn(".md)\n\n## Facts", index_text)
            self.assertFalse(index_text.endswith("\n\n"))


if __name__ == "__main__":
    unittest.main()
