from __future__ import annotations

import json
import os
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "setup-macos.sh"


class SetupMacosTest(unittest.TestCase):
    def install_config_path(self, repo: Path) -> Path:
        return repo / ".test-agent-basics-config" / "config.toml"

    def read_install_config(self, repo: Path) -> dict[str, object]:
        return tomllib.loads(self.install_config_path(repo).read_text(encoding="utf-8"))

    def write_fake_openviking(self, repo: Path) -> Path:
        fake_bin = repo / ".test-openviking" / "ov"
        fake_bin.parent.mkdir(parents=True, exist_ok=True)
        fake_bin.write_text(
            "#!/usr/bin/env sh\n"
            "case \"$1\" in\n"
            "  --help) echo 'fake OpenViking help'; exit 0 ;;\n"
            "  version) echo 'CLI: 0.0.0-test'; exit 0 ;;\n"
            "  *) exit 0 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        fake_bin.chmod(0o755)
        return fake_bin

    def write_fake_openviking_installer(self, repo: Path) -> tuple[Path, Path]:
        fake_dispatcher = repo / ".test-openviking" / "agent-basics"
        log_path = repo / ".test-openviking" / "install.log"
        fake_dispatcher.parent.mkdir(parents=True, exist_ok=True)
        fake_dispatcher.write_text(
            "#!/usr/bin/env sh\n"
            "set -eu\n"
            "printf '%s\\n' \"$*\" >> \"$AGENT_BASICS_TEST_OPENVIKING_INSTALL_LOG\"\n"
            "if [ \"$1\" != \"ov\" ]; then\n"
            "  echo \"unexpected fake dispatcher command: $*\" >&2\n"
            "  exit 2\n"
            "fi\n"
            "case \"$2\" in\n"
            "  bootstrap-system)\n"
            "    shift 2\n"
            "    home=\"\"\n"
            "    while [ \"$#\" -gt 0 ]; do\n"
            "      case \"$1\" in\n"
            "        --home) home=\"$2\"; shift 2 ;;\n"
            "        *) shift ;;\n"
            "      esac\n"
            "    done\n"
            "    if [ -z \"$home\" ]; then echo \"missing --home\" >&2; exit 2; fi\n"
            "    mkdir -p \"$home/venv/bin\"\n"
            "    cat > \"$home/venv/bin/ov\" <<'EOS'\n"
            "#!/usr/bin/env sh\n"
            "case \"$1\" in\n"
            "  --help) echo 'fake installed OpenViking help'; exit 0 ;;\n"
            "  version) echo 'CLI: 0.0.0-installed-test'; exit 0 ;;\n"
            "  *) exit 0 ;;\n"
            "esac\n"
            "EOS\n"
            "    chmod 0755 \"$home/venv/bin/ov\"\n"
            "    printf '{\"storage\":{\"workspace\":\"%s/workspace\"}}\\n' \"$home\" > \"$home/ov.conf\"\n"
            "    printf '{\"url\":\"http://127.0.0.1:1933\",\"timeout\":86400}\\n' > \"$home/ovcli.conf\"\n"
            "    ;;\n"
            "  install-system)\n"
            "    shift 2\n"
            "    home=\"\"\n"
            "    while [ \"$#\" -gt 0 ]; do\n"
            "      case \"$1\" in\n"
            "        --home) home=\"$2\"; shift 2 ;;\n"
            "        *) shift ;;\n"
            "      esac\n"
            "    done\n"
            "    if [ -z \"$home\" ]; then echo \"missing --home\" >&2; exit 2; fi\n"
            "    mkdir -p \"$home/venv/bin\"\n"
            "    cat > \"$home/venv/bin/ov\" <<'EOS'\n"
            "#!/usr/bin/env sh\n"
            "case \"$1\" in\n"
            "  --help) echo 'fake installed OpenViking help'; exit 0 ;;\n"
            "  version) echo 'CLI: 0.0.0-installed-test'; exit 0 ;;\n"
            "  *) exit 0 ;;\n"
            "esac\n"
            "EOS\n"
            "    chmod 0755 \"$home/venv/bin/ov\"\n"
            "    ;;\n"
            "  write-default-config)\n"
            "    shift 2\n"
            "    home=\"\"\n"
            "    config=\"\"\n"
            "    cli_config=\"\"\n"
            "    while [ \"$#\" -gt 0 ]; do\n"
            "      case \"$1\" in\n"
            "        --home) home=\"$2\"; shift 2 ;;\n"
            "        --config) config=\"$2\"; shift 2 ;;\n"
            "        --cli-config) cli_config=\"$2\"; shift 2 ;;\n"
            "        *) shift ;;\n"
            "      esac\n"
            "    done\n"
            "    if [ -z \"$home\" ]; then echo \"missing --home\" >&2; exit 2; fi\n"
            "    if [ -z \"$config\" ]; then config=\"$home/ov.conf\"; fi\n"
            "    if [ -z \"$cli_config\" ]; then cli_config=\"$home/ovcli.conf\"; fi\n"
            "    mkdir -p \"$home\"\n"
            "    printf '{\"storage\":{\"workspace\":\"%s/workspace\"}}\\n' \"$home\" > \"$config\"\n"
            "    printf '{\"url\":\"http://127.0.0.1:1933\",\"timeout\":86400}\\n' > \"$cli_config\"\n"
            "    ;;\n"
            "  service)\n"
            "    shift 2\n"
            "    if [ \"${1:-}\" != \"install\" ]; then\n"
            "      echo \"unexpected fake service action: $*\" >&2\n"
            "      exit 2\n"
            "    fi\n"
            "    ;;\n"
            "  *)\n"
            "    echo \"unexpected fake dispatcher command: $*\" >&2\n"
            "    exit 2\n"
            "    ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        fake_dispatcher.chmod(0o755)
        return fake_dispatcher, log_path

    def run_setup(
        self,
        repo: Path,
        extra_env: dict[str, str] | None = None,
        *,
        check: bool = True,
        fake_openviking: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env.pop("AGENT_BASICS_TEST_OPENVIKING_BIN", None)
        env.pop("AGENT_BASICS_TEST_SKIP_OPENVIKING_CHECK", None)
        env.pop("AGENT_BASICS_TEST_OPENVIKING_AUTO_INSTALL", None)
        env.pop("AGENT_BASICS_TEST_OPENVIKING_INSTALL_DISPATCHER", None)
        env.pop("AGENT_BASICS_TEST_OPENVIKING_INSTALL_LOG", None)
        env.update(
            {
                "AGENT_BASICS_CONFIG_HOME": str(repo / ".test-agent-basics-config"),
                "AGENT_BASICS_INSTALL_COMPAT_MEMORY": "0",
                "AGENT_BASICS_OPEN_MERGE_UI": "0",
                "AGENT_BASICS_PROJECT_NAME": "setup-test",
            }
        )
        if fake_openviking:
            env["AGENT_BASICS_TEST_OPENVIKING_BIN"] = str(self.write_fake_openviking(repo))
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

    def test_fresh_setup_creates_ov_source_store_without_legacy_minirag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            result = self.run_setup(repo)

            memory_root = repo / ".agents" / "memory"
            self.assertIn("Verified user-level OpenViking CLI", result.stdout)
            self.assertTrue((memory_root / "SCHEMA.md").is_file())
            self.assertTrue((memory_root / "ADAPTATION.md").is_file())
            self.assertTrue((memory_root / "memories" / "preferences" / ".gitkeep").is_file())
            self.assertTrue((memory_root / "resources" / "sources" / ".gitkeep").is_file())
            self.assertTrue((repo / ".agents" / "openviking" / "repo.json").is_file())
            self.assertTrue((repo / ".agents" / "backups").is_dir())
            self.assertTrue((repo / ".agents" / "merge-sessions").is_dir())
            self.assertFalse((repo / ".agents" / "runs").exists())
            self.assertTrue((repo / "Skills.md").is_file())
            self.assertTrue((repo / ".agents" / "skills" / "prework.md").is_file())
            self.assertTrue((repo / ".agents" / "skills" / "memory-update.md").is_file())
            self.assertTrue((repo / ".agents" / "skills" / "finish-work.md").is_file())

            self.assertFalse((memory_root / "memory").exists())
            self.assertFalse((memory_root / "documentations").exists())
            self.assertFalse((memory_root / "templates").exists())
            self.assertFalse((memory_root / "rag").exists())

            config = tomllib.loads((repo / ".agents" / "config.toml").read_text(encoding="utf-8"))
            self.assertEqual(config["repo_slug"], "setup-test")
            self.assertIsInstance(config["generated_at"], int)
            self.assertNotIn("agent_basics", config)
            self.assertEqual(
                config["openviking"],
                {
                    "enabled": True,
                    "required": True,
                    "source_store_path": ".agents/memory",
                    "mcp": {
                        "command": "agent-basics",
                        "args": ["mcp"],
                        "cwd_argument": "cwd",
                    },
                },
            )
            self.assertNotIn("run", config)
            self.assertEqual(self.read_install_config(repo)["agent_basics"], {"language": "en"})

            snippet = json.loads((repo / ".agents" / "openviking" / "codex-mcp.json").read_text(encoding="utf-8"))
            self.assertEqual(
                snippet,
                {
                    "mcpServers": {
                        "agent-basics": {
                            "command": "agent-basics",
                            "args": ["mcp"],
                        }
                    }
                },
            )

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

    def test_setup_fails_when_user_openviking_install_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            home = Path(tmp) / "home"
            repo.mkdir()
            home.mkdir()

            result = self.run_setup(
                repo,
                {"HOME": str(home)},
                check=False,
                fake_openviking=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("user-level OpenViking installation is required", result.stderr)
            self.assertIn("setup is not running interactively", result.stderr)
            self.assertIn("agent-basics ov bootstrap-system", result.stderr)
            self.assertFalse((repo / ".agents" / "config.toml").exists())

    def test_setup_invokes_fake_install_and_generates_config_when_openviking_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            home = Path(tmp) / "home"
            repo.mkdir()
            home.mkdir()
            dispatcher, install_log = self.write_fake_openviking_installer(repo)
            ov_home = home / ".openviking"

            result = self.run_setup(
                repo,
                {
                    "AGENT_BASICS_TEST_OPENVIKING_AUTO_INSTALL": "1",
                    "AGENT_BASICS_TEST_OPENVIKING_INSTALL_DISPATCHER": str(dispatcher),
                    "AGENT_BASICS_TEST_OPENVIKING_INSTALL_LOG": str(install_log),
                    "HOME": str(home),
                },
                fake_openviking=False,
            )

            self.assertIn("Running test-only OpenViking installation via fake dispatcher", result.stdout)
            self.assertIn("Verified user-level OpenViking CLI", result.stdout)
            self.assertEqual(
                install_log.read_text(encoding="utf-8").strip().splitlines(),
                [
                    f"ov bootstrap-system --home {ov_home} --service-best-effort --runtime ollama --runtime-best-effort",
                    f"ov service install --home {ov_home}",
                ],
            )
            self.assertTrue((ov_home / "venv" / "bin" / "ov").is_file())
            self.assertTrue((ov_home / "ov.conf").is_file())
            self.assertTrue((ov_home / "ovcli.conf").is_file())

            config = tomllib.loads((repo / ".agents" / "config.toml").read_text(encoding="utf-8"))
            self.assertEqual(config["openviking"]["mcp"]["cwd_argument"], "cwd")
            snippet = json.loads((repo / ".agents" / "openviking" / "codex-mcp.json").read_text(encoding="utf-8"))
            self.assertNotIn("cwd", snippet["mcpServers"]["agent-basics"])

    def test_setup_persists_chinese_language_and_prints_chinese_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            result = self.run_setup(repo, {"AGENT_BASICS_LANGUAGE": "zh-CN"})

            config = tomllib.loads((repo / ".agents" / "config.toml").read_text(encoding="utf-8"))
            agents_text = (repo / "Agents.md").read_text(encoding="utf-8")

            self.assertNotIn("agent_basics", config)
            self.assertEqual(self.read_install_config(repo)["agent_basics"]["language"], "zh-CN")
            self.assertIn("agent-basics 设置完成。", result.stdout)
            self.assertIn("安装语言:", result.stdout)
            self.assertIn("[agent_basics].language", agents_text)
            self.assertIn("~/.agent-basics/config.toml", agents_text)

    def test_setup_language_option_updates_install_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            result = self.run_setup(repo, {"AGENT_BASICS_LANGUAGE": "zh-CN"})
            self.assertIn("agent-basics 设置完成。", result.stdout)

            result = self.run_setup(repo, {"AGENT_BASICS_LANGUAGE": "en"})
            config = tomllib.loads((repo / ".agents" / "config.toml").read_text(encoding="utf-8"))

            self.assertNotIn("agent_basics", config)
            self.assertEqual(self.read_install_config(repo)["agent_basics"]["language"], "en")
            self.assertIn(f"Updated: {self.install_config_path(repo)} language = en", result.stdout)

    def test_setup_uses_existing_install_language_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            config_path = self.install_config_path(repo)
            config_path.parent.mkdir(parents=True)
            config_path.write_text('version = 1\n\n[agent_basics]\nlanguage = "zh-CN"\n', encoding="utf-8")

            result = self.run_setup(repo)

            self.assertIn("Exists: " + str(config_path), result.stdout)
            self.assertIn("agent-basics 设置完成。", result.stdout)
            self.assertEqual(self.read_install_config(repo)["agent_basics"]["language"], "zh-CN")

    def test_setup_removes_legacy_repo_language_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            agents_dir = repo / ".agents"
            agents_dir.mkdir()
            (agents_dir / "config.toml").write_text(
                'version = 1\n\n[agent_basics]\nlanguage = "zh-CN"\n\n[openviking]\nenabled = true\n',
                encoding="utf-8",
            )

            result = self.run_setup(repo)
            config = tomllib.loads((repo / ".agents" / "config.toml").read_text(encoding="utf-8"))

            self.assertNotIn("agent_basics", config)
            self.assertIn("Removed repo-scoped language: .agents/config.toml", result.stdout)

    def test_setup_can_skip_openviking_check_with_test_only_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            home = Path(tmp) / "home"
            repo.mkdir()
            home.mkdir()

            result = self.run_setup(
                repo,
                {
                    "AGENT_BASICS_TEST_SKIP_OPENVIKING_CHECK": "1",
                    "HOME": str(home),
                },
                fake_openviking=False,
            )

            self.assertIn("Skipped user-level OpenViking verification", result.stdout)
            self.assertTrue((repo / ".agents" / "config.toml").is_file())

    def test_setup_web_merge_conflict_creates_unresolved_session_without_gui(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Agents.md").write_text("# Existing Agents\n\nKeep this custom rule.\n", encoding="utf-8")

            result = self.run_setup(repo, {"AGENT_BASICS_CONFLICT_ACTION": "web"})

            self.assertIn("Created web merge session:", result.stdout)
            self.assertIn("Web merge UI was not launched", result.stdout)
            self.assertEqual((repo / "Agents.md").read_text(encoding="utf-8").rstrip() + "\n", "# Existing Agents\n\nKeep this custom rule.\n")
            sessions = sorted((repo / ".agents" / "merge-sessions").iterdir())
            self.assertEqual(len(sessions), 1)
            session = sessions[0]
            self.assertTrue((session / "existing.md").is_file())
            self.assertTrue((session / "proposed.md").is_file())
            self.assertTrue((session / "final.md").is_file())
            self.assertTrue((session / "markdown-merge-ui.html").is_file())
            metadata = json.loads((session / "session.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["status"], "unresolved")
            self.assertEqual(metadata["destination_path"], "Agents.md")
            self.assertIsInstance(metadata["created"], int)
            backups = list((repo / ".agents" / "backups").iterdir())
            self.assertEqual(len(backups), 1)

    def test_upgrade_keeps_existing_user_owned_skills_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Skills.md").write_text("# Custom Skills\n\n- Custom workflow.\n", encoding="utf-8")
            skill = repo / ".agents" / "skills" / "prework.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("# Custom Prework\n\nDo this first.\n", encoding="utf-8")

            result = self.run_setup(repo, {"AGENT_BASICS_CONFLICT_ACTION": "keep"})

            self.assertIn("Kept existing file: Skills.md", result.stdout)
            self.assertIn("Kept existing file: .agents/skills/prework.md", result.stdout)
            self.assertEqual((repo / "Skills.md").read_text(encoding="utf-8").rstrip() + "\n", "# Custom Skills\n\n- Custom workflow.\n")
            self.assertEqual(skill.read_text(encoding="utf-8").rstrip() + "\n", "# Custom Prework\n\nDo this first.\n")
            self.assertTrue((repo / ".agents" / "skills" / "memory-update.md").is_file())
            self.assertTrue((repo / ".agents" / "skills" / "finish-work.md").is_file())

    def test_dogfood_existing_repo_upgrade_preserves_legacy_agent_instructions_and_snapshots_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            legacy_instructions = repo / ".agents" / "INSTRUCTIONS.md"
            legacy_instructions.parent.mkdir(parents=True)
            legacy_instructions.write_text("# Legacy Instructions\n\nKeep existing operating rules.\n", encoding="utf-8")
            legacy_memory = repo / ".agents" / "memory" / "memory" / "facts" / "legacy.md"
            legacy_memory.parent.mkdir(parents=True)
            legacy_memory.write_text("# Legacy Fact\n", encoding="utf-8")

            result = self.run_setup(repo, {"AGENT_BASICS_CONFLICT_ACTION": "keep"})

            self.assertIn("Git repository already initialized", result.stdout)
            self.assertTrue((repo / "Agents.md").is_file())
            self.assertEqual(
                (repo / ".agents" / "AGENT-BASICS.md").read_text(encoding="utf-8").rstrip() + "\n",
                "# Legacy Instructions\n\nKeep existing operating rules.\n",
            )
            snapshots = sorted((repo / ".agents" / "openviking" / "legacy-memory").iterdir())
            self.assertEqual(len(snapshots), 1)
            self.assertTrue((snapshots[0] / "memory" / "facts" / "legacy.md").is_file())
            self.assertTrue((repo / ".agents" / "config.toml").is_file())
            self.assertTrue((repo / ".agents" / "openviking" / "codex-mcp.json").is_file())
            self.assertFalse((repo / ".agents" / "memory" / "rag").exists())


if __name__ == "__main__":
    unittest.main()
