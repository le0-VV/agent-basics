from __future__ import annotations

import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "agent_basics_ov.py"

spec = importlib.util.spec_from_file_location("agent_basics_ov", HELPER)
assert spec and spec.loader
agent_basics_ov = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_basics_ov)


class AgentBasicsOpenVikingHelperTest(unittest.TestCase):
    def test_launchctl_bootstrap_retries_code_five(self) -> None:
        calls = []
        original_run_command = agent_basics_ov.run_command
        original_sleep = agent_basics_ov.time.sleep

        def fake_run_command(command: list[str], timeout: float | None = 30) -> dict[str, object]:
            calls.append((command, timeout))
            if len(calls) == 1:
                return {"ok": False, "command": command, "returncode": 5, "stdout": "", "stderr": "Bootstrap failed"}
            return {"ok": True, "command": command, "returncode": 0, "stdout": "", "stderr": ""}

        try:
            agent_basics_ov.run_command = fake_run_command
            agent_basics_ov.time.sleep = lambda _seconds: None
            payload = agent_basics_ov.run_launchctl_bootstrap(
                ["launchctl", "bootstrap", "gui/501", "/tmp/test.plist"],
                timeout=1,
            )
        finally:
            agent_basics_ov.run_command = original_run_command
            agent_basics_ov.time.sleep = original_sleep

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["launchctl_bootstrap_retries"], 1)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][1], 1)

    def test_ov_default_config_uses_mlx_provider_models(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "ov"
            config = home / "ov.conf"
            cli_config = home / "ovcli.conf"
            output = io.StringIO()
            with redirect_stdout(output):
                result = agent_basics_ov.command_ov_write_default_config(
                    SimpleNamespace(
                        config=str(config),
                        cli_config=str(cli_config),
                        home=str(home),
                        provider="mlx",
                        base_url=None,
                        provider_base=None,
                        lmstudio_base=None,
                        api_key=None,
                        chat_model=None,
                        embedding_model=None,
                        embedding_dimension=768,
                        vlm_timeout=86400,
                        server_url="http://127.0.0.1:1933",
                        cli_timeout=86400,
                        force=False,
                    )
                )

        payload = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(payload["config"]["vlm"]["api_base"], "http://127.0.0.1:18080/v1")
        self.assertEqual(payload["config"]["vlm"]["model"], "mlx-community/gemma-4-e2b-it-4bit")
        self.assertEqual(payload["config"]["embedding"]["dense"]["model"], "mlx-community/embeddinggemma-300m-4bit")

    def test_parser_exposes_mlx_and_custom_provider_only(self) -> None:
        parser = agent_basics_ov.build_parser()
        custom = parser.parse_args(
            [
                "ov",
                "write-default-config",
                "--provider",
                "custom",
                "--base-url",
                "http://127.0.0.1:8000",
                "--chat-model",
                "custom-chat",
                "--embedding-model",
                "custom-embedding",
            ]
        )
        self.assertEqual(custom.provider, "custom")

        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit):
            parser.parse_args(["ollama", "status"])
        with redirect_stderr(stderr), self.assertRaises(SystemExit):
            parser.parse_args(["lmstudio", "plan"])
        with redirect_stderr(stderr), self.assertRaises(SystemExit):
            parser.parse_args(["ov", "write-default-config", "--provider", "ollama"])

    def test_ov_default_config_without_home_uses_repo_local_absolute_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            output = io.StringIO()
            with redirect_stdout(output):
                result = agent_basics_ov.command_ov_write_default_config(
                    SimpleNamespace(
                        repo=str(repo),
                        config=None,
                        cli_config=None,
                        home=None,
                        provider="mlx",
                        base_url=None,
                        provider_base=None,
                        api_key=None,
                        chat_model=None,
                        embedding_model=None,
                        embedding_dimension=768,
                        vlm_timeout=86400,
                        server_url="http://127.0.0.1:1933",
                        cli_timeout=86400,
                        force=False,
                    )
                )

            payload = json.loads(output.getvalue())

        self.assertEqual(result, 0)
        self.assertEqual(
            payload["config"]["storage"]["workspace"],
            str((repo / ".agents" / "openviking" / "workspace").resolve()),
        )

    def test_ov_package_server_dry_run_builds_openviking_process(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "openviking"
            target = home / "openviking"
            payload = agent_basics_ov.ov_package_server_payload(
                SimpleNamespace(
                    home=str(home),
                    server_bin=None,
                    source=None,
                    manifest=None,
                    force=False,
                    dry_run=True,
                )
            )

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["changed"])
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["target"], str(target))
        self.assertEqual(payload["process_name"], "openviking")
        self.assertEqual(payload["packager"], "pyinstaller")
        self.assertEqual(payload["mode"], "onefile")
        self.assertEqual(payload["commands"]["package"][0], str(home / "venv" / "bin" / "python"))
        self.assertIn("--name", payload["commands"]["package"])
        self.assertIn("openviking", payload["commands"]["package"])
        self.assertIn("--collect-all", payload["commands"]["package"])

    def test_ov_pyinstaller_command_adds_native_ragfs_binary(self) -> None:
        command = agent_basics_ov.ov_pyinstaller_command(
            python_bin=Path("/tmp/ov/bin/python"),
            source=Path("/tmp/openviking-server.py"),
            dist_dir=Path("/tmp/dist"),
            build_dir=Path("/tmp/build"),
            spec_dir=Path("/tmp/spec"),
            native_binaries=[(Path("/tmp/site-packages/openviking/lib/ragfs_python.abi3.so"), "openviking/lib")],
        )

        self.assertIn("--add-binary", command)
        self.assertIn("/tmp/site-packages/openviking/lib/ragfs_python.abi3.so:openviking/lib", command)

    def test_ov_package_manifest_requires_package_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "openviking"
            target.write_text("#!/bin/sh\n", encoding="utf-8")
            target.chmod(0o755)
            manifest = root / "openviking-manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "packager": "pyinstaller",
                        "mode": "onefile",
                        "target": str(target),
                        "source_sha256": "abc",
                        "openviking_version": "0.1",
                    }
                ),
                encoding="utf-8",
            )

            self.assertFalse(
                agent_basics_ov.ov_package_manifest_matches(
                    manifest,
                    target=target,
                    source_digest="abc",
                    openviking_version="0.1",
                    package_revision=agent_basics_ov.OV_PACKAGE_REVISION,
                )
            )

    def test_ov_service_defaults_to_packaged_openviking_process(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "openviking"
            packaged = home / "openviking"
            entrypoint = home / "venv" / "bin" / "openviking-server"
            packaged.parent.mkdir(parents=True)
            entrypoint.parent.mkdir(parents=True)
            packaged.write_text("#!/bin/sh\n", encoding="utf-8")
            packaged.chmod(0o755)
            entrypoint.write_text("#!/bin/sh\n", encoding="utf-8")
            entrypoint.chmod(0o755)

            paths = agent_basics_ov.ov_service_paths(
                SimpleNamespace(
                    home=str(home),
                    server_bin=None,
                    config=None,
                    label="com.agent-basics.test.openviking",
                    plist=None,
                )
            )

        self.assertEqual(paths["server_bin"], packaged)
        self.assertEqual(paths["plist_payload"]["ProgramArguments"][0], str(packaged))

    def test_mlx_service_plist_runs_agent_basics_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "mlx"
            python_bin = home / "venv" / "bin" / "python"
            server = home / "agent-basics-mlx"
            payload = agent_basics_ov.mlx_service_plist_payload(
                label="com.agent-basics.test.mlx",
                home=home,
                server_script=server,
                host="127.0.0.1",
                port=18080,
                chat_model=agent_basics_ov.DEFAULT_MLX_CHAT_MODEL,
                embedding_model=agent_basics_ov.DEFAULT_MLX_EMBEDDING_MODEL,
                no_proxy="localhost,127.0.0.1,::1",
                hf_home=home / "huggingface",
                unload_idle_seconds=0,
                preload_models="all",
                startup_structured_output_check="openviking-router",
            )

        self.assertEqual(payload["ProgramArguments"][0], str(server))
        self.assertNotIn(str(python_bin), payload["ProgramArguments"])
        self.assertIn("--chat-model", payload["ProgramArguments"])
        self.assertIn("mlx-community/gemma-4-e2b-it-4bit", payload["ProgramArguments"])
        self.assertIn("--preload-models", payload["ProgramArguments"])
        self.assertIn("all", payload["ProgramArguments"])
        self.assertIn("--startup-structured-output-check", payload["ProgramArguments"])
        self.assertIn("openviking-router", payload["ProgramArguments"])
        self.assertEqual(payload["EnvironmentVariables"]["AGENT_BASICS_MLX_HOME"], str(home))
        self.assertEqual(payload["EnvironmentVariables"]["AGENT_BASICS_MLX_PYTHON"], str(python_bin))
        self.assertEqual(payload["EnvironmentVariables"]["HF_HOME"], str(home / "huggingface"))

    def test_mlx_write_server_installs_agent_basics_mlx_process_with_venv_shebang(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "mlx"
            source = Path(tmp) / "agent-basics-mlx-source"
            target = home / "agent-basics-mlx"
            source.write_text("#!/usr/bin/env python3\nprint('ok')\n", encoding="utf-8")
            payload = agent_basics_ov.mlx_write_server_payload(
                SimpleNamespace(
                    home=str(home),
                    server_script=str(target),
                    source=str(source),
                    force=False,
                    dry_run=False,
                )
            )
            installed_first_line = target.read_text(encoding="utf-8").splitlines()[0]
            installed_mode = target.stat().st_mode

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["changed"])
        self.assertEqual(installed_first_line, f"#!{home / 'venv' / 'bin' / 'python'}")
        self.assertTrue(installed_mode & 0o111)

    def test_mlx_package_dry_run_builds_standalone_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "mlx"
            source = Path(tmp) / "agent-basics-mlx-source.py"
            target = home / "agent-basics-mlx"
            source.write_text("#!/usr/bin/env python3\nprint('ok')\n", encoding="utf-8")
            payload = agent_basics_ov.mlx_package_payload(
                SimpleNamespace(
                    home=str(home),
                    server_script=str(target),
                    source=str(source),
                    manifest=None,
                    force=False,
                    dry_run=True,
                )
            )

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["changed"])
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["target"], str(target))
        self.assertEqual(payload["packager"], "pyinstaller")
        self.assertEqual(payload["mode"], "onefile")
        self.assertEqual(payload["commands"]["package"][0], str(home / "venv" / "bin" / "python"))
        self.assertIn("--onefile", payload["commands"]["package"])
        self.assertIn("--collect-all", payload["commands"]["package"])

    def test_mlx_package_allows_existing_pyinstaller_without_uv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "mlx"
            python_bin = home / "venv" / "bin" / "python"
            source = Path(tmp) / "agent-basics-mlx-source.py"
            target = home / "agent-basics-mlx"
            python_bin.parent.mkdir(parents=True)
            python_bin.write_text("#!/bin/sh\n", encoding="utf-8")
            python_bin.chmod(0o755)
            source.write_text("#!/usr/bin/env python3\nprint('ok')\n", encoding="utf-8")
            original_run_command = agent_basics_ov.run_command
            original_shutil_which = agent_basics_ov.shutil_which

            def fake_run_command(command: list[str], timeout: float | None = 30) -> dict[str, object]:
                if "--distpath" in command:
                    dist_path = Path(command[command.index("--distpath") + 1])
                    dist_path.mkdir(parents=True, exist_ok=True)
                    built = dist_path / "agent-basics-mlx"
                    built.write_text("#!/bin/sh\n", encoding="utf-8")
                    built.chmod(0o755)
                return {"ok": True, "command": command, "returncode": 0, "stdout": "", "stderr": ""}

            try:
                agent_basics_ov.run_command = fake_run_command
                agent_basics_ov.shutil_which = lambda _name: None
                payload = agent_basics_ov.mlx_package_payload(
                    SimpleNamespace(
                        home=str(home),
                        server_script=str(target),
                        source=str(source),
                        manifest=None,
                        force=False,
                        dry_run=False,
                    )
                )
            finally:
                agent_basics_ov.run_command = original_run_command
                agent_basics_ov.shutil_which = original_shutil_which

            self.assertTrue(payload["ok"])
            self.assertTrue(payload["changed"])
            self.assertTrue(target.exists())
            self.assertEqual([step["name"] for step in payload["steps"]], ["check pyinstaller", "package executable"])

    def test_mlx_bootstrap_dry_run_plans_runtime_server_models_and_service(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "mlx"
            server_source = Path(tmp) / "server.py"
            server_source.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
            original_hardware_payload = agent_basics_ov.hardware_payload
            try:
                agent_basics_ov.hardware_payload = lambda: {
                    "ok": True,
                    "system": "Darwin",
                    "machine": "arm64",
                    "recommendation": {"memory_gb": 32.0, "cpu_threads": 8},
                }
                output = io.StringIO()
                with redirect_stdout(output):
                    result = agent_basics_ov.command_mlx_bootstrap(
                        SimpleNamespace(
                            base_url="http://127.0.0.1:18080",
                            home=str(home),
                            python="3.12",
                            package=[],
                            chat_model=agent_basics_ov.DEFAULT_MLX_CHAT_MODEL,
                            embedding_model=agent_basics_ov.DEFAULT_MLX_EMBEDDING_MODEL,
                            model=[],
                            host="127.0.0.1",
                            port=18080,
                            label="com.agent-basics.test.mlx",
                            plist=str(Path(tmp) / "com.agent-basics.test.mlx.plist"),
                            server_script=str(home / "agent-basics-mlx"),
                            source=str(server_source),
                            install="auto",
                            package_server="auto",
                            pull="auto",
                            service="auto",
                            min_memory_gb=16,
                            allow_non_macos=False,
                            force_hardware=False,
                            force_install=False,
                            force_package=False,
                            force_server=False,
                            force_service=False,
                            no_load=True,
                            unload_idle_seconds=0,
                            preload_models="all",
                            startup_structured_output_check="openviking-router",
                            timeout=5,
                            service_timeout=1,
                            wait_server_seconds=0,
                            best_effort=False,
                            dry_run=True,
                        )
                    )
            finally:
                agent_basics_ov.hardware_payload = original_hardware_payload

        payload = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["provider"], "mlx")
        self.assertEqual(
            [step["name"] for step in payload["steps"]],
            ["install runtime", "package server", "pull models", "service install"],
        )
        self.assertEqual(payload["steps"][2]["payload"]["models"], [
            "mlx-community/gemma-4-e2b-it-4bit",
            "mlx-community/embeddinggemma-300m-4bit",
        ])

    def test_mlx_hardware_gate_requires_apple_silicon_and_memory(self) -> None:
        hardware = {
            "system": "Darwin",
            "machine": "x86_64",
            "recommendation": {"memory_gb": 8.0},
        }

        payload = agent_basics_ov.mlx_hardware_gate_payload(hardware, min_memory_gb=16)

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["requirement"], "Apple Silicon Mac with at least 16 GB unified memory")
        self.assertIn("requires Apple Silicon arm64", payload["reasons"][0])
        self.assertIn("requires at least 16 GB", payload["reasons"][1])

    def test_mlx_bootstrap_fails_unsupported_hardware_by_default(self) -> None:
        original_hardware_payload = agent_basics_ov.hardware_payload
        try:
            agent_basics_ov.hardware_payload = lambda: {
                "ok": True,
                "system": "Darwin",
                "machine": "x86_64",
                "recommendation": {"memory_gb": 8.0},
            }
            output = io.StringIO()
            with redirect_stdout(output):
                result = agent_basics_ov.command_mlx_bootstrap(
                    SimpleNamespace(
                        min_memory_gb=16,
                        allow_non_macos=False,
                        force_hardware=False,
                        best_effort=False,
                        dry_run=True,
                    )
                )
        finally:
            agent_basics_ov.hardware_payload = original_hardware_payload

        payload = json.loads(output.getvalue())
        self.assertEqual(result, 1)
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["skipped"])
        self.assertIn("requires an Apple Silicon Mac with at least 16 GB unified memory", payload["error"])
        self.assertIn("--provider custom", payload["recommendation"])

    def test_mlx_bootstrap_best_effort_skips_unsupported_hardware(self) -> None:
        original_hardware_payload = agent_basics_ov.hardware_payload
        try:
            agent_basics_ov.hardware_payload = lambda: {
                "ok": True,
                "system": "Darwin",
                "machine": "arm64",
                "recommendation": {"memory_gb": 8.0},
            }
            output = io.StringIO()
            with redirect_stdout(output):
                result = agent_basics_ov.command_mlx_bootstrap(
                    SimpleNamespace(
                        min_memory_gb=16,
                        allow_non_macos=False,
                        force_hardware=False,
                        best_effort=True,
                        dry_run=True,
                    )
                )
        finally:
            agent_basics_ov.hardware_payload = original_hardware_payload

        payload = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["skipped"])
        self.assertTrue(payload["best_effort"])

    def test_preingest_splits_and_hints_ownership_statements(self) -> None:
        candidates = agent_basics_ov.preingest_candidates(
            "harness_direction",
            "The user wants agent-basics to be a thin harness layer over OpenViking. "
            "agent-basics owns setup, config, MCP, hooks, migration UX, and instructions. "
            "OpenViking owns durable context storage, resources, summaries, vector indexes, and retrieval.",
        )

        self.assertEqual(len(candidates), 3)
        self.assertEqual(candidates[0]["suggested_ov_category"], "preferences")
        self.assertEqual(candidates[1]["suggested_ov_category"], "entities")
        self.assertEqual(candidates[2]["suggested_ov_category"], "entities")

    def test_lmstudio_config_mismatches_only_checks_reported_load_keys(self) -> None:
        mismatches = agent_basics_ov.lmstudio_config_mismatches(
            {
                "context_length": 131072,
                "eval_batch_size": 256,
                "flash_attention": True,
                "offload_kv_cache_to_gpu": True,
                "parallel": 4,
            },
            {
                "model": "google/gemma-4-e2b",
                "context_length": 131072,
                "eval_batch_size": 512,
                "flash_attention": True,
                "offload_kv_cache_to_gpu": True,
                "parallel": 1,
                "llama_k_cache_quantization_type": "q4_0",
            },
        )

        self.assertEqual(mismatches, [{"key": "eval_batch_size", "actual": 256, "desired": 512}])

    def test_lmstudio_default_config_keeps_router_schema_request_time_only(self) -> None:
        config = agent_basics_ov.lmstudio_desired_chat_config(
            cpu_threads=8,
            parallel=1,
            context_length=131072,
            kv_cache_quantization="q4_0",
            gpu_offload_ratio=1.0,
            temperature=0,
        )

        operation = {field["key"]: field["value"] for field in config["operation"]["fields"]}
        load = {field["key"]: field["value"] for field in config["load"]["fields"]}

        self.assertNotIn("llm.prediction.systemPrompt", operation)
        self.assertNotIn("llm.prediction.structured", operation)
        self.assertEqual(operation["llm.prediction.temperature"], 0)
        self.assertEqual(load["llm.load.numParallelSessions"], 1)
        self.assertEqual(load["llm.load.contextLength"], 131072)
        self.assertEqual(load["llm.load.llama.kCacheQuantizationType"], {"checked": True, "value": "q4_0"})
        self.assertEqual(load["llm.load.llama.vCacheQuantizationType"], {"checked": True, "value": "q4_0"})

    def test_lmstudio_config_merge_clears_stale_router_defaults(self) -> None:
        existing = {
            "preset": "",
            "operation": {
                "fields": [
                    {"key": "llm.prediction.structured", "value": {"type": "json"}},
                    {"key": "llm.prediction.systemPrompt", "value": "old router prompt"},
                    {"key": "custom.operation", "value": True},
                ]
            },
            "load": {"fields": []},
        }
        desired = {"preset": "", "operation": {"fields": []}, "load": {"fields": []}}

        merged = agent_basics_ov.merge_lmstudio_config(
            existing,
            desired,
            remove_operation_keys=agent_basics_ov.LMSTUDIO_ROUTING_DEFAULT_KEYS,
        )
        operation = {field["key"]: field["value"] for field in merged["operation"]["fields"]}

        self.assertNotIn("llm.prediction.structured", operation)
        self.assertNotIn("llm.prediction.systemPrompt", operation)
        self.assertEqual(operation["custom.operation"], True)

    def test_lmstudio_config_merge_preserves_unrelated_fields(self) -> None:
        existing = {
            "preset": "",
            "operation": {"fields": [{"key": "custom.operation", "value": True}]},
            "load": {
                "fields": [
                    {"key": "llm.load.numParallelSessions", "value": 4},
                    {"key": "custom.load", "value": "preserve"},
                ]
            },
        }
        desired = {
            "preset": "",
            "operation": {"fields": [{"key": "llm.prediction.temperature", "value": 0}]},
            "load": {"fields": [{"key": "llm.load.numParallelSessions", "value": 1}]},
        }

        merged = agent_basics_ov.merge_lmstudio_config(existing, desired)
        operation = {field["key"]: field["value"] for field in merged["operation"]["fields"]}
        load = {field["key"]: field["value"] for field in merged["load"]["fields"]}

        self.assertEqual(operation["custom.operation"], True)
        self.assertEqual(operation["llm.prediction.temperature"], 0)
        self.assertEqual(load["llm.load.numParallelSessions"], 1)
        self.assertEqual(load["custom.load"], "preserve")

    def test_lmstudio_hardware_gate_requires_enough_apple_silicon_memory(self) -> None:
        hardware = {
            "system": "Darwin",
            "machine": "arm64",
            "recommendation": {"memory_gb": 8.0},
        }

        payload = agent_basics_ov.lmstudio_hardware_gate_payload(hardware, min_memory_gb=16)

        self.assertFalse(payload["ok"])
        self.assertIn("requires at least 16 GB", payload["reasons"][0])

    def test_lmstudio_service_plist_starts_lms_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "lmstudio"
            lms_bin = home / "bin" / "lms"

            payload = agent_basics_ov.lmstudio_service_plist_payload(
                label="com.agent-basics.test.lmstudio",
                home=home,
                lms_bin=lms_bin,
                port=1234,
                no_proxy="localhost,127.0.0.1,::1",
            )

        self.assertEqual(payload["ProgramArguments"], [str(lms_bin), "server", "start", "--port", "1234"])
        self.assertEqual(payload["RunAtLoad"], True)
        self.assertEqual(payload["KeepAlive"], True)

    def test_lmstudio_service_permission_error_returns_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "lmstudio"
            lms_bin = home / "bin" / "lms"
            plist_path = Path(tmp) / "com.agent-basics.test.lmstudio.plist"
            lms_bin.parent.mkdir(parents=True)
            lms_bin.write_text("#!/bin/sh\n", encoding="utf-8")
            lms_bin.chmod(0o755)

            original_mkdir = agent_basics_ov.Path.mkdir
            original_platform_system = agent_basics_ov.platform.system

            def fake_mkdir(path: Path, *args: object, **kwargs: object) -> None:
                if Path(path).name == "logs":
                    raise PermissionError(1, "Operation not permitted", str(path))
                return original_mkdir(path, *args, **kwargs)

            try:
                agent_basics_ov.Path.mkdir = fake_mkdir
                agent_basics_ov.platform.system = lambda: "Darwin"
                payload = agent_basics_ov.lmstudio_service_payload(
                    SimpleNamespace(
                        service_action="install",
                        lmstudio_home=str(home),
                        lms_bin=str(lms_bin),
                        port=1234,
                        label="com.agent-basics.test.lmstudio",
                        plist=str(plist_path),
                        timeout=1,
                        dry_run=False,
                        force=False,
                        no_load=True,
                    )
                )
            finally:
                agent_basics_ov.Path.mkdir = original_mkdir
                agent_basics_ov.platform.system = original_platform_system

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["exception_type"], "PermissionError")
        self.assertIn("failed to write LM Studio service files", payload["error"])
        self.assertFalse(plist_path.exists())

    def test_lmstudio_bootstrap_best_effort_ignores_service_permission_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "lmstudio"
            lms_bin = home / "bin" / "lms"
            plist_path = Path(tmp) / "com.agent-basics.test.lmstudio.plist"
            lms_bin.parent.mkdir(parents=True)
            lms_bin.write_text("#!/bin/sh\n", encoding="utf-8")
            lms_bin.chmod(0o755)

            original_mkdir = agent_basics_ov.Path.mkdir
            original_platform_system = agent_basics_ov.platform.system

            def fake_mkdir(path: Path, *args: object, **kwargs: object) -> None:
                if Path(path).name == "logs":
                    raise PermissionError(1, "Operation not permitted", str(path))
                return original_mkdir(path, *args, **kwargs)

            try:
                agent_basics_ov.Path.mkdir = fake_mkdir
                agent_basics_ov.platform.system = lambda: "Darwin"
                output = io.StringIO()
                with redirect_stdout(output):
                    result = agent_basics_ov.command_lmstudio_bootstrap(
                        SimpleNamespace(
                            base_url="http://127.0.0.1:1234",
                            lmstudio_home=str(home),
                            model=agent_basics_ov.DEFAULT_CHAT_MODEL,
                            embedding_model=agent_basics_ov.DEFAULT_EMBEDDING_MODEL,
                            download_model=[],
                            min_memory_gb=16,
                            allow_non_macos=False,
                            force_hardware=True,
                            install="never",
                            service="always",
                            configure="never",
                            download="never",
                            cask=agent_basics_ov.DEFAULT_LMSTUDIO_CASK,
                            app_path=str(Path(tmp) / "LM Studio.app"),
                            lms_bin=str(lms_bin),
                            port=1234,
                            label="com.agent-basics.test.lmstudio",
                            plist=str(plist_path),
                            timeout=5,
                            service_timeout=1,
                            wait_server_seconds=0,
                            force_install=False,
                            force_service=False,
                            no_load=True,
                            best_effort=True,
                            dry_run=False,
                        )
                    )
            finally:
                agent_basics_ov.Path.mkdir = original_mkdir
                agent_basics_ov.platform.system = original_platform_system

        payload = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["best_effort"])
        service = payload["steps"][1]
        self.assertEqual(service["name"], "service install")
        self.assertTrue(service["best_effort_ignored_failure"])
        self.assertEqual(service["payload"]["exception_type"], "PermissionError")

    def test_lmstudio_bootstrap_dry_run_plans_service_download_and_jit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "lmstudio"
            app_path = Path(tmp) / "LM Studio.app"
            lms_bin = home / "bin" / "lms"
            plist_path = Path(tmp) / "com.agent-basics.test.lmstudio.plist"

            original_hardware_payload = agent_basics_ov.hardware_payload
            original_lmstudio_status_payload = agent_basics_ov.lmstudio_status_payload
            try:
                agent_basics_ov.hardware_payload = lambda: {
                    "ok": True,
                    "system": "Darwin",
                    "machine": "arm64",
                    "recommendation": {"memory_gb": 32.0, "cpu_threads": 8},
                }
                agent_basics_ov.lmstudio_status_payload = lambda base_url, timeout=5: {
                    "ok": True,
                    "models": [{"key": agent_basics_ov.DEFAULT_CHAT_MODEL, "max_context_length": 131072}],
                    "openai_models": [],
                    "loaded": [],
                    "loaded_gemma_llms": [],
                }
                output = io.StringIO()
                with redirect_stdout(output):
                    result = agent_basics_ov.command_lmstudio_bootstrap(
                        SimpleNamespace(
                            base_url="http://127.0.0.1:1234",
                            lmstudio_home=str(home),
                            model=agent_basics_ov.DEFAULT_CHAT_MODEL,
                            embedding_model=agent_basics_ov.DEFAULT_EMBEDDING_MODEL,
                            download_model=[],
                            min_memory_gb=16,
                            allow_non_macos=False,
                            force_hardware=False,
                            install="auto",
                            service="auto",
                            configure="auto",
                            download="auto",
                            cask=agent_basics_ov.DEFAULT_LMSTUDIO_CASK,
                            app_path=str(app_path),
                            lms_bin=str(lms_bin),
                            port=1234,
                            label="com.agent-basics.test.lmstudio",
                            plist=str(plist_path),
                            timeout=5,
                            service_timeout=1,
                            wait_server_seconds=0,
                            force_install=False,
                            force_service=False,
                            no_load=True,
                            best_effort=False,
                            dry_run=True,
                        )
                    )
            finally:
                agent_basics_ov.hardware_payload = original_hardware_payload
                agent_basics_ov.lmstudio_status_payload = original_lmstudio_status_payload

        payload = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["dry_run"])
        self.assertEqual(
            [step["name"] for step in payload["steps"]],
            ["install", "service install", "configure models", "wait server", "download models", "ensure jit loading"],
        )
        service = payload["steps"][1]["payload"]
        self.assertEqual(service["plist_payload"]["ProgramArguments"], [str(lms_bin), "server", "start", "--port", "1234"])
        downloads = payload["steps"][4]["payload"]["results"]
        self.assertEqual([item["model"] for item in downloads], [agent_basics_ov.DEFAULT_CHAT_MODEL, agent_basics_ov.DEFAULT_EMBEDDING_MODEL])
        self.assertTrue(payload["steps"][5]["payload"]["jit_loading"])

    def test_ov_native_import_files_selects_source_store_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            memory_root = repo / ".agents" / "memory"
            (memory_root / "memories" / "preferences").mkdir(parents=True)
            (memory_root / "resources" / "sources").mkdir(parents=True)
            (memory_root / "memory" / "facts").mkdir(parents=True)
            (memory_root / "SCHEMA.md").write_text("# Schema\n", encoding="utf-8")
            (memory_root / "ADAPTATION.md").write_text("# Adapt\n", encoding="utf-8")
            (memory_root / "memories" / "preferences" / "keep.md").write_text("# Keep\n", encoding="utf-8")
            (memory_root / "resources" / "sources" / "docs.md").write_text("# Docs\n", encoding="utf-8")
            (memory_root / "memory" / "facts" / "legacy.md").write_text("# Legacy\n", encoding="utf-8")

            selected = agent_basics_ov.ov_native_import_files(repo)

        self.assertEqual(
            [path.relative_to(repo).as_posix() for path in selected["memories"]],
            [".agents/memory/memories/preferences/keep.md"],
        )
        self.assertEqual(
            [path.relative_to(repo).as_posix() for path in selected["resources"]],
            [
                ".agents/memory/ADAPTATION.md",
                ".agents/memory/SCHEMA.md",
                ".agents/memory/resources/sources/docs.md",
            ],
        )

    def test_ov_source_store_filter_ignores_legacy_memory_and_lock_paths(self) -> None:
        paths = [
            ".agents/memory/memories/preferences/keep.md",
            ".agents/memory/resources/sources/docs.md",
            ".agents/memory/skills/workflow.md",
            ".agents/memory/INDEX.md",
            ".agents/memory/memory/facts/legacy.md",
            ".agents/memory/rag/write.lock/owner",
            ".agents/memory/rag/config.json",
            ".agents/openviking/locks/ingest.lock/owner.json",
        ]

        self.assertEqual(
            agent_basics_ov.ov_relevant_source_store_paths(paths),
            [
                ".agents/memory/memories/preferences/keep.md",
                ".agents/memory/resources/sources/docs.md",
                ".agents/memory/skills/workflow.md",
                ".agents/memory/INDEX.md",
            ],
        )

    def test_ov_install_hooks_writes_managed_git_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            hooks_dir = repo / ".git" / "hooks"
            hooks_dir.mkdir(parents=True)

            payload = agent_basics_ov.ov_install_hooks_payload(repo)
            second = agent_basics_ov.ov_install_hooks_payload(repo)

            pre_commit = hooks_dir / "pre-commit"
            post_merge = hooks_dir / "post-merge"
            pre_commit_text = pre_commit.read_text(encoding="utf-8")
            post_merge_text = post_merge.read_text(encoding="utf-8")
            pre_commit_executable = os.access(pre_commit, os.X_OK)
            post_merge_executable = os.access(post_merge, os.X_OK)

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["changed"])
        self.assertFalse(second["changed"])
        self.assertIn(agent_basics_ov.OV_HOOK_MARKER, pre_commit_text)
        self.assertIn('if [ -x "$repo/agent-basics" ]', pre_commit_text)
        self.assertIn("ov hook pre-commit", pre_commit_text)
        self.assertIn("ov hook post-merge", post_merge_text)
        self.assertTrue(pre_commit_executable)
        self.assertTrue(post_merge_executable)

    def test_ov_install_hooks_upgrades_legacy_memory_hooks_and_removes_obsolete_ones(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            hooks_dir = repo / ".git" / "hooks"
            hooks_dir.mkdir(parents=True)
            for hook_name in ["pre-commit", "post-merge", "post-commit", "post-checkout"]:
                (hooks_dir / hook_name).write_text(
                    "#!/usr/bin/env bash\n"
                    "set -euo pipefail\n"
                    "# agent-basics memory hook\n"
                    "exec .agents/memory/rag/agent-memory.py hook\n",
                    encoding="utf-8",
                )

            payload = agent_basics_ov.ov_install_hooks_payload(repo)
            pre_commit_text = (hooks_dir / "pre-commit").read_text(encoding="utf-8")
            post_merge_text = (hooks_dir / "post-merge").read_text(encoding="utf-8")
            post_commit_exists = (hooks_dir / "post-commit").exists()
            post_checkout_exists = (hooks_dir / "post-checkout").exists()

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["changed"])
        self.assertIn(agent_basics_ov.OV_HOOK_MARKER, pre_commit_text)
        self.assertIn(agent_basics_ov.OV_HOOK_MARKER, post_merge_text)
        self.assertFalse(post_commit_exists)
        self.assertFalse(post_checkout_exists)

    def test_ov_install_hooks_uses_git_common_hooks_for_linked_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "worktree"
            common_git = root / "common.git"
            private_git = common_git / "worktrees" / "worktree"
            repo.mkdir()
            private_git.mkdir(parents=True)
            repo.joinpath(".git").write_text(f"gitdir: {private_git}\n", encoding="utf-8")

            def fake_run(command: list[str], timeout: float | None = 30) -> dict[str, object]:
                self.assertEqual(command, ["git", "-C", str(repo), "rev-parse", "--git-common-dir"])
                return {
                    "ok": True,
                    "command": command,
                    "returncode": 0,
                    "stdout": str(common_git),
                    "stderr": "",
                }

            original_run_command = agent_basics_ov.run_command
            try:
                agent_basics_ov.run_command = fake_run
                payload = agent_basics_ov.ov_install_hooks_payload(repo)
            finally:
                agent_basics_ov.run_command = original_run_command

            pre_commit = common_git / "hooks" / "pre-commit"
            private_pre_commit = private_git / "hooks" / "pre-commit"
            pre_commit_exists = pre_commit.exists()
            private_pre_commit_exists = private_pre_commit.exists()

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["hooks_dir"], str(common_git / "hooks"))
        self.assertTrue(pre_commit_exists)
        self.assertFalse(private_pre_commit_exists)

    def test_ov_install_hooks_refuses_unmanaged_existing_hook_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            hook = repo / ".git" / "hooks" / "pre-commit"
            hook.parent.mkdir(parents=True)
            hook.write_text("#!/bin/sh\necho custom\n", encoding="utf-8")

            payload = agent_basics_ov.ov_install_hooks_payload(repo)
            hook_text = hook.read_text(encoding="utf-8")

        self.assertFalse(payload["ok"])
        self.assertEqual(hook_text, "#!/bin/sh\necho custom\n")
        self.assertIn("not managed", payload["hooks"][0]["error"])

    def test_ov_hook_pre_commit_runs_ingest_for_staged_source_changes_with_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            commands: list[list[str]] = []

            def fake_run(command: list[str], timeout: float | None = 30) -> dict[str, object]:
                commands.append(command)
                if command[:3] == ["git", "-C", str(repo)]:
                    return {
                        "ok": True,
                        "command": command,
                        "returncode": 0,
                        "stdout": "\n".join(
                            [
                                ".agents/memory/memories/preferences/keep.md",
                                ".agents/memory/rag/config.json",
                            ]
                        ),
                        "stderr": "",
                    }
                return {"ok": True, "command": command, "returncode": 0, "stdout": "{}", "stderr": ""}

            original = agent_basics_ov.run_command
            try:
                agent_basics_ov.run_command = fake_run
                payload = agent_basics_ov.ov_hook_run_payload(repo, event="pre-commit", prompt=False)
            finally:
                agent_basics_ov.run_command = original

            lock_path_exists = agent_basics_ov.ov_hook_ingest_lock_path(repo).exists()

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["source_store"]["relevant_paths"], [".agents/memory/memories/preferences/keep.md"])
        self.assertEqual(commands[0][:6], ["git", "-C", str(repo), "diff", "--cached", "--name-only"])
        self.assertIn("ingest-changed", commands[1])
        self.assertFalse(lock_path_exists)

    def test_ov_hook_post_merge_uses_committed_diff_and_ingest_changed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            commands: list[list[str]] = []

            def fake_run(command: list[str], timeout: float | None = 30) -> dict[str, object]:
                commands.append(command)
                if command[:3] == ["git", "-C", str(repo)]:
                    return {
                        "ok": True,
                        "command": command,
                        "returncode": 0,
                        "stdout": ".agents/memory/resources/source.md",
                        "stderr": "",
                    }
                return {"ok": True, "command": command, "returncode": 0, "stdout": "{}", "stderr": ""}

            original = agent_basics_ov.run_command
            try:
                agent_basics_ov.run_command = fake_run
                payload = agent_basics_ov.ov_hook_run_payload(repo, event="post-merge", prompt=False)
            finally:
                agent_basics_ov.run_command = original

        self.assertTrue(payload["ok"])
        self.assertEqual(commands[0][3], "diff-tree")
        self.assertIn("ORIG_HEAD", commands[0])
        self.assertIn("HEAD", commands[0])
        self.assertIn("ingest-changed", commands[1])

    def test_ov_hook_does_not_ingest_when_openviking_lock_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            lock_path = agent_basics_ov.ov_hook_ingest_lock_path(repo)
            lock_path.mkdir(parents=True)
            (lock_path / "owner.json").write_text('{"pid": 123, "created": 1777900000}\n', encoding="utf-8")
            commands: list[list[str]] = []

            def fake_run(command: list[str], timeout: float | None = 30) -> dict[str, object]:
                commands.append(command)
                return {
                    "ok": True,
                    "command": command,
                    "returncode": 0,
                    "stdout": ".agents/memory/memories/preferences/keep.md",
                    "stderr": "",
                }

            original = agent_basics_ov.run_command
            try:
                agent_basics_ov.run_command = fake_run
                payload = agent_basics_ov.ov_hook_run_payload(repo, event="pre-commit", prompt=False)
            finally:
                agent_basics_ov.run_command = original

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["action"], "locked")
        self.assertEqual(len(commands), 1)
        self.assertIn(".agents/openviking/locks/ingest.lock", payload["lock"]["lock_path"])

    def test_ov_mkdir_p_builds_valid_viking_uris(self) -> None:
        calls: list[tuple[list[str], float | None]] = []

        def fake_run(command: list[str], timeout: float | None = 30, env: dict[str, str] | None = None) -> dict[str, object]:
            calls.append((command, timeout))
            return {"ok": True, "stderr": ""}

        original = agent_basics_ov.run_command_env
        try:
            agent_basics_ov.run_command_env = fake_run
            agent_basics_ov.ov_mkdir_p(Path("/tmp/ov"), "viking://resources/projects/agent-basics", timeout=7)
        finally:
            agent_basics_ov.run_command_env = original

        self.assertEqual(
            [command[2] for command, _timeout in calls],
            ["viking://resources", "viking://resources/projects", "viking://resources/projects/agent-basics"],
        )
        self.assertEqual([timeout for _command, timeout in calls], [7, 7, 7])

    def test_ov_memory_target_uri_uses_openviking_category_and_project_slug(self) -> None:
        repo = Path("/tmp/Agent Basics")
        path = repo / ".agents" / "memory" / "memories" / "cases" / "example.md"
        target = agent_basics_ov.ov_memory_target_uri(
            "viking://user/default/memories",
            repo,
            path,
            "cases",
        )

        self.assertEqual(
            target,
            "viking://user/default/memories/cases/projects/agent-basics/example.md",
        )

    def test_ov_import_repo_memory_dry_run_writes_native_memory_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "agent-basics"
            memory_path = repo / ".agents" / "memory" / "memories" / "cases" / "case.md"
            memory_path.parent.mkdir(parents=True)
            memory_path.write_text(
                "---\n"
                "record_kind: memory\n"
                "ov_category: cases\n"
                "title: Example case\n"
                "requires_human_review: false\n"
                "---\n"
                "\n"
                "# Example case\n",
                encoding="utf-8",
            )

            original_find_ov_bin = agent_basics_ov.find_ov_bin
            original_run_command = agent_basics_ov.run_command
            try:
                agent_basics_ov.find_ov_bin = lambda: Path("/tmp/ov")
                agent_basics_ov.run_command = lambda command, timeout=30: {"ok": True, "command": command, "stdout": "{}", "stderr": ""}
                output = io.StringIO()
                with redirect_stdout(output):
                    result = agent_basics_ov.command_ov_import_repo_memory(
                        SimpleNamespace(
                            repo=str(repo),
                            target=None,
                            memory_target=agent_basics_ov.DEFAULT_OV_MEMORY_TARGET,
                            timeout=agent_basics_ov.DEFAULT_OV_VLM_TIMEOUT_SECONDS,
                            include_review=False,
                            force=False,
                            dry_run=True,
                            wait=False,
                            wait_memory=False,
                            wait_resources=False,
                            busy_retries=0,
                            busy_delay=0,
                            write=False,
                        )
                    )
            finally:
                agent_basics_ov.find_ov_bin = original_find_ov_bin
                agent_basics_ov.run_command = original_run_command

        payload = json.loads(output.getvalue())
        memory_command = payload["results"][0]["command"]

        self.assertEqual(result, 0)
        self.assertEqual(memory_command[1], "write")
        self.assertIn("viking://user/default/memories/cases/projects/agent-basics/case.md", memory_command)

    def test_ov_import_repo_memory_reimports_when_state_target_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "agent-basics"
            memory_path = repo / ".agents" / "memory" / "memories" / "cases" / "case.md"
            memory_path.parent.mkdir(parents=True)
            memory_text = (
                "---\n"
                "record_kind: memory\n"
                "ov_category: cases\n"
                "title: Example case\n"
                "requires_human_review: false\n"
                "---\n"
                "\n"
                "# Example case\n"
            )
            memory_path.write_text(memory_text, encoding="utf-8")
            target = "viking://user/default/memories/cases/projects/agent-basics/case.md"
            state_path = repo / ".agents" / "openviking" / "import-state.json"
            state_path.parent.mkdir(parents=True)
            state_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "imports": {
                            ".agents/memory/memories/cases/case.md": {
                                "ok": True,
                                "method": "write",
                                "sha256": agent_basics_ov.sha256_text(memory_text),
                                "target": target,
                            }
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            calls: list[tuple[list[str], float | None]] = []

            def fake_run(command: list[str], timeout: float | None = 30, env: dict[str, str] | None = None) -> dict[str, object]:
                calls.append((command, timeout))
                if command[1] == "health":
                    return {"ok": True, "command": command, "stdout": "{}", "stderr": "", "returncode": 0}
                if command[1] == "stat":
                    return {"ok": False, "command": command, "stdout": "", "stderr": "not found", "returncode": 1}
                return {"ok": True, "command": command, "stdout": "{}", "stderr": "", "returncode": 0}

            original_find_ov_bin = agent_basics_ov.find_ov_bin
            original_run_command_env = agent_basics_ov.run_command_env
            try:
                agent_basics_ov.find_ov_bin = lambda: Path("/tmp/ov")
                agent_basics_ov.run_command_env = fake_run
                output = io.StringIO()
                with redirect_stdout(output):
                    result = agent_basics_ov.command_ov_import_repo_memory(
                        SimpleNamespace(
                            repo=str(repo),
                            target=None,
                            memory_target=agent_basics_ov.DEFAULT_OV_MEMORY_TARGET,
                            timeout=agent_basics_ov.DEFAULT_OV_VLM_TIMEOUT_SECONDS,
                            quick_timeout=3,
                            include_review=False,
                            force=False,
                            dry_run=False,
                            wait=False,
                            wait_memory=False,
                            wait_resources=False,
                            busy_retries=0,
                            busy_delay=0,
                            write=False,
                        )
                    )
            finally:
                agent_basics_ov.find_ov_bin = original_find_ov_bin
                agent_basics_ov.run_command_env = original_run_command_env

        payload = json.loads(output.getvalue())
        commands = [command for command, _timeout in calls]
        write_commands = [command for command in commands if command[1] == "write"]

        self.assertEqual(result, 0)
        self.assertFalse(payload["results"][0]["skipped"])
        self.assertEqual(len(write_commands), 1)
        self.assertIn(target, write_commands[0])
        for command, timeout in calls:
            if command[1] in {"health", "mkdir", "stat", "read"}:
                self.assertEqual(timeout, 3)

    def test_ov_import_repo_memory_does_not_write_when_state_stat_times_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "agent-basics"
            memory_path = repo / ".agents" / "memory" / "memories" / "cases" / "case.md"
            memory_path.parent.mkdir(parents=True)
            memory_text = (
                "---\n"
                "record_kind: memory\n"
                "ov_category: cases\n"
                "title: Example case\n"
                "requires_human_review: false\n"
                "---\n"
                "\n"
                "# Example case\n"
            )
            memory_path.write_text(memory_text, encoding="utf-8")
            target = "viking://user/default/memories/cases/projects/agent-basics/case.md"
            state_path = repo / ".agents" / "openviking" / "import-state.json"
            state_path.parent.mkdir(parents=True)
            state_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "imports": {
                            ".agents/memory/memories/cases/case.md": {
                                "ok": True,
                                "method": "write",
                                "sha256": agent_basics_ov.sha256_text(memory_text),
                                "target": target,
                            }
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            calls: list[tuple[list[str], float | None]] = []

            def fake_run(command: list[str], timeout: float | None = 30, env: dict[str, str] | None = None) -> dict[str, object]:
                calls.append((command, timeout))
                if command[1] == "health":
                    return {"ok": True, "command": command, "stdout": "{}", "stderr": "", "returncode": 0}
                if command[1] == "stat":
                    return {
                        "ok": False,
                        "command": command,
                        "stdout": "",
                        "stderr": "",
                        "error": "timed out after 4s",
                    }
                return {"ok": True, "command": command, "stdout": "{}", "stderr": "", "returncode": 0}

            original_find_ov_bin = agent_basics_ov.find_ov_bin
            original_run_command_env = agent_basics_ov.run_command_env
            try:
                agent_basics_ov.find_ov_bin = lambda: Path("/tmp/ov")
                agent_basics_ov.run_command_env = fake_run
                output = io.StringIO()
                with redirect_stdout(output):
                    result = agent_basics_ov.command_ov_import_repo_memory(
                        SimpleNamespace(
                            repo=str(repo),
                            target=None,
                            memory_target=agent_basics_ov.DEFAULT_OV_MEMORY_TARGET,
                            timeout=agent_basics_ov.DEFAULT_OV_VLM_TIMEOUT_SECONDS,
                            quick_timeout=4,
                            include_review=False,
                            force=False,
                            dry_run=False,
                            wait=False,
                            wait_memory=False,
                            wait_resources=False,
                            busy_retries=0,
                            busy_delay=0,
                            write=False,
                        )
                    )
            finally:
                agent_basics_ov.find_ov_bin = original_find_ov_bin
                agent_basics_ov.run_command_env = original_run_command_env

        payload = json.loads(output.getvalue())
        commands = [command for command, _timeout in calls]

        self.assertEqual(result, 1)
        self.assertFalse(payload["results"][0]["ok"])
        self.assertEqual(payload["results"][0]["error"], "failed to verify existing OpenViking target")
        self.assertNotIn("write", [command[1] for command in commands])

    def test_ov_existing_content_result_verifies_matching_target(self) -> None:
        calls: list[tuple[list[str], float | None]] = []

        original = agent_basics_ov.run_command_env
        try:
            def fake_run(command: list[str], timeout: float | None = 30, env: dict[str, str] | None = None) -> dict[str, object]:
                calls.append((command, timeout))
                return {
                    "ok": True,
                    "command": command,
                    "returncode": 0,
                    "stdout": "hello\n",
                    "stderr": "",
                }

            agent_basics_ov.run_command_env = fake_run
            result = agent_basics_ov.ov_existing_content_result(Path("/tmp/ov"), "viking://target", "hello\n", timeout=9)
        finally:
            agent_basics_ov.run_command_env = original

        assert result is not None
        self.assertTrue(result["ok"])
        self.assertTrue(result["verified_existing"])
        self.assertEqual(calls[0][1], 9)

    def test_ov_import_repo_memory_reports_parent_failure_without_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "agent-basics"
            memory_path = repo / ".agents" / "memory" / "memories" / "cases" / "case.md"
            memory_path.parent.mkdir(parents=True)
            memory_path.write_text(
                "---\n"
                "record_kind: memory\n"
                "ov_category: cases\n"
                "title: Example case\n"
                "requires_human_review: false\n"
                "---\n"
                "\n"
                "# Example case\n",
                encoding="utf-8",
            )

            calls: list[tuple[list[str], float | None]] = []

            def fake_run(command: list[str], timeout: float | None = 30, env: dict[str, str] | None = None) -> dict[str, object]:
                calls.append((command, timeout))
                if command[1] == "health":
                    return {"ok": True, "command": command, "stdout": "{}", "stderr": "", "returncode": 0}
                if command[1] == "read":
                    return {"ok": False, "command": command, "stdout": "", "stderr": "not found", "returncode": 1}
                if command[1] == "mkdir" and command[2].endswith("/cases"):
                    return {
                        "ok": False,
                        "command": command,
                        "stdout": "",
                        "stderr": "resource is busy and cannot be written now",
                        "returncode": 1,
                    }
                return {"ok": True, "command": command, "stdout": "{}", "stderr": "", "returncode": 0}

            original_find_ov_bin = agent_basics_ov.find_ov_bin
            original_run_command_env = agent_basics_ov.run_command_env
            try:
                agent_basics_ov.find_ov_bin = lambda: Path("/tmp/ov")
                agent_basics_ov.run_command_env = fake_run
                output = io.StringIO()
                with redirect_stdout(output):
                    result = agent_basics_ov.command_ov_import_repo_memory(
                        SimpleNamespace(
                            repo=str(repo),
                            target=None,
                            memory_target=agent_basics_ov.DEFAULT_OV_MEMORY_TARGET,
                            timeout=agent_basics_ov.DEFAULT_OV_VLM_TIMEOUT_SECONDS,
                            quick_timeout=4,
                            include_review=False,
                            force=False,
                            dry_run=False,
                            wait=False,
                            wait_memory=False,
                            wait_resources=False,
                            busy_retries=0,
                            busy_delay=0,
                            write=False,
                        )
                    )
            finally:
                agent_basics_ov.find_ov_bin = original_find_ov_bin
                agent_basics_ov.run_command_env = original_run_command_env

        payload = json.loads(output.getvalue())
        commands = [command for command, _timeout in calls]

        self.assertEqual(result, 1)
        self.assertFalse(payload["ok"])
        self.assertFalse(payload["results"][0]["ok"])
        self.assertEqual(payload["results"][0]["error"], "failed to create OpenViking parent URI")
        self.assertNotIn("write", [command[1] for command in commands])
        for command, timeout in calls:
            if command[1] in {"health", "mkdir", "read"}:
                self.assertEqual(timeout, 4)

    def test_ov_import_repo_memory_does_not_write_when_target_stat_times_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "agent-basics"
            memory_path = repo / ".agents" / "memory" / "memories" / "cases" / "case.md"
            memory_path.parent.mkdir(parents=True)
            memory_path.write_text(
                "---\n"
                "record_kind: memory\n"
                "ov_category: cases\n"
                "title: Example case\n"
                "requires_human_review: false\n"
                "---\n"
                "\n"
                "# Example case\n",
                encoding="utf-8",
            )

            calls: list[tuple[list[str], float | None]] = []

            def fake_run(command: list[str], timeout: float | None = 30, env: dict[str, str] | None = None) -> dict[str, object]:
                calls.append((command, timeout))
                if command[1] == "health":
                    return {"ok": True, "command": command, "stdout": "{}", "stderr": "", "returncode": 0}
                if command[1] == "read":
                    return {"ok": False, "command": command, "stdout": "", "stderr": "not found", "returncode": 1}
                if command[1] == "stat":
                    return {
                        "ok": False,
                        "command": command,
                        "stdout": "",
                        "stderr": "",
                        "error": "timed out after 4s",
                    }
                return {"ok": True, "command": command, "stdout": "{}", "stderr": "", "returncode": 0}

            original_find_ov_bin = agent_basics_ov.find_ov_bin
            original_run_command_env = agent_basics_ov.run_command_env
            try:
                agent_basics_ov.find_ov_bin = lambda: Path("/tmp/ov")
                agent_basics_ov.run_command_env = fake_run
                output = io.StringIO()
                with redirect_stdout(output):
                    result = agent_basics_ov.command_ov_import_repo_memory(
                        SimpleNamespace(
                            repo=str(repo),
                            target=None,
                            memory_target=agent_basics_ov.DEFAULT_OV_MEMORY_TARGET,
                            timeout=agent_basics_ov.DEFAULT_OV_VLM_TIMEOUT_SECONDS,
                            quick_timeout=4,
                            include_review=False,
                            force=False,
                            dry_run=False,
                            wait=False,
                            wait_memory=False,
                            wait_resources=False,
                            busy_retries=0,
                            busy_delay=0,
                            write=False,
                        )
                    )
            finally:
                agent_basics_ov.find_ov_bin = original_find_ov_bin
                agent_basics_ov.run_command_env = original_run_command_env

        payload = json.loads(output.getvalue())
        commands = [command for command, _timeout in calls]

        self.assertEqual(result, 1)
        self.assertFalse(payload["results"][0]["ok"])
        self.assertEqual(payload["results"][0]["error"], "failed to inspect OpenViking target")
        self.assertNotIn("write", [command[1] for command in commands])

    def test_retry_busy_can_wait_for_openviking_background_work(self) -> None:
        calls: list[tuple[list[str], float | None]] = []

        def fake_run(command: list[str], timeout: float | None = 30, env: dict[str, str] | None = None) -> dict[str, object]:
            calls.append((command, timeout))
            if command[1] == "wait":
                return {"ok": True, "command": command, "stdout": "waited", "stderr": "", "returncode": 0}
            if len([command for command, _timeout in calls if command[1] == "write"]) == 1:
                return {
                    "ok": False,
                    "command": command,
                    "stdout": "",
                    "stderr": "resource is busy and cannot be written now",
                    "returncode": 1,
                }
            return {"ok": True, "command": command, "stdout": "{}", "stderr": "", "returncode": 0}

        original = agent_basics_ov.run_command_env
        original_sleep = agent_basics_ov.time.sleep
        try:
            agent_basics_ov.run_command_env = fake_run
            agent_basics_ov.time.sleep = lambda _seconds: None
            result = agent_basics_ov.run_command_retry_busy(
                ["/tmp/ov", "write", "viking://target"],
                retries=1,
                delay=0,
                wait_command=["/tmp/ov", "wait"],
                timeout=2,
                wait_timeout=3,
            )
        finally:
            agent_basics_ov.run_command_env = original
            agent_basics_ov.time.sleep = original_sleep

        self.assertTrue(result["ok"])
        self.assertEqual(result["busy_retries"], 1)
        self.assertEqual(result["busy_waits"], 1)
        self.assertEqual([command[1] for command, _timeout in calls], ["write", "wait", "write"])
        self.assertEqual([timeout for _command, timeout in calls], [2, 3, 2])

    def test_ov_search_payload_scopes_every_category_to_repo(self) -> None:
        commands: list[list[str]] = []

        def fake_run(command: list[str], timeout: float | None = 30) -> dict[str, object]:
            commands.append(command)
            scope = command[command.index("--uri") + 1]
            result = {"memories": [], "resources": [], "skills": [], "total": 0}
            if scope.endswith("/preferences/projects/agent-basics"):
                result["memories"] = [
                    {
                        "context_type": "memory",
                        "uri": "viking://user/default/memories/preferences/projects/agent-basics/example.md",
                        "score": 0.9,
                    }
                ]
                result["total"] = 1
            if scope == "viking://resources/projects/agent-basics":
                result["resources"] = [
                    {
                        "context_type": "resource",
                        "uri": "viking://resources/projects/agent-basics/README.md",
                        "score": 0.8,
                    }
                ]
                result["total"] = 1
            return {
                "ok": True,
                "command": command,
                "returncode": 0,
                "stdout": json.dumps({"ok": True, "result": result}),
                "stderr": "",
                "elapsed_seconds": 0.01,
            }

        original_find_ov_bin = agent_basics_ov.find_ov_bin
        original_run_command = agent_basics_ov.run_command
        try:
            agent_basics_ov.find_ov_bin = lambda: Path("/tmp/ov")
            agent_basics_ov.run_command = fake_run
            payload = agent_basics_ov.ov_search_payload(
                Path("/tmp/agent-basics"),
                query="repo memory",
                limit=5,
            )
        finally:
            agent_basics_ov.find_ov_bin = original_find_ov_bin
            agent_basics_ov.run_command = original_run_command

        scopes = [command[command.index("--uri") + 1] for command in commands]
        self.assertTrue(payload["ok"])
        self.assertIn("viking://resources/projects/agent-basics", scopes)
        self.assertIn("viking://user/default/memories/preferences/projects/agent-basics", scopes)
        self.assertEqual(
            payload["result"]["memories"][0]["uri"],
            "viking://user/default/memories/preferences/projects/agent-basics/example.md",
        )
        self.assertNotIn("stdout", payload["commands"][0])

    def test_ov_search_payload_filters_sibling_repo_results(self) -> None:
        commands: list[list[str]] = []

        def fake_run(command: list[str], timeout: float | None = 30) -> dict[str, object]:
            commands.append(command)
            scope = command[command.index("--uri") + 1]
            result = {"memories": [], "resources": [], "skills": [], "total": 0}
            if scope == "viking://resources/projects/agent":
                result["resources"] = [
                    {
                        "context_type": "resource",
                        "uri": "viking://resources/projects/agent/resources/README.md",
                        "score": 0.9,
                    },
                    {
                        "context_type": "resource",
                        "uri": "viking://resources/projects/agent-tools/resources/README.md",
                        "score": 0.95,
                    },
                ]
            if scope.endswith("/preferences/projects/agent"):
                result["memories"] = [
                    {
                        "context_type": "memory",
                        "uri": "viking://user/default/memories/preferences/projects/agent/prefer.md",
                        "score": 0.9,
                    },
                    {
                        "context_type": "memory",
                        "uri": "viking://user/default/memories/preferences/projects/agent-tools/prefer.md",
                        "score": 0.95,
                    },
                ]
            result["total"] = len(result["memories"]) + len(result["resources"]) + len(result["skills"])
            return {
                "ok": True,
                "command": command,
                "returncode": 0,
                "stdout": json.dumps({"ok": True, "result": result}),
                "stderr": "",
                "elapsed_seconds": 0.01,
            }

        original_find_ov_bin = agent_basics_ov.find_ov_bin
        original_run_command = agent_basics_ov.run_command
        try:
            agent_basics_ov.find_ov_bin = lambda: Path("/tmp/ov")
            agent_basics_ov.run_command = fake_run
            payload = agent_basics_ov.ov_search_payload(Path("/tmp/agent"), query="repo memory", limit=5)
        finally:
            agent_basics_ov.find_ov_bin = original_find_ov_bin
            agent_basics_ov.run_command = original_run_command

        result_uris = [
            item["uri"]
            for key in ["memories", "resources", "skills"]
            for item in payload["result"][key]
        ]
        scopes = [command[command.index("--uri") + 1] for command in commands]
        self.assertTrue(payload["ok"])
        self.assertIn("viking://resources/projects/agent", scopes)
        self.assertNotIn("viking://resources/projects/agent-tools", scopes)
        self.assertEqual(
            result_uris,
            [
                "viking://user/default/memories/preferences/projects/agent/prefer.md",
                "viking://resources/projects/agent/resources/README.md",
            ],
        )

    def test_ov_search_payload_uses_distinct_scopes_for_two_repos(self) -> None:
        commands: list[list[str]] = []

        def fake_run(command: list[str], timeout: float | None = 30) -> dict[str, object]:
            commands.append(command)
            return {
                "ok": True,
                "command": command,
                "returncode": 0,
                "stdout": json.dumps({"ok": True, "result": {"memories": [], "resources": [], "skills": [], "total": 0}}),
                "stderr": "",
                "elapsed_seconds": 0.01,
            }

        original_find_ov_bin = agent_basics_ov.find_ov_bin
        original_run_command = agent_basics_ov.run_command
        try:
            agent_basics_ov.find_ov_bin = lambda: Path("/tmp/ov")
            agent_basics_ov.run_command = fake_run
            payload_a = agent_basics_ov.ov_search_payload(Path("/tmp/Agent"), query="repo memory", limit=5)
            payload_b = agent_basics_ov.ov_search_payload(Path("/tmp/Agent Tools"), query="repo memory", limit=5)
        finally:
            agent_basics_ov.find_ov_bin = original_find_ov_bin
            agent_basics_ov.run_command = original_run_command

        self.assertTrue(payload_a["ok"])
        self.assertTrue(payload_b["ok"])
        self.assertIn("viking://resources/projects/agent", payload_a["scopes"])
        self.assertIn("viking://resources/projects/agent-tools", payload_b["scopes"])
        self.assertFalse(set(payload_a["scopes"]) & set(payload_b["scopes"]))

    def test_ov_read_rejects_global_uri_without_explicit_opt_in(self) -> None:
        payload = agent_basics_ov.ov_read_payload(
            Path("/tmp/agent-basics"),
            uri="viking://resources/projects/other-repo/README.md",
        )

        self.assertFalse(payload["ok"])
        self.assertIn("--allow-global", payload["error"])

    def test_ov_read_payload_two_repos_have_distinct_namespace_permissions(self) -> None:
        commands: list[list[str]] = []

        def fake_run(command: list[str], timeout: float | None = 30) -> dict[str, object]:
            commands.append(command)
            return {"ok": True, "command": command, "returncode": 0, "stdout": "content", "stderr": ""}

        original_find_ov_bin = agent_basics_ov.find_ov_bin
        original_run_command = agent_basics_ov.run_command
        try:
            agent_basics_ov.find_ov_bin = lambda: Path("/tmp/ov")
            agent_basics_ov.run_command = fake_run
            repo_a = Path("/tmp/Agent")
            repo_b = Path("/tmp/Agent Tools")
            uri_a = "viking://resources/projects/agent/resources/README.md"
            uri_b = "viking://resources/projects/agent-tools/resources/README.md"

            accepted_a = agent_basics_ov.ov_read_payload(repo_a, uri=uri_a)
            rejected_a_to_b = agent_basics_ov.ov_read_payload(repo_a, uri=uri_b)
            accepted_b = agent_basics_ov.ov_read_payload(repo_b, uri=uri_b)
            rejected_b_to_a = agent_basics_ov.ov_read_payload(repo_b, uri=uri_a)
        finally:
            agent_basics_ov.find_ov_bin = original_find_ov_bin
            agent_basics_ov.run_command = original_run_command

        self.assertTrue(accepted_a["ok"])
        self.assertTrue(accepted_b["ok"])
        self.assertFalse(rejected_a_to_b["ok"])
        self.assertFalse(rejected_b_to_a["ok"])
        self.assertEqual(accepted_a["repo_slug"], "agent")
        self.assertEqual(accepted_b["repo_slug"], "agent-tools")
        self.assertEqual([command[1] for command in commands], ["read", "stat", "read", "stat"])

    def test_ov_record_dry_run_uses_source_store_and_openviking_project_namespace(self) -> None:
        payload = agent_basics_ov.ov_record_payload(
            Path("/tmp/Agent Basics"),
            category="preferences",
            title="Prefer repo scoped OV writes",
            content="Record through agent-basics so repo source files and OV stay aligned.",
            dry_run=True,
        )

        self.assertTrue(payload["ok"])
        self.assertIn(
            "/.agents/memory/memories/preferences/",
            payload["source_path"],
        )
        self.assertIn(
            "viking://user/default/memories/preferences/projects/agent-basics/",
            payload["target"],
        )

    def test_ov_record_updates_import_state_after_successful_write(self) -> None:
        commands: list[list[str]] = []

        def fake_run(command: list[str], timeout: float | None = 30) -> dict[str, object]:
            commands.append(command)
            return {"ok": True, "command": command, "returncode": 0, "stdout": "{}", "stderr": ""}

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "Agent Basics"
            repo.mkdir()
            original_find_ov_bin = agent_basics_ov.find_ov_bin
            original_run_command = agent_basics_ov.run_command
            try:
                agent_basics_ov.find_ov_bin = lambda: Path("/tmp/ov")
                agent_basics_ov.run_command = fake_run
                payload = agent_basics_ov.ov_record_payload(
                    repo,
                    category="preferences",
                    title="Prefer synced record state",
                    content="A successful record should not leave the source store stale.",
                )
                staleness = agent_basics_ov.ov_import_staleness(repo)
                state_path_exists = Path(payload["state_path"]).is_file()
            finally:
                agent_basics_ov.find_ov_bin = original_find_ov_bin
                agent_basics_ov.run_command = original_run_command

        self.assertTrue(payload["ok"])
        self.assertTrue(state_path_exists)
        self.assertEqual(payload["state"]["method"], "write")
        self.assertEqual(payload["state"]["ok"], True)
        self.assertEqual(staleness["stale_count"], 0)
        self.assertIn("write", [command[1] for command in commands])

    def test_ov_record_dry_run_two_repos_have_distinct_source_paths_and_targets(self) -> None:
        payload_a = agent_basics_ov.ov_record_payload(
            Path("/tmp/Agent"),
            category="preferences",
            title="Prefer scoped writes",
            content="Repo A record.",
            dry_run=True,
        )
        payload_b = agent_basics_ov.ov_record_payload(
            Path("/tmp/Agent Tools"),
            category="preferences",
            title="Prefer scoped writes",
            content="Repo B record.",
            dry_run=True,
        )

        self.assertTrue(payload_a["ok"])
        self.assertTrue(payload_b["ok"])
        self.assertIn("/Agent/.agents/memory/memories/preferences/", payload_a["source_path"])
        self.assertIn("/Agent Tools/.agents/memory/memories/preferences/", payload_b["source_path"])
        self.assertIn("viking://user/default/memories/preferences/projects/agent/", payload_a["target"])
        self.assertIn("viking://user/default/memories/preferences/projects/agent-tools/", payload_b["target"])
        self.assertNotEqual(payload_a["target"], payload_b["target"])

    def test_ov_add_resource_dry_run_defaults_to_repo_resource_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "agent-basics"
            resource = repo / "docs" / "api.md"
            resource.parent.mkdir(parents=True)
            resource.write_text("# API\n", encoding="utf-8")

            payload = agent_basics_ov.ov_add_resource_payload(
                repo,
                source="docs/api.md",
                dry_run=True,
            )

        self.assertTrue(payload["ok"])
        self.assertEqual(
            payload["target"],
            "viking://resources/projects/agent-basics/resources/docs/api.md",
        )

    def test_ov_add_resource_dry_run_two_repos_have_distinct_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_a = Path(tmp) / "Agent"
            repo_b = Path(tmp) / "Agent Tools"
            resource_a = repo_a / "docs" / "api.md"
            resource_b = repo_b / "docs" / "api.md"
            resource_a.parent.mkdir(parents=True)
            resource_b.parent.mkdir(parents=True)
            resource_a.write_text("# API A\n", encoding="utf-8")
            resource_b.write_text("# API B\n", encoding="utf-8")

            payload_a = agent_basics_ov.ov_add_resource_payload(repo_a, source="docs/api.md", dry_run=True)
            payload_b = agent_basics_ov.ov_add_resource_payload(repo_b, source="docs/api.md", dry_run=True)
            rejected = agent_basics_ov.ov_add_resource_payload(
                repo_a,
                source="docs/api.md",
                target="viking://resources/projects/agent-tools/resources/docs/api.md",
                dry_run=True,
            )

        self.assertTrue(payload_a["ok"])
        self.assertTrue(payload_b["ok"])
        self.assertEqual(payload_a["target"], "viking://resources/projects/agent/resources/docs/api.md")
        self.assertEqual(payload_b["target"], "viking://resources/projects/agent-tools/resources/docs/api.md")
        self.assertFalse(rejected["ok"])
        self.assertIn("repo namespace", rejected["error"])

    def test_ov_default_config_supports_custom_api_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "ov.conf"
            cli_config_path = Path(tmp) / "ovcli.conf"
            with redirect_stdout(io.StringIO()):
                result = agent_basics_ov.command_ov_write_default_config(
                    SimpleNamespace(
                        config=str(config_path),
                        cli_config=str(cli_config_path),
                        home=str(Path(tmp) / "openviking"),
                        provider="custom",
                        base_url="http://127.0.0.1:8000",
                        provider_base=None,
                        api_key="test-key",
                        chat_model="custom-chat",
                        embedding_model="custom-embedding",
                        embedding_dimension=768,
                        vlm_timeout=agent_basics_ov.DEFAULT_OV_VLM_TIMEOUT_SECONDS,
                        server_url="http://127.0.0.1:1933",
                        cli_timeout=agent_basics_ov.DEFAULT_OV_VLM_TIMEOUT_SECONDS,
                        force=False,
                    )
                )
            payload = agent_basics_ov.load_json_file(config_path)
            cli_payload = agent_basics_ov.load_json_file(cli_config_path)

        self.assertEqual(result, 0)
        assert payload is not None
        assert cli_payload is not None
        self.assertGreater(payload["vlm"]["timeout"], 0)
        self.assertEqual(payload["vlm"]["api_base"], "http://127.0.0.1:8000/v1")
        self.assertEqual(payload["vlm"]["api_key"], "test-key")
        self.assertEqual(payload["vlm"]["model"], "custom-chat")
        self.assertEqual(payload["embedding"]["dense"]["model"], "custom-embedding")
        self.assertEqual(cli_payload["timeout"], agent_basics_ov.DEFAULT_OV_VLM_TIMEOUT_SECONDS)

    def test_merge_no_proxy_preserves_existing_and_adds_localhost_bypass(self) -> None:
        merged = agent_basics_ov.merge_no_proxy("example.com,localhost")
        values = merged.split(",")

        self.assertIn("example.com", values)
        self.assertIn("localhost", values)
        self.assertIn("127.0.0.1", values)
        self.assertIn("::1", values)
        self.assertEqual(values.count("localhost"), 1)

    def test_ov_server_dry_run_wraps_user_level_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server_path = Path(tmp) / "openviking-server"
            config_path = Path(tmp) / "ov.conf"
            server_path.write_text("#!/bin/sh\n", encoding="utf-8")
            server_path.chmod(0o755)
            config_path.write_text("{}\n", encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                result = agent_basics_ov.command_ov_server(
                    SimpleNamespace(
                        server_bin=str(server_path),
                        config=str(config_path),
                        host="127.0.0.1",
                        port=1933,
                        workers=1,
                        bot=False,
                        with_bot=False,
                        dry_run=True,
                    )
                )

        payload = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(
            payload["command"],
            [
                str(server_path),
                "--config",
                str(config_path),
                "--host",
                "127.0.0.1",
                "--port",
                "1933",
                "--workers",
                "1",
            ],
        )

    def test_ov_service_plist_wraps_user_level_openviking_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "openviking"
            server_path = home / "venv" / "bin" / "openviking-server"
            config_path = home / "ov.conf"

            payload = agent_basics_ov.ov_service_plist_payload(
                label="com.agent-basics.test.openviking",
                home=home,
                server_bin=server_path,
                config=config_path,
                no_proxy="example.com,localhost,127.0.0.1,::1",
            )
            plist_text = agent_basics_ov.ov_service_plist_text(payload)

        self.assertIn("<key>Label</key>", plist_text)
        self.assertIn("<string>com.agent-basics.test.openviking</string>", plist_text)
        self.assertIn(f"<string>{server_path}</string>", plist_text)
        self.assertIn(f"<string>{config_path}</string>", plist_text)
        self.assertIn("<key>RunAtLoad</key>\n    <true/>", plist_text)
        self.assertIn("<key>KeepAlive</key>\n    <true/>", plist_text)
        self.assertIn("<string>example.com,localhost,127.0.0.1,::1</string>", plist_text)
        self.assertIn(f"<string>{home / 'logs' / 'openviking-server.out.log'}</string>", plist_text)

    def test_ov_service_install_dry_run_does_not_write_launch_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "openviking"
            server_path = home / "venv" / "bin" / "openviking-server"
            config_path = home / "ov.conf"
            plist_path = Path(tmp) / "com.agent-basics.test.openviking.plist"
            server_path.parent.mkdir(parents=True)
            server_path.write_text("#!/bin/sh\n", encoding="utf-8")
            server_path.chmod(0o755)
            config_path.write_text("{}\n", encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                result = agent_basics_ov.command_ov_service(
                    SimpleNamespace(
                        service_action="install",
                        home=str(home),
                        server_bin=str(server_path),
                        config=str(config_path),
                        label="com.agent-basics.test.openviking",
                        plist=str(plist_path),
                        dry_run=True,
                        force=False,
                        no_load=False,
                    )
                )

        payload = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["dry_run"])
        self.assertTrue(payload["would_change_plist"])
        self.assertFalse(plist_path.exists())
        self.assertIn(["launchctl", "bootstrap", payload["target"].rsplit("/", 1)[0], str(plist_path)], payload["commands"])
        self.assertEqual(payload["plist_payload"]["ProgramArguments"], [str(server_path), "--config", str(config_path)])

    def test_ov_service_permission_error_returns_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "openviking"
            server_path = home / "openviking"
            config_path = home / "ov.conf"
            plist_path = Path(tmp) / "com.agent-basics.test.openviking.plist"
            home.mkdir(parents=True)
            server_path.write_text("#!/bin/sh\n", encoding="utf-8")
            server_path.chmod(0o755)
            config_path.write_text("{}\n", encoding="utf-8")

            original_mkdir = agent_basics_ov.Path.mkdir
            original_platform_system = agent_basics_ov.platform.system

            def fake_mkdir(path: Path, *args: object, **kwargs: object) -> None:
                if Path(path).name == "logs":
                    raise PermissionError(1, "Operation not permitted", str(path))
                return original_mkdir(path, *args, **kwargs)

            output = io.StringIO()
            try:
                agent_basics_ov.Path.mkdir = fake_mkdir
                agent_basics_ov.platform.system = lambda: "Darwin"
                with redirect_stdout(output):
                    result = agent_basics_ov.command_ov_service(
                        SimpleNamespace(
                            service_action="install",
                            home=str(home),
                            server_bin=str(server_path),
                            config=str(config_path),
                            label="com.agent-basics.test.openviking",
                            plist=str(plist_path),
                            timeout=1,
                            dry_run=False,
                            force=False,
                            no_load=True,
                            repo_local=False,
                        )
                    )
            finally:
                agent_basics_ov.Path.mkdir = original_mkdir
                agent_basics_ov.platform.system = original_platform_system

        payload = json.loads(output.getvalue())
        self.assertEqual(result, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["exception_type"], "PermissionError")
        self.assertIn("failed to write OpenViking service files", payload["error"])
        self.assertFalse(plist_path.exists())

    def test_ov_bootstrap_dry_run_reports_install_config_and_service_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "openviking"
            ov_bin = home / "venv" / "bin" / "ov"
            ov_bin.parent.mkdir(parents=True)
            ov_bin.write_text("#!/bin/sh\n", encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                result = agent_basics_ov.command_ov_bootstrap_system(
                    SimpleNamespace(
                        home=str(home),
                        python="3.12",
                        package="openviking",
                        config=None,
                        cli_config=None,
                        lmstudio_base="http://127.0.0.1:1234",
                        chat_model=agent_basics_ov.DEFAULT_CHAT_MODEL,
                        embedding_model=agent_basics_ov.DEFAULT_EMBEDDING_MODEL,
                        embedding_dimension=768,
                        vlm_timeout=agent_basics_ov.DEFAULT_OV_VLM_TIMEOUT_SECONDS,
                        server_url="http://127.0.0.1:1933",
                        cli_timeout=agent_basics_ov.DEFAULT_OV_VLM_TIMEOUT_SECONDS,
                        service="never",
                        service_best_effort=False,
                        server_bin=None,
                        label=agent_basics_ov.DEFAULT_OV_SERVICE_LABEL,
                        plist=None,
                        service_timeout=agent_basics_ov.DEFAULT_OV_SERVICE_COMMAND_TIMEOUT_SECONDS,
                        force_install=False,
                        force_config=False,
                        force_service=False,
                        no_load=False,
                        dry_run=True,
                    )
                )

        payload = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["dry_run"])
        self.assertFalse(payload["install"]["needed"])
        self.assertTrue(payload["package_server"]["needed"])
        self.assertTrue(payload["config"]["needed"])
        self.assertFalse(payload["service"]["enabled"])
        self.assertEqual(payload["service"]["skipped_reason"], "disabled by --service never")

    def test_ov_bootstrap_custom_provider_skips_bundled_runtime_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "openviking"
            output = io.StringIO()
            with redirect_stdout(output):
                result = agent_basics_ov.command_ov_bootstrap_system(
                    SimpleNamespace(
                        home=str(home),
                        python="3.12",
                        package="openviking",
                        config=None,
                        cli_config=None,
                        provider="custom",
                        runtime="auto",
                        runtime_best_effort=False,
                        base_url="http://127.0.0.1:8000",
                        provider_base=None,
                        api_key="test-key",
                        chat_model="custom-chat",
                        embedding_model="custom-embedding",
                        embedding_dimension=768,
                        vlm_timeout=agent_basics_ov.DEFAULT_OV_VLM_TIMEOUT_SECONDS,
                        server_url="http://127.0.0.1:1933",
                        cli_timeout=agent_basics_ov.DEFAULT_OV_VLM_TIMEOUT_SECONDS,
                        service="never",
                        service_best_effort=False,
                        server_bin=None,
                        label=agent_basics_ov.DEFAULT_OV_SERVICE_LABEL,
                        plist=None,
                        service_timeout=agent_basics_ov.DEFAULT_OV_SERVICE_COMMAND_TIMEOUT_SECONDS,
                        force_install=False,
                        force_config=False,
                        force_service=False,
                        no_load=False,
                        dry_run=True,
                    )
                )

        payload = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(payload["runtime"]["provider"], "none")
        self.assertTrue(payload["runtime"]["skipped"])

    def test_ov_bootstrap_installs_config_and_macos_service(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "openviking"
            server_path = home / "venv" / "bin" / "openviking-server"
            python_bin = home / "venv" / "bin" / "python"
            native_binding = home / "venv" / "lib" / "python3.12" / "site-packages" / "openviking" / "lib" / "ragfs_python.abi3.so"
            plist_path = Path(tmp) / "com.agent-basics.test.openviking.plist"
            server_path.parent.mkdir(parents=True)
            server_path.write_text("#!/bin/sh\n", encoding="utf-8")
            server_path.chmod(0o755)
            python_bin.write_text("#!/bin/sh\n", encoding="utf-8")
            python_bin.chmod(0o755)
            native_binding.parent.mkdir(parents=True)
            native_binding.write_bytes(b"native")
            commands: list[list[str]] = []

            def fake_run(command: list[str], timeout: float | None = 30) -> dict[str, object]:
                commands.append(command)
                if command[:2] == [str(python_bin), "-c"] and "find_spec('openviking')" in command[2]:
                    return {
                        "ok": True,
                        "command": command,
                        "returncode": 0,
                        "stdout": f"{native_binding}\n",
                        "stderr": "",
                    }
                if command[:2] == [str(python_bin), "-c"] and "m.version('openviking')" in command[2]:
                    return {
                        "ok": True,
                        "command": command,
                        "returncode": 0,
                        "stdout": "0.3.14\n",
                        "stderr": "",
                    }
                if "--distpath" in command:
                    dist_path = Path(command[command.index("--distpath") + 1])
                    dist_path.mkdir(parents=True, exist_ok=True)
                    built = dist_path / "openviking"
                    built.write_text("#!/bin/sh\n", encoding="utf-8")
                    built.chmod(0o755)
                return {"ok": True, "command": command, "returncode": 0, "stdout": "", "stderr": ""}

            original_run_command = agent_basics_ov.run_command
            original_shutil_which = agent_basics_ov.shutil_which
            original_platform_system = agent_basics_ov.platform.system
            try:
                agent_basics_ov.run_command = fake_run
                agent_basics_ov.shutil_which = lambda name: "/tmp/uv" if name == "uv" else None
                agent_basics_ov.platform.system = lambda: "Darwin"
                output = io.StringIO()
                with redirect_stdout(output):
                    result = agent_basics_ov.command_ov_bootstrap_system(
                        SimpleNamespace(
                            home=str(home),
                            python="3.12",
                            package="openviking",
                            config=None,
                            cli_config=None,
                            provider="mlx",
                            runtime="none",
                            runtime_best_effort=False,
                            lmstudio_base="http://127.0.0.1:1234",
                            chat_model=agent_basics_ov.DEFAULT_CHAT_MODEL,
                            embedding_model=agent_basics_ov.DEFAULT_EMBEDDING_MODEL,
                            embedding_dimension=768,
                            vlm_timeout=agent_basics_ov.DEFAULT_OV_VLM_TIMEOUT_SECONDS,
                            server_url="http://127.0.0.1:1933",
                            cli_timeout=agent_basics_ov.DEFAULT_OV_VLM_TIMEOUT_SECONDS,
                            service="auto",
                            service_best_effort=False,
                            server_bin=str(server_path),
                            label="com.agent-basics.test.openviking",
                            plist=str(plist_path),
                            service_timeout=agent_basics_ov.DEFAULT_OV_SERVICE_COMMAND_TIMEOUT_SECONDS,
                            force_install=False,
                            force_config=False,
                            force_service=False,
                            no_load=True,
                            dry_run=False,
                        )
                    )
            finally:
                agent_basics_ov.run_command = original_run_command
                agent_basics_ov.shutil_which = original_shutil_which
                agent_basics_ov.platform.system = original_platform_system

            payload = json.loads(output.getvalue())
            config_exists = (home / "ov.conf").is_file()
            cli_config_exists = (home / "ovcli.conf").is_file()
            plist_exists = plist_path.is_file()

        self.assertEqual(result, 0)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["service_enabled"])
        self.assertEqual(
            [step["name"] for step in payload["steps"]],
            ["install-system", "package-server", "write-default-config", "service install", "runtime bootstrap"],
        )
        self.assertTrue(payload["steps"][4]["payload"]["skipped"])
        self.assertEqual(commands[0], ["/tmp/uv", "venv", "--python", "3.12", str(home / "venv")])
        self.assertEqual(commands[1][:4], ["/tmp/uv", "pip", "install", "--python"])
        self.assertTrue(config_exists)
        self.assertTrue(cli_config_exists)
        self.assertTrue(plist_exists)

    def test_ov_native_memory_paths_map_to_openviking_categories(self) -> None:
        category, reason, review = agent_basics_ov.legacy_to_ov_category(
            Path(".agents/memory/memories/preferences/example.md"),
            "",
            "The user wants .agents/memory to stay as the OV source store.",
        )
        self.assertEqual(category, "preferences")
        self.assertEqual(reason, "OV-native preference memory")
        self.assertFalse(review)

        category, reason, review = agent_basics_ov.legacy_to_ov_category(
            Path(".agents/memory/resources/sources/example.md"),
            "",
            "https://example.com",
        )
        self.assertEqual(category, "none")
        self.assertEqual(reason, "OV-native resource, not memory")
        self.assertFalse(review)

        category, reason, review = agent_basics_ov.legacy_to_ov_category(
            Path(".agents/memory/imports/legacy-memory.md"),
            "",
            "Raw copied material.",
        )
        self.assertEqual(category, "none")
        self.assertEqual(reason, "copied source material awaiting adaptation")
        self.assertTrue(review)


if __name__ == "__main__":
    unittest.main()
