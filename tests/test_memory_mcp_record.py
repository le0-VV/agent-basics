from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEMORY_MCP = ROOT / ".agents" / "memory" / "rag" / "memory-mcp.py"


class MemoryMcpRecordTest(unittest.TestCase):
    def test_memory_record_defers_rebuild_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            memory_root = repo / ".agents" / "memory"
            (memory_root / "rag").mkdir(parents=True)
            (memory_root / "INDEX.md").write_text(
                """# Memory Index

## Facts

- None yet.
""",
                encoding="utf-8",
            )

            env = dict(os.environ)
            env["AGENT_BASICS_REPO_ROOT"] = str(repo)
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "memory_record",
                    "arguments": {
                        "type": "fact",
                        "title": "Approval-light writes",
                        "content": "MCP records defer rebuilds by default.",
                        "tags": ["memory", "mcp"],
                    },
                },
            }
            completed = subprocess.run(
                [sys.executable, str(MEMORY_MCP)],
                input=json.dumps(request) + "\n",
                cwd=repo,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=30,
            )

            response = json.loads(completed.stdout)
            self.assertNotIn("error", response)
            result_text = response["result"]["content"][0]["text"]
            self.assertIn("Recorded fact:", result_text)
            self.assertNotIn("Rebuilt memory index", result_text)
            self.assertFalse((memory_root / "rag" / "index.sqlite").exists())
            self.assertIn(
                "- [Approval-light writes](memory/facts/",
                (memory_root / "INDEX.md").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
