from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DISPATCHER = ROOT / "agent-basics"


class AgentBasicsDispatcherTest(unittest.TestCase):
    def run_dispatcher(
        self,
        args: list[str],
        *,
        cwd: Path = ROOT,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        completed_env = dict(os.environ)
        if env:
            completed_env.update(env)
        return subprocess.run(
            [str(DISPATCHER), *args],
            cwd=cwd,
            env=completed_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

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

    def test_provider_specific_runtime_commands_are_not_public(self) -> None:
        completed = subprocess.run(
            [str(DISPATCHER), "lmstudio", "plan"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(completed.returncode, 2)
        self.assertIn("unknown command: lmstudio", completed.stderr)

        completed = subprocess.run(
            [str(DISPATCHER), "ollama", "status"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(completed.returncode, 2)
        self.assertIn("unknown command: ollama", completed.stderr)

    def test_public_help_centers_openviking_and_mlx(self) -> None:
        completed = self.run_dispatcher(["--help"])

        self.assertEqual(completed.returncode, 0)
        self.assertIn("agent-basics [--repo DIR] mcp", completed.stdout)
        self.assertIn("agent-basics [--repo DIR] ov", completed.stdout)
        self.assertIn("agent-basics [--repo DIR] mlx", completed.stdout)
        self.assertNotIn("memory <validate", completed.stdout)
        self.assertNotIn("validate|rebuild|search|record", completed.stdout)
        self.assertNotIn("--embedding-mode", completed.stdout)

    def test_mcp_help_explains_directory_agnostic_setup(self) -> None:
        completed = self.run_dispatcher(["mcp", "--help"])

        self.assertEqual(completed.returncode, 0)
        self.assertIn("agent-basics mcp", completed.stdout)
        self.assertIn("working directory: optional", completed.stdout)
        self.assertIn("pass `cwd`", completed.stdout)

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

    def test_mcp_tools_prefer_cwd_argument(self) -> None:
        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
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
        status_tool = next(tool for tool in response["result"]["tools"] if tool["name"] == "status")
        properties = status_tool["inputSchema"]["properties"]

        self.assertEqual(completed.returncode, 0)
        self.assertIn("cwd", properties)
        self.assertIn("repo_path", properties)
        self.assertIn("Backward-compatible alias", properties["repo_path"]["description"])

    def test_mcp_status_resolves_cwd_inside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            subdir = repo / "src" / "feature"
            (repo / ".agents").mkdir(parents=True)
            subdir.mkdir(parents=True)
            (repo / ".agents" / "config.toml").write_text("version = 1\n", encoding="utf-8")
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "status",
                    "arguments": {"cwd": str(subdir), "online": False},
                },
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
        payload = response["result"]["structuredContent"]
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(payload["repo"], str(repo.resolve()))

    def test_verify_runs_available_lightweight_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            tests_dir = repo / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_smoke.py").write_text(
                "import unittest\n\n"
                "class SmokeTest(unittest.TestCase):\n"
                "    def test_smoke(self):\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            (repo / "setup-macos.sh").write_text("#!/usr/bin/env bash\ntrue\n", encoding="utf-8")

            completed = self.run_dispatcher(["--repo", str(repo), "verify"])

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("[PASS] unit tests", completed.stdout)
        self.assertIn("[PASS] setup-macos.sh syntax", completed.stdout)
        self.assertIn("[SKIP] cargo test", completed.stdout)

    def test_verify_summarizes_openviking_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            fake_dispatcher = repo / "agent-basics"
            fake_dispatcher.write_text(
                "#!/usr/bin/env python3\n"
                "import json\n"
                "import sys\n"
                "if sys.argv[1:] != ['ov', 'status', '--offline']:\n"
                "    raise SystemExit(2)\n"
                "print(json.dumps({\n"
                "    'ok': True,\n"
                f"    'repo': {str(repo)!r},\n"
                "    'openviking': {\n"
                "        'workspace': '.agents/openviking/workspace',\n"
                "        'server_url': 'http://127.0.0.1:1933',\n"
                "    },\n"
                "    'source_store': {'canonical': {\n"
                "        'counts': {'memories': 2, 'resources': 1, 'skills': 0},\n"
                "        'stale_count': 0,\n"
                "        'state': {'imports': {'too': 'large'}},\n"
                "    }},\n"
                "}))\n",
                encoding="utf-8",
            )
            fake_dispatcher.chmod(0o755)

            completed = self.run_dispatcher(["--repo", str(repo), "verify"])

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("[PASS] OpenViking offline status", completed.stdout)
        self.assertIn("source_store: 2 memories, 1 resources, 0 skills", completed.stdout)
        self.assertIn("stale_source_files: 0", completed.stdout)
        self.assertNotIn("\"imports\"", completed.stdout)

    def test_commit_validates_message_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            completed = self.run_dispatcher(["--repo", tmp, "commit", "bad message"])

        self.assertEqual(completed.returncode, 2)
        self.assertIn("commit message must match", completed.stderr)

    def test_commit_refuses_when_no_staged_changes(self) -> None:
        if not shutil.which("git"):
            self.skipTest("git is not available")

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            completed = self.run_dispatcher(["--repo", str(repo), "commit", "fix(test): no staged changes"])

        self.assertEqual(completed.returncode, 1)
        self.assertIn("no staged changes", completed.stderr)

    def test_commit_creates_supervised_author_commit(self) -> None:
        if not shutil.which("git"):
            self.skipTest("git is not available")

        global_name = subprocess.run(
            ["git", "config", "--global", "user.name"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        ).stdout.strip()
        global_email = subprocess.run(
            ["git", "config", "--global", "user.email"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        ).stdout.strip()
        if not global_name or not global_email:
            self.skipTest("global git identity is not configured")

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            (repo / "file.txt").write_text("content\n", encoding="utf-8")
            subprocess.run(["git", "add", "file.txt"], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

            completed = self.run_dispatcher(
                ["--repo", str(repo), "commit", "feat(test): commit workflow state"],
                env={
                    "GIT_AUTHOR_NAME": "Wrong Author",
                    "GIT_AUTHOR_EMAIL": "wrong@example.invalid",
                    "GIT_COMMITTER_NAME": "Wrong Committer",
                    "GIT_COMMITTER_EMAIL": "wrong@example.invalid",
                },
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

            log = subprocess.run(
                ["git", "log", "-1", "--format=%an%x00%ae%x00%cn%x00%ce%x00%s"],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            ).stdout.strip()

        author_name, author_email, committer_name, committer_email, subject = log.split("\0")
        supervised_name = f"Coding agent supervised by {global_name}"
        self.assertEqual(author_name, supervised_name)
        self.assertEqual(author_email, global_email)
        self.assertEqual(committer_name, supervised_name)
        self.assertEqual(committer_email, global_email)
        self.assertEqual(subject, "feat(test): commit workflow state")


if __name__ == "__main__":
    unittest.main()
