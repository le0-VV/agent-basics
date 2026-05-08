from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "agent_basics_ov.py"

spec = importlib.util.spec_from_file_location("agent_basics_ov", HELPER)
assert spec and spec.loader
agent_basics_ov = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_basics_ov)


class SecurityMcpOpenVikingAttackTest(unittest.TestCase):
    def test_mcp_rejects_repo_less_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            attacker = Path(tmp) / "attacker-controlled"
            repo.mkdir()
            (repo / ".git").mkdir()
            attacker.mkdir()

            with self.assertRaises(agent_basics_ov.McpError) as error:
                agent_basics_ov.mcp_call_tool(repo, "status", {"cwd": str(attacker), "online": False})

        self.assertEqual(error.exception.code, agent_basics_ov.MCP_ERROR_INVALID_PARAMS)
        self.assertIn("not inside a git or agent-basics repository", error.exception.message)

    def test_mcp_rejects_malformed_json_rpc_argument_types(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()

            responses = agent_basics_ov.mcp_handle_message(
                repo,
                {
                    "jsonrpc": "2.0",
                    "id": 7,
                    "method": "tools/call",
                    "params": {"name": "status", "arguments": {"cwd": ["not", "a", "string"]}},
                },
            )

        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0]["error"]["code"], agent_basics_ov.MCP_ERROR_INVALID_PARAMS)
        self.assertIn("cwd", responses[0]["error"]["message"])

    def test_viking_uri_namespace_escape_attempts_are_rejected_before_subprocess(self) -> None:
        commands: list[list[str]] = []
        original_find_ov_bin = agent_basics_ov.find_ov_bin
        original_run_command = agent_basics_ov.run_command

        def fake_run_command(command: list[str], timeout: float | None = 30) -> dict[str, object]:
            commands.append(command)
            return {"ok": True, "command": command, "returncode": 0, "stdout": "{}", "stderr": ""}

        try:
            agent_basics_ov.find_ov_bin = lambda: Path("/tmp/ov")
            agent_basics_ov.run_command = fake_run_command
            payload_dotdot = agent_basics_ov.ov_read_payload(
                Path("/tmp/agent-basics"),
                uri="viking://resources/projects/agent-basics/../other-repo/secret.md",
            )
            payload_encoded = agent_basics_ov.ov_read_payload(
                Path("/tmp/agent-basics"),
                uri="viking://resources/projects/agent-basics/%2e%2e/other-repo/secret.md",
            )
        finally:
            agent_basics_ov.find_ov_bin = original_find_ov_bin
            agent_basics_ov.run_command = original_run_command

        self.assertFalse(payload_dotdot["ok"])
        self.assertFalse(payload_encoded["ok"])
        self.assertEqual(commands, [])

    def test_add_resource_rejects_external_files_and_symlink_escapes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            secret = root / "secret.md"
            secret.write_text("do not ingest\n", encoding="utf-8")
            external_payload = agent_basics_ov.ov_add_resource_payload(
                repo,
                source=str(secret),
                dry_run=True,
            )

            symlink_payload = None
            linked = repo / "linked-secret.md"
            try:
                linked.symlink_to(secret)
                symlink_payload = agent_basics_ov.ov_add_resource_payload(
                    repo,
                    source="linked-secret.md",
                    dry_run=True,
                )
            except OSError:
                symlink_payload = {"ok": False, "error": "symlink setup unavailable"}

        self.assertFalse(external_payload["ok"])
        self.assertIn("inside the repository", external_payload["error"])
        self.assertFalse(symlink_payload["ok"])
        self.assertIn("inside the repository", symlink_payload["error"])

    def test_add_skill_rejects_existing_external_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            skill = root / "SKILL.md"
            skill.write_text("# External skill\n", encoding="utf-8")

            payload = agent_basics_ov.ov_add_skill_payload(repo, data=str(skill), dry_run=True)

        self.assertFalse(payload["ok"])
        self.assertIn("inside the repository", payload["error"])

    def test_native_import_inventory_ignores_symlink_escapes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            memory_dir = repo / ".agents" / "memory" / "resources"
            memory_dir.mkdir(parents=True)
            inside = memory_dir / "inside.md"
            inside.write_text("# inside\n", encoding="utf-8")
            secret = root / "secret.md"
            secret.write_text("# outside\n", encoding="utf-8")
            linked = memory_dir / "linked-secret.md"
            try:
                linked.symlink_to(secret)
            except OSError:
                self.skipTest("symlink setup unavailable")

            files = agent_basics_ov.ov_native_import_files(repo)

        self.assertIn(inside, files["resources"])
        self.assertNotIn(linked, files["resources"])

    def test_status_redacts_api_keys_from_repo_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            config_dir = repo / ".agents" / "openviking"
            config_dir.mkdir(parents=True)
            (repo / ".git").mkdir()
            (config_dir / "ov.conf").write_text(
                json.dumps(
                    {
                        "embedding": {"dense": {"api_key": "sk-secret-embedding"}},
                        "vlm": {"api_key": "sk-secret-vlm"},
                    }
                ),
                encoding="utf-8",
            )
            (config_dir / "ovcli.conf").write_text(json.dumps({"url": "http://127.0.0.1:1933"}), encoding="utf-8")
            original_find_ov_bin = agent_basics_ov.find_ov_bin
            try:
                agent_basics_ov.find_ov_bin = lambda: None
                payload = agent_basics_ov.ov_status_payload(repo, online=False)
            finally:
                agent_basics_ov.find_ov_bin = original_find_ov_bin

        serialized = json.dumps(payload)
        self.assertNotIn("sk-secret", serialized)
        self.assertEqual(payload["openviking"]["config"]["embedding"]["dense"]["api_key"], "<redacted>")
        self.assertEqual(payload["openviking"]["config"]["vlm"]["api_key"], "<redacted>")

    def test_write_default_config_output_redacts_api_key_but_file_keeps_secret(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            home = repo / ".agents" / "openviking"
            output = io.StringIO()
            with redirect_stdout(output):
                result = agent_basics_ov.command_ov_write_default_config(
                    SimpleNamespace(
                        repo=str(repo),
                        config=None,
                        cli_config=None,
                        home=str(home),
                        provider="custom",
                        base_url="http://127.0.0.1:18080",
                        provider_base=None,
                        api_key="sk-write-secret",
                        chat_model="chat",
                        embedding_model="embedding",
                        embedding_dimension=768,
                        vlm_timeout=86400,
                        server_url="http://127.0.0.1:1933",
                        cli_timeout=86400,
                        force=False,
                    )
                )

            stdout_payload = json.loads(output.getvalue())
            file_payload = json.loads((home / "ov.conf").read_text(encoding="utf-8"))

        self.assertEqual(result, 0)
        self.assertNotIn("sk-write-secret", output.getvalue())
        self.assertEqual(stdout_payload["config"]["vlm"]["api_key"], "<redacted>")
        self.assertEqual(stdout_payload["config"]["embedding"]["max_input_tokens"], 2048)
        self.assertEqual(file_payload["vlm"]["api_key"], "sk-write-secret")

    def test_record_shell_metacharacters_and_oversized_titles_stay_in_bounded_uri_segment(self) -> None:
        title = "$(touch /tmp/pwned); `whoami`; " + ("A" * 500)

        payload = agent_basics_ov.ov_record_payload(
            Path("/tmp/Agent Basics"),
            category="preferences",
            title=title,
            content="Keep shell metacharacters as content, never as command syntax.",
            dry_run=True,
        )

        target_name = payload["target"].rsplit("/", 1)[-1]
        self.assertTrue(payload["ok"])
        self.assertLessEqual(len(target_name), len("1777777777-") + 96 + len(".md"))
        self.assertNotIn("$", target_name)
        self.assertNotIn("`", target_name)
        self.assertNotIn(";", target_name)

    def test_stale_hook_lock_with_dead_pid_is_recovered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            lock = repo / ".agents" / "openviking" / "locks" / "ingest.lock"
            lock.mkdir(parents=True)
            (lock / "owner.json").write_text(
                json.dumps({"pid": 999999999, "token": "stale", "event": "pre-commit"}),
                encoding="utf-8",
            )

            payload = agent_basics_ov.ov_acquire_hook_ingest_lock(repo, event="pre-commit")

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["recovered_stale_lock"])
        self.assertFalse(payload["locked"])

    def test_install_hooks_does_not_trust_spoofed_gitdir_file_when_git_rejects_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            outside_git = root / "outside.git"
            repo.mkdir()
            outside_git.mkdir()
            (repo / ".git").write_text(f"gitdir: {outside_git}\n", encoding="utf-8")
            original_run_command = agent_basics_ov.run_command

            def fake_run_command(command: list[str], timeout: float | None = 30) -> dict[str, object]:
                return {
                    "ok": False,
                    "command": command,
                    "returncode": 128,
                    "stdout": "",
                    "stderr": "fatal: not a git repository",
                }

            try:
                agent_basics_ov.run_command = fake_run_command
                payload = agent_basics_ov.ov_install_hooks_payload(repo)
            finally:
                agent_basics_ov.run_command = original_run_command

        self.assertFalse(payload["ok"])
        self.assertFalse((outside_git / "hooks").exists())
        self.assertIn("does not have a .git directory", payload["error"])


if __name__ == "__main__":
    unittest.main()
