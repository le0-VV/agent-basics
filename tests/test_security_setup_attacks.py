from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "setup-macos.sh"


class SetupSecurityAttackTest(unittest.TestCase):
    def write_fake_openviking(self, repo: Path) -> Path:
        fake_bin = repo / ".test-openviking" / "ov"
        fake_bin.parent.mkdir(parents=True, exist_ok=True)
        fake_bin.write_text(
            "#!/usr/bin/env sh\n"
            "case \"$1\" in\n"
            "  --help) echo 'fake OpenViking help'; exit 0 ;;\n"
            "  version) echo 'CLI: 0.0.0-security-test'; exit 0 ;;\n"
            "  health) exit 0 ;;\n"
            "  *) exit 0 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        fake_bin.chmod(0o755)
        return fake_bin

    def run_setup(
        self,
        repo: Path,
        extra_env: dict[str, str] | None = None,
        *,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env.update(
            {
                "AGENT_BASICS_CONFIG_HOME": str(repo / ".test-agent-basics-config"),
                "AGENT_BASICS_INSTALL_COMPAT_MEMORY": "0",
                "AGENT_BASICS_OPEN_MERGE_UI": "0",
                "AGENT_BASICS_PROJECT_NAME": "security-test",
                "AGENT_BASICS_TEST_OPENVIKING_BIN": str(self.write_fake_openviking(repo)),
            }
        )
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            ["bash", str(SETUP), str(repo)],
            cwd=ROOT,
            env=env,
            text=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
            timeout=60,
        )

    def assert_rejected_unsafe_path(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsafe managed setup path", result.stderr)

    def test_rejects_symlinked_agents_markdown_without_clobbering_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            outside = root / "outside-agents.md"
            outside.write_text("# Outside\n\nDo not overwrite.\n", encoding="utf-8")
            (repo / "Agents.md").symlink_to(outside)

            result = self.run_setup(repo, {"AGENT_BASICS_CONFLICT_ACTION": "replace"})

            self.assert_rejected_unsafe_path(result)
            self.assertEqual(outside.read_text(encoding="utf-8"), "# Outside\n\nDo not overwrite.\n")

    def test_rejects_symlinked_agents_directory_without_writing_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            outside = root / "outside-agents"
            repo.mkdir()
            outside.mkdir()
            (repo / ".agents").symlink_to(outside, target_is_directory=True)

            result = self.run_setup(repo)

            self.assert_rejected_unsafe_path(result)
            self.assertEqual(list(outside.iterdir()), [])

    def test_rejects_symlinked_backups_directory_before_conflict_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            outside = root / "outside-backups"
            repo.mkdir()
            outside.mkdir()
            (repo / "Agents.md").write_text("# Existing\n\nKeep this.\n", encoding="utf-8")
            agents_dir = repo / ".agents"
            agents_dir.mkdir()
            (agents_dir / "backups").symlink_to(outside, target_is_directory=True)

            result = self.run_setup(repo, {"AGENT_BASICS_CONFLICT_ACTION": "replace"})

            self.assert_rejected_unsafe_path(result)
            self.assertEqual(list(outside.iterdir()), [])
            self.assertEqual((repo / "Agents.md").read_text(encoding="utf-8"), "# Existing\n\nKeep this.\n")

    def test_rejects_symlinked_merge_sessions_directory_before_web_merge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            outside = root / "outside-merge-sessions"
            repo.mkdir()
            outside.mkdir()
            (repo / "Agents.md").write_text("# Existing\n\nKeep this.\n", encoding="utf-8")
            agents_dir = repo / ".agents"
            agents_dir.mkdir()
            (agents_dir / "merge-sessions").symlink_to(outside, target_is_directory=True)

            result = self.run_setup(repo, {"AGENT_BASICS_CONFLICT_ACTION": "web"})

            self.assert_rejected_unsafe_path(result)
            self.assertEqual(list(outside.iterdir()), [])
            self.assertEqual((repo / "Agents.md").read_text(encoding="utf-8"), "# Existing\n\nKeep this.\n")

    def test_rejects_symlinked_legacy_instructions_before_seed_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            outside = root / "outside-instructions.md"
            outside.write_text("# Outside Instructions\n\nDo not import.\n", encoding="utf-8")
            agents_dir = repo / ".agents"
            agents_dir.mkdir()
            (agents_dir / "INSTRUCTIONS.md").symlink_to(outside)

            result = self.run_setup(repo)

            self.assert_rejected_unsafe_path(result)
            self.assertFalse((agents_dir / "AGENT-BASICS.md").exists())

    def test_rejects_symlinked_gitignore_before_append(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            outside = root / "outside-gitignore"
            outside.write_text("keep-me\n", encoding="utf-8")
            (repo / ".gitignore").symlink_to(outside)

            result = self.run_setup(repo)

            self.assert_rejected_unsafe_path(result)
            self.assertEqual(outside.read_text(encoding="utf-8"), "keep-me\n")

    def test_rejects_symlinked_save_conflict_target_without_writing_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            outside = root / "outside-new-template.md"
            outside.write_text("keep-me\n", encoding="utf-8")
            (repo / "Agents.md").write_text("# Existing\n\nKeep this.\n", encoding="utf-8")
            (repo / "Agents.md.agent-basics.new").symlink_to(outside)

            result = self.run_setup(repo, {"AGENT_BASICS_CONFLICT_ACTION": "save"})

            self.assert_rejected_unsafe_path(result)
            self.assertEqual(outside.read_text(encoding="utf-8"), "keep-me\n")
            self.assertEqual((repo / "Agents.md").read_text(encoding="utf-8"), "# Existing\n\nKeep this.\n")

    def test_rejects_symlinked_repo_config_before_language_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            outside = root / "outside-config.toml"
            outside.write_text("[agent_basics]\nlanguage = \"zh-CN\"\n", encoding="utf-8")
            agents_dir = repo / ".agents"
            agents_dir.mkdir()
            (agents_dir / "config.toml").symlink_to(outside)

            result = self.run_setup(repo)

            self.assert_rejected_unsafe_path(result)
            self.assertEqual(outside.read_text(encoding="utf-8"), "[agent_basics]\nlanguage = \"zh-CN\"\n")

    def test_embedding_api_writer_rejects_symlinked_generated_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            embedding_dir = repo / ".agents" / "memory" / "rag" / "embedding-api"
            embedding_dir.mkdir(parents=True)
            outside = root / "outside-server.py"
            outside.write_text("keep-me\n", encoding="utf-8")
            (embedding_dir / "server.py").symlink_to(outside)
            setup_library = SETUP.read_text(encoding="utf-8").split("\nensure_agent_basics_install_config\n", 1)[0]
            driver = root / "call-write-embedding-api.sh"
            driver.write_text(
                setup_library
                + "\nwrite_embedding_api_files \"owner/model\"\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                ["bash", str(driver), str(repo)],
                cwd=ROOT,
                env={
                    **os.environ,
                    "AGENT_BASICS_CONFIG_HOME": str(repo / ".test-agent-basics-config"),
                    "AGENT_BASICS_PROJECT_NAME": "security-test",
                },
                text=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
            )

            self.assert_rejected_unsafe_path(result)
            self.assertEqual(outside.read_text(encoding="utf-8"), "keep-me\n")

    def test_project_name_shell_metacharacters_do_not_execute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo; still-a-directory\nwith-newline"
            marker = root / "pwned"
            project_name = f"security-test\"; touch {marker}; #\n../../escape"

            result = self.run_setup(repo, {"AGENT_BASICS_PROJECT_NAME": project_name}, check=True)

            self.assertEqual(result.returncode, 0)
            self.assertFalse(marker.exists())
            self.assertTrue((repo / ".agents" / "config.toml").is_file())
            self.assertTrue((repo / ".agents" / "openviking" / "repo.json").is_file())

    def test_hostile_path_does_not_hijack_core_setup_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            fake_bin = root / "fake-bin"
            marker = root / "path-hijacked"
            fake_bin.mkdir()
            for name in ["python3", "git"]:
                path = fake_bin / name
                path.write_text(
                    "#!/usr/bin/env sh\n"
                    f"touch {marker}\n"
                    "exit 99\n",
                    encoding="utf-8",
                )
                path.chmod(0o755)

            result = self.run_setup(
                repo,
                {"PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}"},
                check=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertFalse(marker.exists())
            self.assertTrue((repo / ".agents" / "config.toml").is_file())


if __name__ == "__main__":
    unittest.main()
