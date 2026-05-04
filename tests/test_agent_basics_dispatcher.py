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

    def test_run_lifecycle_uses_repo_local_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            started = self.run_dispatcher(
                ["--repo", str(repo), "run", "start", "--task", "Build long horizon workflow"]
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            self.assertIn("Started run:", started.stdout)

            current = repo / ".agents" / "runs" / "current"
            self.assertTrue(current.is_file())
            run_id = current.read_text(encoding="utf-8").strip()
            self.assertRegex(run_id, r"^\d+-build-long-horizon-workflow$")

            run_dir = repo / ".agents" / "runs" / run_id
            state_path = run_dir / "state.json"
            checkpoint_path = run_dir / "CHECKPOINT.md"
            handoff_path = run_dir / "handoff.md"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["task"], "Build long horizon workflow")
            self.assertEqual(state["status"], "active")
            self.assertIsInstance(state["created_at"], int)
            self.assertTrue(checkpoint_path.is_file())
            self.assertTrue(handoff_path.is_file())

            checkpointed = self.run_dispatcher(
                ["--repo", str(repo), "run", "checkpoint", "--message", "first checkpoint"]
            )
            self.assertEqual(checkpointed.returncode, 0, checkpointed.stderr)
            self.assertIn("first checkpoint", checkpoint_path.read_text(encoding="utf-8"))

            handed_off = self.run_dispatcher(
                ["--repo", str(repo), "run", "handoff", "--message", "next worker owns tests"]
            )
            self.assertEqual(handed_off.returncode, 0, handed_off.stderr)
            self.assertIn("next worker owns tests", handoff_path.read_text(encoding="utf-8"))

            status = self.run_dispatcher(["--repo", str(repo), "run", "status"])
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("Status: active", status.stdout)
            self.assertIn("Task: Build long horizon workflow", status.stdout)

            finished = self.run_dispatcher(["--repo", str(repo), "run", "finish", "--message", "done"])
            self.assertEqual(finished.returncode, 0, finished.stderr)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "complete")
            self.assertIsInstance(state["completed_at"], int)
            self.assertIn("Run finished: done", checkpoint_path.read_text(encoding="utf-8"))

    def test_run_status_fails_without_current_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            completed = self.run_dispatcher(["--repo", tmp, "run", "status"])

        self.assertEqual(completed.returncode, 1)
        self.assertIn("no current run", completed.stderr)

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
