#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import os
import platform
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any


DEFAULT_OLLAMA_BASE = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_API_KEY = "ollama"
DEFAULT_LM_STUDIO_BASE = "http://127.0.0.1:1234"
DEFAULT_CHAT_MODEL = "gemma4:e2b"
DEFAULT_EMBEDDING_MODEL = "embeddinggemma:latest"
DEFAULT_RUNTIME_PROVIDER = "ollama"
DEFAULT_LMSTUDIO_CHAT_MODEL = "google/gemma-4-e2b"
DEFAULT_LMSTUDIO_EMBEDDING_MODEL = "text-embedding-embeddinggemma-300m-qat"
DEFAULT_OV_HOME = Path.home() / ".openviking"
DEFAULT_OV_BIN = DEFAULT_OV_HOME / "venv" / "bin" / "ov"
DEFAULT_OV_CONFIG = DEFAULT_OV_HOME / "ov.conf"
DEFAULT_OV_CLI_CONFIG = DEFAULT_OV_HOME / "ovcli.conf"
DEFAULT_OV_SERVER = DEFAULT_OV_HOME / "venv" / "bin" / "openviking-server"
DEFAULT_OV_SERVICE_LABEL = "com.agent-basics.openviking"
DEFAULT_OV_SERVICE_PLIST = Path.home() / "Library" / "LaunchAgents" / f"{DEFAULT_OV_SERVICE_LABEL}.plist"
DEFAULT_OV_SERVICE_COMMAND_TIMEOUT_SECONDS = 120
DEFAULT_OV_VLM_TIMEOUT_SECONDS = 86400
DEFAULT_OV_MEMORY_TARGET = "viking://user/default/memories"
DEFAULT_OV_RESOURCE_TARGET = "viking://resources/projects"
OV_HOOK_MARKER = "agent-basics-openviking-hook"
LEGACY_MEMORY_HOOK_MARKER = "agent-basics memory hook"
DEFAULT_LMSTUDIO_HOME = Path.home() / ".lmstudio"
DEFAULT_LMSTUDIO_APP = Path("/Applications/LM Studio.app")
DEFAULT_LMS_BIN = DEFAULT_LMSTUDIO_HOME / "bin" / "lms"
DEFAULT_LMSTUDIO_CASK = "lm-studio"
DEFAULT_LMSTUDIO_PORT = 1234
DEFAULT_LMSTUDIO_SERVICE_LABEL = "com.agent-basics.lmstudio"
DEFAULT_LMSTUDIO_SERVICE_PLIST = Path.home() / "Library" / "LaunchAgents" / f"{DEFAULT_LMSTUDIO_SERVICE_LABEL}.plist"
DEFAULT_LMSTUDIO_MIN_MEMORY_GB = 16.0
DEFAULT_LMSTUDIO_CHAT_DOWNLOAD = DEFAULT_LMSTUDIO_CHAT_MODEL
DEFAULT_LMSTUDIO_EMBEDDING_DOWNLOAD = DEFAULT_LMSTUDIO_EMBEDDING_MODEL
LMSTUDIO_DEFAULT_CONFIG_ROOT = Path(".internal") / "user-concrete-model-default-config"
GEMMA_LLM_KEYS = {"google/gemma-4-e2b", "google/gemma-4-e4b"}
LMSTUDIO_KNOWN_CONFIG_PATHS = {
    DEFAULT_LMSTUDIO_CHAT_MODEL: [
        Path("google") / "gemma-4-e2b.json",
        Path("lmstudio-community") / "gemma-4-E2B-it-GGUF" / "gemma-4-E2B-it-Q4_K_M.gguf.json",
    ],
    DEFAULT_LMSTUDIO_EMBEDDING_MODEL: [
        Path("lmstudio-community") / "embeddinggemma-300m-qat-GGUF" / "embeddinggemma-300m-qat-Q4_0.gguf.json",
    ],
}
LMSTUDIO_REPORTED_LOAD_KEYS = (
    "context_length",
    "eval_batch_size",
    "flash_attention",
    "offload_kv_cache_to_gpu",
)
LMSTUDIO_ROUTING_DEFAULT_KEYS = {
    "llm.prediction.structured",
    "llm.prediction.systemPrompt",
}

OV_MEMORY_CATEGORIES = [
    "profile",
    "preferences",
    "entities",
    "events",
    "cases",
    "patterns",
    "tools",
    "skills",
]

ROUTER_SYSTEM_PROMPT = """You are an OpenViking memory routing assistant. Return no markdown, no prose, no explanation, and no fields outside the schema.

OpenViking memory categories:
- profile: who the user is; stable identity or attributes.
- preferences: what the user wants, prefers, dislikes, or habitually asks agents to do. Use semantic facets; do not mix unrelated facets.
- entities: named things and their stable attributes, including projects, systems, tools, repositories, people, organizations, and configured technologies.
- events: time-bound things that happened, are happening, or are planned, including decisions and milestones.
- cases: specific problem -> cause, solution, workaround, or outcome.
- patterns: reusable process or method for similar situations.
- tools: specific tool usage insights, parameters, success/failure patterns, and optimization.
- skills: reusable workflow or skill execution strategy.

Output splitting rules:
- If one candidate contains multiple durable ideas, output multiple items with the same input_id and different titles.
- Do not collapse a user preference, a project/system fact, and a backend fact into one item.
- Keep one independently updatable idea per item.

Record kind rules:
- Source records and URL-only items are not memories. Mark them as record_kind "resource" and ov_category "none".
- If record_kind is "resource", ov_category must be "none".
- Security rules, operating rules, procedures, preferences, facts, decisions, and cases are memories, not resources, even when they mention a tool name.
- Durable "must/never/always/do not" rules are patterns unless they are clearly user preferences, tool-specific lessons, or concrete failure cases.
- If record_kind is "memory" or "resource", action must be create, append, or needs_review. Use action "ignore" only when record_kind is "ignore".
- Each candidate may include suggested_record_kind, suggested_ov_category, and suggested_action. Follow those hints unless clearly wrong.

Tie-breakers:
- Prefer preferences over entities when the text says the user wants/prefers/dislikes something.
- Prefer entities over preferences when the text describes what a project/system/tool is or how it is configured.
- Prefer events for accepted/rejected decisions, milestones, current work, planned work, or dated facts.
- Prefer cases for concrete failures and fixes.
- Prefer patterns for repeatable instructions.
- System/component ownership and responsibility statements are entities, not skills.
- Use needs_review when a candidate conflicts with existing memory, updates a previous default, or could delete user knowledge.
"""

ROUTER_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "input_id",
                    "action",
                    "record_kind",
                    "ov_category",
                    "facet",
                    "title",
                    "abstract",
                    "overview",
                    "content",
                    "tags",
                    "certainty",
                    "requires_human_review",
                    "reason",
                ],
                "properties": {
                    "input_id": {"type": "string"},
                    "action": {
                        "type": "string",
                        "enum": ["create", "append", "ignore", "needs_review"],
                    },
                    "record_kind": {
                        "type": "string",
                        "enum": ["memory", "resource", "ignore"],
                    },
                    "ov_category": {
                        "type": "string",
                        "enum": [*OV_MEMORY_CATEGORIES, "none"],
                    },
                    "facet": {"type": "string"},
                    "title": {"type": "string"},
                    "abstract": {"type": "string"},
                    "overview": {"type": "string"},
                    "content": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "certainty": {"type": "string", "enum": ["low", "medium", "high"]},
                    "requires_human_review": {"type": "boolean"},
                    "reason": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}


def print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def repo_root_from_args(args: argparse.Namespace) -> Path:
    raw = getattr(args, "repo", None) or os.environ.get("AGENT_BASICS_REPO_ROOT") or os.getcwd()
    return Path(raw).expanduser().resolve()


def run_command(command: list[str], timeout: float | None = 30) -> dict[str, Any]:
    started = time.time()
    try:
        completed = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return {
            "ok": False,
            "command": command,
            "error": "not found",
            "elapsed_seconds": round(time.time() - started, 3),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "command": command,
            "error": f"timed out after {exc.timeout}s",
            "elapsed_seconds": round(time.time() - started, 3),
        }
    return {
        "ok": completed.returncode == 0,
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "elapsed_seconds": round(time.time() - started, 3),
    }


def result_is_busy(result: dict[str, Any]) -> bool:
    text = f"{result.get('stdout', '')}\n{result.get('stderr', '')}".lower()
    return "resource is busy" in text or "cannot be written now" in text


def run_command_retry_busy(command: list[str], *, retries: int, delay: float) -> dict[str, Any]:
    result = run_command(command, timeout=None)
    attempts = 0
    while not result["ok"] and result_is_busy(result) and attempts < retries:
        attempts += 1
        time.sleep(delay)
        result = run_command(command, timeout=None)
    if attempts:
        result["busy_retries"] = attempts
    return result


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "project"


def extract_json_object(text: str) -> Any:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    start_candidates = [index for index in [stripped.find("{"), stripped.find("[")] if index >= 0]
    if not start_candidates:
        raise ValueError("output did not contain JSON")
    start = min(start_candidates)
    return json.loads(stripped[start:])


def ov_bin_or_error() -> tuple[Path | None, dict[str, Any] | None]:
    ov_bin = find_ov_bin()
    if ov_bin:
        return ov_bin, None
    return None, {"ok": False, "error": "OpenViking CLI not found; run `agent-basics ov install-system` first"}


def ov_repo_slug(repo: Path) -> str:
    return slugify(repo.name)


def ov_repo_resource_root(repo: Path) -> str:
    return f"{DEFAULT_OV_RESOURCE_TARGET}/{ov_repo_slug(repo)}"


def ov_repo_memory_root(repo: Path, memory_base_uri: str = DEFAULT_OV_MEMORY_TARGET) -> str:
    return f"{memory_base_uri.rstrip('/')}/projects/{ov_repo_slug(repo)}"


def ov_repo_scoped_prefixes(repo: Path, memory_base_uri: str = DEFAULT_OV_MEMORY_TARGET) -> list[str]:
    repo_slug = ov_repo_slug(repo)
    return [
        f"viking://resources/projects/{repo_slug}",
        *[f"{memory_base_uri.rstrip('/')}/{category}/projects/{repo_slug}" for category in OV_MEMORY_CATEGORIES],
    ]


def uri_has_path_boundary(uri: str, prefix: str) -> bool:
    normalized_prefix = prefix.rstrip("/")
    return uri == normalized_prefix or uri.startswith(f"{normalized_prefix}/")


def ov_uri_is_repo_scoped(uri: str, repo: Path, memory_base_uri: str = DEFAULT_OV_MEMORY_TARGET) -> bool:
    repo_slug = ov_repo_slug(repo)
    memory_marker = f"/projects/{repo_slug}"
    resource_root = f"viking://resources/projects/{repo_slug}"
    return (
        uri_has_path_boundary(uri, resource_root)
        or (
            uri.startswith(memory_base_uri.rstrip("/") + "/")
            and (uri.endswith(memory_marker) or f"{memory_marker}/" in uri)
        )
    )


def filter_ov_find_result(payload: Any, repo: Path, *, include_global: bool = False) -> Any:
    if include_global or not isinstance(payload, dict):
        return payload
    result = payload.get("result")
    if not isinstance(result, dict):
        return payload
    filtered_result = dict(result)
    for key in ["memories", "resources", "skills"]:
        items = result.get(key)
        if isinstance(items, list):
            filtered_result[key] = [
                item
                for item in items
                if isinstance(item, dict) and ov_uri_is_repo_scoped(str(item.get("uri", "")), repo)
            ]
    filtered_result["total"] = sum(
        len(filtered_result.get(key, []))
        for key in ["memories", "resources", "skills"]
        if isinstance(filtered_result.get(key), list)
    )
    return {**payload, "result": filtered_result}


def ov_command_payload(command: list[str], *, timeout: float | None = None, parse_json: bool = True) -> dict[str, Any]:
    result = run_command(command, timeout=timeout)
    payload = dict(result)
    if parse_json and result.get("stdout"):
        try:
            payload["json"] = extract_json_object(str(result["stdout"]))
        except Exception as exc:
            payload["json_parse_error"] = str(exc)
    return payload


def summarize_command_payload(payload: dict[str, Any]) -> dict[str, Any]:
    summary = {
        "ok": payload.get("ok"),
        "command": payload.get("command"),
        "returncode": payload.get("returncode"),
        "elapsed_seconds": payload.get("elapsed_seconds"),
    }
    for key in ["scope", "stderr", "error", "json_parse_error", "busy_retries", "verified_existing", "already_exists"]:
        if key in payload and payload.get(key):
            summary[key] = payload[key]
    if isinstance(payload.get("json"), dict):
        parsed = payload["json"]
        summary["json_ok"] = parsed.get("ok")
        if isinstance(parsed.get("result"), dict):
            result = parsed["result"]
            summary["result_total"] = result.get("total")
    return summary


def http_json(
    base_url: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {path}: {body}") from exc
    except Exception as exc:
        return http_json_with_curl(url, path, payload, exc)
    return json.loads(text) if text else {}


def http_json_with_curl(
    url: str,
    path: str,
    payload: dict[str, Any] | None,
    original_error: Exception,
) -> dict[str, Any]:
    curl = shutil_which("curl")
    if not curl:
        raise RuntimeError(f"HTTP request failed for {path}: {original_error}") from original_error

    command = [curl, "-sS", url]
    input_text = None
    if payload is not None:
        command = [
            curl,
            "-sS",
            "-X",
            "POST",
            url,
            "-H",
            "Content-Type: application/json",
            "--data-binary",
            "@-",
        ]
        input_text = json.dumps(payload)

    completed = subprocess.run(
        command,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"HTTP request failed for {path}: {original_error}; curl fallback failed: {completed.stderr.strip()}"
        ) from original_error
    try:
        return json.loads(completed.stdout) if completed.stdout else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"HTTP response for {path} was not JSON: {completed.stdout[:500]}") from exc


def find_ov_bin() -> Path | None:
    explicit = os.environ.get("AGENT_BASICS_OV_BIN")
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.exists() else None
    if DEFAULT_OV_BIN.exists():
        return DEFAULT_OV_BIN
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / "ov"
        if candidate.exists():
            return candidate
    return None


def find_ov_server() -> Path | None:
    explicit = os.environ.get("AGENT_BASICS_OV_SERVER")
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.exists() else None
    if DEFAULT_OV_SERVER.exists():
        return DEFAULT_OV_SERVER
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / "openviking-server"
        if candidate.exists():
            return candidate
    return None


def load_json_file(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        return {"_error": str(exc)}


def default_lmstudio_config_root(home: Path) -> Path:
    return home.expanduser() / LMSTUDIO_DEFAULT_CONFIG_ROOT


def lmstudio_alias_config_path(config_root: Path, model: str) -> Path:
    parts = model.split("/")
    if len(parts) == 1:
        return config_root / f"{model}.json"
    return config_root.joinpath(*parts[:-1]) / f"{parts[-1]}.json"


def unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    result = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            result.append(path)
    return result


def lmstudio_default_config_paths(home: Path, model: str) -> list[Path]:
    config_root = default_lmstudio_config_root(home)
    paths = [lmstudio_alias_config_path(config_root, model)]
    paths.extend(config_root / relative for relative in LMSTUDIO_KNOWN_CONFIG_PATHS.get(model, []))
    return unique_paths(paths)


def lmstudio_field(key: str, value: Any) -> dict[str, Any]:
    return {"key": key, "value": value}


def lmstudio_structured_value() -> dict[str, Any]:
    return {"type": "json", "jsonSchema": ROUTER_OUTPUT_SCHEMA}


def lmstudio_desired_chat_config(
    *,
    cpu_threads: int,
    parallel: int,
    context_length: int,
    kv_cache_quantization: str,
    gpu_offload_ratio: float,
    temperature: float,
    include_routing_defaults: bool = False,
) -> dict[str, Any]:
    operation_fields = [
        lmstudio_field("llm.prediction.llama.cpuThreads", cpu_threads),
        lmstudio_field("llm.prediction.temperature", temperature),
    ]
    if include_routing_defaults:
        operation_fields.extend(
            [
                lmstudio_field("llm.prediction.structured", lmstudio_structured_value()),
                lmstudio_field("llm.prediction.systemPrompt", ROUTER_SYSTEM_PROMPT),
            ]
        )
    return {
        "preset": "",
        "operation": {"fields": operation_fields},
        "load": {
            "fields": [
                lmstudio_field("llm.load.llama.acceleration.offloadRatio", gpu_offload_ratio),
                lmstudio_field("llm.load.llama.cpuThreadPoolSize", cpu_threads),
                lmstudio_field("llm.load.numParallelSessions", parallel),
                lmstudio_field(
                    "llm.load.llama.kCacheQuantizationType",
                    {"checked": True, "value": kv_cache_quantization},
                ),
                lmstudio_field(
                    "llm.load.llama.vCacheQuantizationType",
                    {"checked": True, "value": kv_cache_quantization},
                ),
                lmstudio_field("llm.load.contextLength", context_length),
            ]
        },
    }


def lmstudio_desired_embedding_config(*, parallel: int, context_length: int) -> dict[str, Any]:
    return {
        "preset": "",
        "operation": {"fields": []},
        "load": {
            "fields": [
                lmstudio_field("llm.load.numParallelSessions", parallel),
                lmstudio_field("llm.load.contextLength", context_length),
            ]
        },
    }


def lmstudio_config_section(config: dict[str, Any], section: str) -> list[dict[str, Any]]:
    raw_section = config.get(section)
    if not isinstance(raw_section, dict):
        return []
    fields = raw_section.get("fields")
    if not isinstance(fields, list):
        return []
    return [field for field in fields if isinstance(field, dict) and isinstance(field.get("key"), str)]


def merge_lmstudio_fields(
    existing: list[dict[str, Any]],
    desired: list[dict[str, Any]],
    *,
    remove_keys: set[str] | None = None,
) -> list[dict[str, Any]]:
    remove_keys = remove_keys or set()
    desired_by_key = {field["key"]: field for field in desired}
    merged = []
    used = set()
    for field in existing:
        key = field["key"]
        if key in desired_by_key:
            merged.append(desired_by_key[key])
            used.add(key)
        elif key in remove_keys:
            continue
        else:
            merged.append(field)
    for field in desired:
        if field["key"] not in used and field["key"] not in {item["key"] for item in existing}:
            merged.append(field)
    return merged


def merge_lmstudio_config(
    existing: dict[str, Any] | None,
    desired: dict[str, Any],
    *,
    remove_operation_keys: set[str] | None = None,
) -> dict[str, Any]:
    base = existing if isinstance(existing, dict) and "_error" not in existing else {}
    merged = {
        "preset": base.get("preset", desired.get("preset", "")),
        "operation": {
            "fields": merge_lmstudio_fields(
                lmstudio_config_section(base, "operation"),
                lmstudio_config_section(desired, "operation"),
                remove_keys=remove_operation_keys,
            )
        },
        "load": {
            "fields": merge_lmstudio_fields(
                lmstudio_config_section(base, "load"),
                lmstudio_config_section(desired, "load"),
            )
        },
    }
    return merged


def summarize_lmstudio_config_value(value: Any) -> Any:
    if isinstance(value, str) and len(value) > 160:
        return f"{value[:157]}..."
    if isinstance(value, dict):
        if set(value) == {"checked", "value"}:
            return value
        return {"summary": f"object with keys: {', '.join(sorted(value))}"}
    return value


def lmstudio_config_mismatches_by_key(
    actual: dict[str, Any] | None,
    desired: dict[str, Any],
    *,
    remove_operation_keys: set[str] | None = None,
) -> list[dict[str, Any]]:
    if not actual or "_error" in actual:
        return [{"key": "*", "actual": None if not actual else actual, "desired": "valid JSON config"}]
    mismatches = []
    remove_operation_keys = remove_operation_keys or set()
    desired_operation_keys = {field["key"] for field in lmstudio_config_section(desired, "operation")}
    for field in lmstudio_config_section(actual, "operation"):
        key = field["key"]
        if key in remove_operation_keys and key not in desired_operation_keys:
            mismatches.append(
                {
                    "section": "operation",
                    "key": key,
                    "actual": summarize_lmstudio_config_value(field.get("value")),
                    "desired": "<removed>",
                }
            )
    for section in ["operation", "load"]:
        actual_by_key = {field["key"]: field.get("value") for field in lmstudio_config_section(actual, section)}
        for desired_field in lmstudio_config_section(desired, section):
            key = desired_field["key"]
            actual_value = actual_by_key.get(key, "<missing>")
            desired_value = desired_field.get("value")
            if actual_value != desired_value:
                mismatches.append(
                    {
                        "section": section,
                        "key": key,
                        "actual": summarize_lmstudio_config_value(actual_value),
                        "desired": summarize_lmstudio_config_value(desired_value),
                    }
                )
    return mismatches


def write_json_with_backup(path: Path, payload: dict[str, Any], *, backup: bool) -> str | None:
    backup_path = None
    if backup and path.exists():
        backup_path = path.with_name(f"{path.name}.bak.{int(time.time())}")
        backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return str(backup_path) if backup_path else None


def command_ov_doctor(args: argparse.Namespace) -> int:
    repo = repo_root_from_args(args)
    payload = ov_status_payload(
        repo,
        online=args.online,
        providers=args.providers,
        provider=getattr(args, "provider", DEFAULT_RUNTIME_PROVIDER),
        base_url=args.base_url,
    )
    payload["doctor"] = {
        "online_checks": args.online,
        "provider_checks": args.providers,
        "repo_scoped_gateway": True,
        "mcp_command": "agent-basics mcp",
    }
    if not args.online:
        payload["recommendation"] = "Run `agent-basics ov doctor --online` before relying on live OpenViking retrieval."
    print_json(payload)
    return 0 if payload["ok"] else 1


def command_ov_install_system(args: argparse.Namespace) -> int:
    home = Path(args.home).expanduser()
    venv = home / "venv"
    ov_bin = venv / "bin" / "ov"
    if ov_bin.exists() and not args.force:
        print_json(
            {
                "ok": True,
                "changed": False,
                "message": "OpenViking is already installed",
                "ov_bin": str(ov_bin),
            }
        )
        return 0

    uv = shutil_which("uv")
    if not uv:
        print_json({"ok": False, "error": "uv is required to install OpenViking systemwide"})
        return 1

    home.mkdir(parents=True, exist_ok=True)
    steps = [
        run_command([uv, "venv", "--python", args.python, str(venv)], timeout=None),
        run_command([uv, "pip", "install", "--python", str(venv / "bin" / "python"), args.package], timeout=None),
    ]
    ok = all(step["ok"] for step in steps)
    print_json({"ok": ok, "changed": ok, "home": str(home), "ov_bin": str(ov_bin), "steps": steps})
    return 0 if ok else 1


def shutil_which(name: str) -> str | None:
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / name
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def command_ov_write_default_config(args: argparse.Namespace) -> int:
    path = Path(args.config).expanduser()
    home = Path(args.home).expanduser()
    cli_config_path = Path(getattr(args, "cli_config", None) or home / "ovcli.conf").expanduser()
    server_url = getattr(args, "server_url", None) or "http://127.0.0.1:1933"
    provider = getattr(args, "provider", DEFAULT_RUNTIME_PROVIDER)
    base_url = (
        getattr(args, "base_url", None)
        or getattr(args, "provider_base", None)
        or getattr(args, "lmstudio_base", None)
        or (DEFAULT_LM_STUDIO_BASE if provider == "lmstudio" else DEFAULT_OLLAMA_BASE)
    ).rstrip("/")
    api_key = getattr(args, "api_key", None) or (DEFAULT_OLLAMA_API_KEY if provider == "ollama" else "lm-studio")
    config_payload = {
        "storage": {"workspace": str(Path(args.home).expanduser() / "workspace")},
        "log": {"level": "INFO", "output": "stdout"},
        "embedding": {
            "dense": {
                "provider": "openai",
                "model": args.embedding_model,
                "api_key": api_key,
                "api_base": f"{base_url}/v1",
                "dimension": args.embedding_dimension,
            },
            "max_concurrent": 1,
            "text_source": "content_only",
            "max_input_tokens": 2048,
        },
        "vlm": {
            "provider": "openai",
            "model": args.chat_model,
            "api_key": api_key,
            "api_base": f"{base_url}/v1",
            "max_concurrent": 1,
            "timeout": args.vlm_timeout,
        },
        "server": {"host": "127.0.0.1", "port": 1933},
    }
    cli_payload = {
        "url": server_url.rstrip("/"),
        "timeout": getattr(args, "cli_timeout", DEFAULT_OV_VLM_TIMEOUT_SECONDS),
    }

    results = []
    ok = True
    for target, payload in [(path, config_payload), (cli_config_path, cli_payload)]:
        exists = target.exists()
        current = load_json_file(target) if exists else None
        changed = bool(args.force or not exists)
        error = None
        if exists and not args.force and isinstance(current, dict) and "_error" in current:
            changed = False
            ok = False
            error = f"{target} is not valid JSON; pass --force to replace it"
        elif changed:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            current = payload
        results.append(
            {
                "path": str(target),
                "exists_before": exists,
                "changed": changed,
                "config": current,
                **({"error": error} if error else {}),
            }
        )

    print_json(
        {
            "ok": ok,
            "changed": any(item["changed"] for item in results),
            "path": str(path),
            "cli_config_path": str(cli_config_path),
            "config": results[0]["config"],
            "cli_config": results[1]["config"],
            "desired_config": config_payload,
            "desired_cli_config": cli_payload,
            "files": results,
        }
    )
    return 0 if ok else 1


def command_payload_from_handler(handler: Any, args: argparse.Namespace) -> dict[str, Any]:
    output = io.StringIO()
    try:
        with redirect_stdout(output):
            returncode = handler(args)
    except Exception as exc:
        text = output.getvalue().strip()
        return {
            "ok": False,
            "returncode": 1,
            "stdout": text,
            "error": str(exc),
            "exception_type": type(exc).__name__,
        }
    text = output.getvalue().strip()
    try:
        payload = json.loads(text) if text else {}
    except json.JSONDecodeError as exc:
        payload = {"ok": returncode == 0, "stdout": text, "json_parse_error": str(exc)}
    payload.setdefault("ok", returncode == 0)
    payload["returncode"] = returncode
    return payload


def ov_bootstrap_lmstudio_args(args: argparse.Namespace, *, dry_run: bool) -> argparse.Namespace:
    lmstudio_mode = getattr(args, "lmstudio", "auto")
    return argparse.Namespace(
        base_url=getattr(args, "lmstudio_base", DEFAULT_LM_STUDIO_BASE),
        lmstudio_home=str(DEFAULT_LMSTUDIO_HOME),
        model=getattr(args, "lmstudio_chat_model", DEFAULT_LMSTUDIO_CHAT_MODEL),
        embedding_model=getattr(args, "lmstudio_embedding_model", DEFAULT_LMSTUDIO_EMBEDDING_MODEL),
        download_model=[],
        min_memory_gb=getattr(args, "lmstudio_min_memory_gb", DEFAULT_LMSTUDIO_MIN_MEMORY_GB),
        allow_non_macos=False,
        force_hardware=lmstudio_mode == "always",
        install="always" if lmstudio_mode == "always" else "auto",
        service="always" if lmstudio_mode == "always" else "auto",
        configure="always" if lmstudio_mode == "always" else "auto",
        download="always" if lmstudio_mode == "always" else "auto",
        cask=getattr(args, "lmstudio_cask", DEFAULT_LMSTUDIO_CASK),
        app_path=getattr(args, "lmstudio_app_path", str(DEFAULT_LMSTUDIO_APP)),
        lms_bin=getattr(args, "lmstudio_lms_bin", None),
        port=DEFAULT_LMSTUDIO_PORT,
        label=DEFAULT_LMSTUDIO_SERVICE_LABEL,
        plist=None,
        timeout=5,
        service_timeout=getattr(args, "service_timeout", DEFAULT_OV_SERVICE_COMMAND_TIMEOUT_SECONDS),
        wait_server_seconds=getattr(args, "lmstudio_wait_server_seconds", 30),
        force_install=False,
        force_service=False,
        no_load=getattr(args, "no_load", False),
        best_effort=getattr(args, "lmstudio_best_effort", False),
        dry_run=dry_run,
    )


def ov_bootstrap_ollama_args(args: argparse.Namespace, *, dry_run: bool) -> argparse.Namespace:
    return argparse.Namespace(
        base_url=getattr(args, "base_url", None) or getattr(args, "provider_base", None) or DEFAULT_OLLAMA_BASE,
        model=getattr(args, "chat_model", DEFAULT_CHAT_MODEL),
        embedding_model=getattr(args, "embedding_model", DEFAULT_EMBEDDING_MODEL),
        pull_model=[],
        install=getattr(args, "ollama_install", "auto"),
        pull=getattr(args, "ollama_pull", "auto"),
        timeout=getattr(args, "ollama_timeout", 5),
        dry_run=dry_run,
    )


def ov_runtime_plan_payload(args: argparse.Namespace, *, dry_run: bool) -> dict[str, Any]:
    runtime = getattr(args, "runtime", "none")
    if getattr(args, "lmstudio", "never") != "never":
        runtime = "lmstudio"
    if runtime == "none":
        return {"ok": True, "changed": False, "skipped": True, "provider": "none"}
    if runtime == "ollama":
        return command_payload_from_handler(command_ollama_bootstrap, ov_bootstrap_ollama_args(args, dry_run=dry_run))
    if runtime == "lmstudio":
        return command_payload_from_handler(command_lmstudio_bootstrap, ov_bootstrap_lmstudio_args(args, dry_run=dry_run))
    return {"ok": False, "changed": False, "error": f"unsupported runtime provider: {runtime}"}


def command_ov_bootstrap_system(args: argparse.Namespace) -> int:
    home = Path(args.home).expanduser()
    config = Path(args.config).expanduser() if args.config else home / "ov.conf"
    cli_config = Path(args.cli_config).expanduser() if args.cli_config else home / "ovcli.conf"
    service_enabled = args.service == "always" or (args.service == "auto" and platform.system() == "Darwin")
    service_skipped_reason = None if service_enabled else (
        "disabled by --service never" if args.service == "never" else "not macOS"
    )

    if args.dry_run:
        runtime_plan = ov_runtime_plan_payload(args, dry_run=True)
        print_json(
            {
                "ok": True,
                "dry_run": True,
                "home": str(home),
                "install": {
                    "needed": args.force_install or not (home / "venv" / "bin" / "ov").exists(),
                    "package": args.package,
                    "python": args.python,
                },
                "config": {
                    "path": str(config),
                    "cli_config": str(cli_config),
                    "needed": args.force_config or not config.exists() or not cli_config.exists(),
                },
                "service": {
                    "enabled": service_enabled,
                    "best_effort": args.service_best_effort,
                    "skipped_reason": service_skipped_reason,
                },
                "runtime": runtime_plan,
                "lmstudio": runtime_plan if getattr(args, "lmstudio", "never") != "never" else {"ok": True, "changed": False, "skipped": True, "mode": "never"},
            }
        )
        return 0

    install_payload = command_payload_from_handler(
        command_ov_install_system,
        argparse.Namespace(
            home=str(home),
            python=args.python,
            package=args.package,
            force=args.force_install,
        ),
    )
    steps: list[dict[str, Any]] = [{"name": "install-system", "payload": install_payload}]
    ok = bool(install_payload.get("ok"))
    if not ok:
        print_json({"ok": False, "home": str(home), "steps": steps})
        return 1

    config_payload = command_payload_from_handler(
        command_ov_write_default_config,
        argparse.Namespace(
            config=str(config),
            cli_config=str(cli_config),
            home=str(home),
            provider=getattr(args, "provider", DEFAULT_RUNTIME_PROVIDER),
            base_url=getattr(args, "base_url", None),
            provider_base=getattr(args, "provider_base", None),
            lmstudio_base=getattr(args, "lmstudio_base", None),
            api_key=getattr(args, "api_key", None),
            chat_model=args.chat_model,
            embedding_model=args.embedding_model,
            embedding_dimension=args.embedding_dimension,
            vlm_timeout=args.vlm_timeout,
            server_url=args.server_url,
            cli_timeout=args.cli_timeout,
            force=args.force_config,
        ),
    )
    steps.append({"name": "write-default-config", "payload": config_payload})
    ok = ok and bool(config_payload.get("ok"))
    if not config_payload.get("ok"):
        print_json({"ok": False, "home": str(home), "steps": steps})
        return 1

    if service_enabled:
        service_payload = command_payload_from_handler(
            command_ov_service,
            argparse.Namespace(
                service_action="install",
                home=str(home),
                server_bin=args.server_bin,
                config=str(config),
                label=args.label,
                plist=args.plist,
                timeout=args.service_timeout,
                dry_run=False,
                force=args.force_service,
                no_load=args.no_load,
            ),
        )
        steps.append({"name": "service install", "payload": service_payload})
        if not service_payload.get("ok"):
            ok = bool(args.service_best_effort)
            steps[-1]["best_effort_ignored_failure"] = bool(args.service_best_effort)
    else:
        steps.append(
            {
                "name": "service install",
                "payload": {
                    "ok": True,
                    "changed": False,
                    "skipped": True,
                    "reason": service_skipped_reason,
                },
            }
        )

    runtime_payload = ov_runtime_plan_payload(args, dry_run=False)
    steps.append({"name": "runtime bootstrap", "payload": runtime_payload})
    if not runtime_payload.get("ok"):
        ok = bool(getattr(args, "runtime_best_effort", False) or getattr(args, "lmstudio_best_effort", False))
        steps[-1]["best_effort_ignored_failure"] = bool(
            getattr(args, "runtime_best_effort", False) or getattr(args, "lmstudio_best_effort", False)
        )

    print_json(
        {
            "ok": ok,
            "changed": any(bool(step["payload"].get("changed")) for step in steps),
            "home": str(home),
            "service_enabled": service_enabled,
            "service_best_effort": args.service_best_effort,
            "steps": steps,
        }
    )
    return 0 if ok else 1


def merge_no_proxy(value: str) -> str:
    required = ["127.0.0.1", "localhost", "::1"]
    existing = [item.strip() for item in value.split(",") if item.strip()]
    lowered = {item.lower() for item in existing}
    for item in required:
        if item.lower() not in lowered:
            existing.append(item)
    return ",".join(existing)


def ov_service_domain() -> str:
    return f"gui/{os.getuid()}"


def ov_service_target(label: str) -> str:
    return f"{ov_service_domain()}/{label}"


def ov_service_plist_path(label: str) -> Path:
    if label == DEFAULT_OV_SERVICE_LABEL:
        return DEFAULT_OV_SERVICE_PLIST
    return Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"


def ov_service_plist_payload(
    *,
    label: str,
    home: Path,
    server_bin: Path,
    config: Path,
    no_proxy: str,
) -> dict[str, Any]:
    logs = home / "logs"
    return {
        "Label": label,
        "ProgramArguments": [str(server_bin), "--config", str(config)],
        "WorkingDirectory": str(home),
        "RunAtLoad": True,
        "KeepAlive": True,
        "ProcessType": "Background",
        "StandardOutPath": str(logs / "openviking-server.out.log"),
        "StandardErrorPath": str(logs / "openviking-server.err.log"),
        "EnvironmentVariables": {
            "NO_PROXY": no_proxy,
            "no_proxy": no_proxy,
        },
    }


def ov_service_plist_text(payload: dict[str, Any]) -> str:
    def value_xml(value: Any, indent: int) -> str:
        pad = "  " * indent
        if isinstance(value, bool):
            return f"{pad}<{'true' if value else 'false'}/>\n"
        if isinstance(value, int):
            return f"{pad}<integer>{value}</integer>\n"
        if isinstance(value, list):
            items = "".join(value_xml(item, indent + 1) for item in value)
            return f"{pad}<array>\n{items}{pad}</array>\n"
        if isinstance(value, dict):
            items = []
            for key in sorted(value):
                items.append(f"{pad}  <key>{html.escape(str(key), quote=False)}</key>\n")
                items.append(value_xml(value[key], indent + 1))
            return f"{pad}<dict>\n{''.join(items)}{pad}</dict>\n"
        return f"{pad}<string>{html.escape(str(value), quote=False)}</string>\n"

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n'
        f"{value_xml(payload, 1)}"
        "</plist>\n"
    )


def ov_service_paths(args: argparse.Namespace) -> dict[str, Any]:
    home = Path(getattr(args, "home", DEFAULT_OV_HOME)).expanduser()
    label = getattr(args, "label", DEFAULT_OV_SERVICE_LABEL) or DEFAULT_OV_SERVICE_LABEL
    server_bin = (
        Path(args.server_bin).expanduser()
        if getattr(args, "server_bin", None)
        else home / "venv" / "bin" / "openviking-server"
    )
    config = Path(args.config).expanduser() if getattr(args, "config", None) else home / "ov.conf"
    plist_path = Path(args.plist).expanduser() if getattr(args, "plist", None) else ov_service_plist_path(label)
    no_proxy = merge_no_proxy(os.environ.get("NO_PROXY") or os.environ.get("no_proxy", ""))
    plist_payload = ov_service_plist_payload(
        label=label,
        home=home,
        server_bin=server_bin,
        config=config,
        no_proxy=no_proxy,
    )
    return {
        "home": home,
        "label": label,
        "server_bin": server_bin,
        "config": config,
        "plist_path": plist_path,
        "plist_payload": plist_payload,
        "plist_text": ov_service_plist_text(plist_payload),
        "domain": ov_service_domain(),
        "target": ov_service_target(label),
    }


def ov_service_changed(plist_path: Path, plist_text: str) -> bool:
    try:
        return plist_path.read_text(encoding="utf-8") != plist_text
    except FileNotFoundError:
        return True


def command_ov_service(args: argparse.Namespace) -> int:
    paths = ov_service_paths(args)
    action = args.service_action
    service_timeout = getattr(args, "timeout", DEFAULT_OV_SERVICE_COMMAND_TIMEOUT_SECONDS)
    plist_path = paths["plist_path"]
    plist_text = paths["plist_text"]
    changed = ov_service_changed(plist_path, plist_text)
    install_commands = [
        ["launchctl", "bootstrap", paths["domain"], str(plist_path)],
        ["launchctl", "enable", paths["target"]],
        ["launchctl", "kickstart", "-k", paths["target"]],
    ]
    payload: dict[str, Any] = {
        "ok": True,
        "action": action,
        "home": str(paths["home"]),
        "label": paths["label"],
        "target": paths["target"],
        "plist": str(plist_path),
        "server_bin": str(paths["server_bin"]),
        "config": str(paths["config"]),
        "plist_payload": paths["plist_payload"],
        "timeout": service_timeout,
        "would_change_plist": changed,
    }

    if action == "status":
        command = ["launchctl", "print", paths["target"]]
        payload["commands"] = [command]
        if args.dry_run:
            payload["dry_run"] = True
            print_json(payload)
            return 0
        result = run_command(command, timeout=service_timeout)
        payload["steps"] = [result]
        payload["ok"] = bool(result["ok"])
        print_json(payload)
        return 0 if payload["ok"] else 1

    if action == "start":
        command = ["launchctl", "kickstart", "-k", paths["target"]]
        payload["commands"] = [command]
        if args.dry_run:
            payload["dry_run"] = True
            print_json(payload)
            return 0
        result = run_command(command, timeout=service_timeout)
        payload["steps"] = [result]
        payload["ok"] = bool(result["ok"])
        print_json(payload)
        return 0 if payload["ok"] else 1

    if action == "stop":
        command = ["launchctl", "bootout", paths["target"]]
        payload["commands"] = [command]
        if args.dry_run:
            payload["dry_run"] = True
            print_json(payload)
            return 0
        result = run_command(command, timeout=service_timeout)
        payload["steps"] = [result]
        payload["ok"] = bool(result["ok"])
        print_json(payload)
        return 0 if payload["ok"] else 1

    if action == "uninstall":
        commands = [["launchctl", "bootout", paths["target"]]]
        payload["commands"] = commands
        if args.dry_run:
            payload["dry_run"] = True
            print_json(payload)
            return 0
        steps = [run_command(commands[0], timeout=service_timeout)]
        removed = False
        if plist_path.exists():
            plist_path.unlink()
            removed = True
        payload["removed_plist"] = removed
        payload["steps"] = steps
        payload["ok"] = True
        print_json(payload)
        return 0

    if action not in {"install", "restart"}:
        print_json({"ok": False, "error": f"unsupported OpenViking service action: {action}"})
        return 2

    commands = []
    if action == "restart":
        commands.append(["launchctl", "bootout", paths["target"]])
        commands.extend(install_commands)
    else:
        commands.append(["launchctl", "print", paths["target"]])
        if changed or getattr(args, "force", False):
            commands.append(["launchctl", "bootout", paths["target"]])
            commands.extend(install_commands)
        else:
            commands.append(["launchctl", "kickstart", "-k", paths["target"]])
    payload["commands"] = commands

    if args.dry_run:
        payload["dry_run"] = True
        print_json(payload)
        return 0

    if platform.system() != "Darwin":
        payload["ok"] = False
        payload["error"] = "OpenViking service management requires macOS launchctl"
        print_json(payload)
        return 1
    if not paths["server_bin"].exists() or not os.access(paths["server_bin"], os.X_OK):
        payload["ok"] = False
        payload["error"] = "OpenViking server is not executable"
        print_json(payload)
        return 1
    if not paths["config"].exists():
        payload["ok"] = False
        payload["error"] = "OpenViking config does not exist"
        print_json(payload)
        return 1

    paths["home"].mkdir(parents=True, exist_ok=True)
    (paths["home"] / "logs").mkdir(parents=True, exist_ok=True)
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if changed:
        if plist_path.exists():
            backup = plist_path.with_name(f"{plist_path.name}.bak.{int(time.time())}")
            backup.write_text(plist_path.read_text(encoding="utf-8"), encoding="utf-8")
        plist_path.write_text(plist_text, encoding="utf-8")

    if getattr(args, "no_load", False):
        payload["changed"] = changed
        payload["backup"] = str(backup) if backup else None
        payload["loaded"] = False
        payload["no_load"] = True
        print_json(payload)
        return 0

    steps: list[dict[str, Any]] = []
    if action == "install":
        status = run_command(["launchctl", "print", paths["target"]], timeout=service_timeout)
        status["optional"] = True
        steps.append(status)
        if status["ok"] and not changed and not getattr(args, "force", False):
            kickstart = run_command(["launchctl", "kickstart", "-k", paths["target"]], timeout=service_timeout)
            steps.append(kickstart)
        else:
            if status["ok"]:
                bootout = run_command(["launchctl", "bootout", paths["target"]], timeout=service_timeout)
                bootout["optional"] = True
                steps.append(bootout)
            steps.extend(run_command(command, timeout=service_timeout) for command in install_commands)
    else:
        bootout = run_command(["launchctl", "bootout", paths["target"]], timeout=service_timeout)
        bootout["optional"] = True
        steps.append(bootout)
        steps.extend(run_command(command, timeout=service_timeout) for command in install_commands)

    required_steps = [step for step in steps if not step.get("optional")]
    payload["changed"] = changed
    payload["backup"] = str(backup) if backup else None
    payload["loaded"] = bool(required_steps and all(step["ok"] for step in required_steps))
    payload["steps"] = steps
    payload["ok"] = all(step["ok"] for step in required_steps)
    print_json(payload)
    return 0 if payload["ok"] else 1


def command_ov_server(args: argparse.Namespace) -> int:
    server_bin = Path(args.server_bin).expanduser() if args.server_bin else find_ov_server()
    if server_bin is None:
        print_json(
            {
                "ok": False,
                "error": "OpenViking server executable not found; run `agent-basics ov install-system` first",
            }
        )
        return 1
    config = Path(args.config).expanduser()
    command = [str(server_bin), "--config", str(config)]
    if args.host:
        command.extend(["--host", args.host])
    if args.port is not None:
        command.extend(["--port", str(args.port)])
    if args.workers is not None:
        command.extend(["--workers", str(args.workers)])
    if args.bot:
        command.append("--bot")
    if args.with_bot:
        command.append("--with-bot")
    payload = {
        "ok": True,
        "command": command,
        "server_bin": str(server_bin),
        "config": str(config),
        "foreground": True,
        "no_proxy": merge_no_proxy(os.environ.get("NO_PROXY") or os.environ.get("no_proxy", "")),
    }
    if args.dry_run:
        payload["dry_run"] = True
        print_json(payload)
        return 0
    if not server_bin.exists() or not os.access(server_bin, os.X_OK):
        print_json({"ok": False, "server_bin": str(server_bin), "error": "OpenViking server is not executable"})
        return 1
    if not config.exists():
        print_json({"ok": False, "config": str(config), "error": "OpenViking config does not exist"})
        return 1
    env = dict(os.environ)
    env["NO_PROXY"] = payload["no_proxy"]
    env["no_proxy"] = payload["no_proxy"]
    os.execve(str(server_bin), command, env)
    return 1


def ov_native_import_files(repo: Path) -> dict[str, list[Path]]:
    memory_root = repo / ".agents" / "memory"

    def markdown_files(root: Path) -> list[Path]:
        if not root.exists():
            return []
        return sorted(path for path in root.rglob("*.md") if path.is_file() and path.name != ".gitkeep")

    resource_files: list[Path] = []
    for name in ["SCHEMA.md", "INDEX.md", "ADAPTATION.md"]:
        path = memory_root / name
        if path.is_file():
            resource_files.append(path)
    resource_files.extend(markdown_files(memory_root / "resources"))

    return {
        "memories": markdown_files(memory_root / "memories"),
        "resources": sorted(dict.fromkeys(resource_files)),
        "skills": markdown_files(memory_root / "skills"),
    }


def ov_import_state_path(repo: Path) -> Path:
    return repo / ".agents" / "openviking" / "import-state.json"


def load_ov_import_state(repo: Path) -> dict[str, Any]:
    path = ov_import_state_path(repo)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"version": 1, "imports": {}}
    except json.JSONDecodeError:
        return {"version": 1, "imports": {}, "previous_state_error": f"{path} is not valid JSON"}


def write_ov_import_state(repo: Path, payload: dict[str, Any]) -> None:
    path = ov_import_state_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated"] = int(time.time())
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ov_memory_content(repo: Path, path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    meta, body = parse_front_matter(text)
    rel = path.relative_to(repo).as_posix()
    return "\n".join(
        [
            f"Project: {repo.name}",
            f"Source path: {rel}",
            f"Record kind: {meta.get('record_kind', 'memory')}",
            f"OpenViking category hint: {meta.get('ov_category', '')}",
            f"Title: {meta.get('title', path.stem)}",
            f"Status: {meta.get('status', '')}",
            f"Summary: {meta.get('summary', '')}",
            f"Tags: {meta.get('tags', '')}",
            "",
            body.strip(),
            "",
        ]
    )


def ov_target_uri(base_uri: str, repo: Path, path: Path, namespace: str) -> str:
    rel = path.relative_to(repo).as_posix()
    return f"{base_uri.rstrip('/')}/{namespace}/{rel}"


def ov_parent_uri(uri: str) -> str:
    return uri.rstrip("/").rsplit("/", 1)[0]


def ov_memory_category(meta: dict[str, str], path: Path) -> str:
    category = meta.get("ov_category", "").strip()
    if category in OV_MEMORY_CATEGORIES:
        return category
    parts = path.parts
    if "memories" in parts:
        index = parts.index("memories")
        if index + 1 < len(parts) and parts[index + 1] in OV_MEMORY_CATEGORIES:
            return parts[index + 1]
    return "entities"


def ov_memory_target_uri(base_uri: str, repo: Path, path: Path, category: str) -> str:
    return f"{base_uri.rstrip('/')}/{category}/projects/{slugify(repo.name)}/{path.name}"


def ov_mkdir_p(ov_bin: Path, uri: str) -> list[dict[str, Any]]:
    if not uri.startswith("viking://"):
        return []
    suffix = uri[len("viking://") :].strip("/")
    if not suffix:
        return []
    pieces = suffix.split("/")
    commands = []
    current = "viking://"
    for piece in pieces:
        current = f"viking://{piece}" if current == "viking://" else f"{current.rstrip('/')}/{piece}"
        result = run_command([str(ov_bin), "mkdir", current, "-o", "json"], timeout=None)
        if not result["ok"] and "already" not in result.get("stderr", "").lower() and "exist" not in result.get("stderr", "").lower():
            commands.append(result)
            break
        commands.append(result)
    return commands


def ov_existing_content_result(ov_bin: Path, target: str, expected: str) -> dict[str, Any] | None:
    read_result = run_command([str(ov_bin), "read", target, "-o", "json"], timeout=None)
    if read_result["ok"] and read_result.get("stdout", "").strip() == expected.strip():
        return {
            "ok": True,
            "command": read_result.get("command"),
            "returncode": read_result.get("returncode"),
            "stdout": "existing target content matches source",
            "stderr": read_result.get("stderr", ""),
            "verified_existing": True,
        }
    return None


def command_ov_import_repo_memory(args: argparse.Namespace) -> int:
    repo = repo_root_from_args(args)
    ov_bin = find_ov_bin()
    if not ov_bin:
        print_json({"ok": False, "error": "OpenViking CLI not found; run `agent-basics ov install-system` first"})
        return 1

    files = ov_native_import_files(repo)
    state = load_ov_import_state(repo)
    imports = state.setdefault("imports", {})
    base_uri = (args.target or f"viking://resources/projects/{slugify(repo.name)}").rstrip("/")
    memory_base_uri = args.memory_target.rstrip("/")
    parent_results = [] if args.dry_run else ov_mkdir_p(ov_bin, base_uri)

    health = run_command([str(ov_bin), "health", "-o", "json"], timeout=10)
    if not health["ok"] and not args.dry_run:
        print_json(
            {
                "ok": False,
                "repo": str(repo),
                "openviking": {"bin": str(ov_bin), "health": health},
                "recommendation": "Start the OpenViking server, then rerun `agent-basics ov import-repo-memory --write`.",
            }
        )
        return 1

    results: list[dict[str, Any]] = []

    def should_skip(path: Path, digest: str, method: str) -> bool:
        if args.force:
            return False
        previous = imports.get(path.relative_to(repo).as_posix())
        return (
            isinstance(previous, dict)
            and previous.get("sha256") == digest
            and previous.get("ok") is True
            and previous.get("method") == method
        )

    def record_result(
        kind: str,
        path: Path,
        digest: str,
        command_result: dict[str, Any] | None,
        *,
        skipped: bool = False,
        method: str,
        target: str | None = None,
    ) -> None:
        rel = path.relative_to(repo).as_posix()
        ok = skipped or bool(command_result and command_result.get("ok"))
        entry = {
            "kind": kind,
            "method": method,
            "path": rel,
            "target": target,
            "sha256": digest,
            "ok": ok,
            "skipped": skipped,
            "imported_at": int(time.time()) if ok and not skipped else imports.get(rel, {}).get("imported_at"),
        }
        if command_result is not None:
            entry["returncode"] = command_result.get("returncode")
            if not ok:
                entry["stdout"] = command_result.get("stdout")
                entry["stderr"] = command_result.get("stderr")
            for key in ["busy_retries", "verified_existing", "already_exists", "previous_error"]:
                if key in command_result:
                    entry[key] = command_result[key]
        imports[rel] = entry
        result_entry = dict(entry)
        if command_result is not None:
            result_entry["command"] = command_result.get("command")
            result_entry["stdout"] = command_result.get("stdout")
            result_entry["stderr"] = command_result.get("stderr")
        results.append(result_entry)

    for path in files["memories"]:
        text = path.read_text(encoding="utf-8")
        meta, _ = parse_front_matter(text)
        digest = sha256_text(text)
        if str(meta.get("requires_human_review", "")).lower() == "true" and not args.include_review:
            record_result("memory", path, digest, None, skipped=True, method="write")
            results[-1]["reason"] = "requires_human_review"
            continue
        category = ov_memory_category(meta, path)
        target = ov_memory_target_uri(memory_base_uri, repo, path, category)
        if should_skip(path, digest, "write"):
            record_result("memory", path, digest, None, skipped=True, method="write", target=target)
            continue
        if not args.dry_run and not args.force:
            existing_result = ov_existing_content_result(ov_bin, target, text)
            if existing_result:
                record_result("memory", path, digest, existing_result, method="write", target=target)
                continue
        if not args.dry_run:
            parent_results.extend(ov_mkdir_p(ov_bin, ov_parent_uri(target)))
        stat_result = {"ok": False} if args.dry_run else run_command([str(ov_bin), "stat", target, "-o", "json"], timeout=None)
        mode = "replace" if stat_result["ok"] else "create"
        command = [str(ov_bin), "write", target, "--from-file", str(path), "--mode", mode, "-o", "json"]
        if args.wait_memory:
            command.extend(["--wait", "--timeout", str(args.timeout)])
        result = (
            {"ok": True, "command": command, "stdout": "dry-run", "stderr": "", "returncode": 0}
            if args.dry_run
            else run_command_retry_busy(command, retries=args.busy_retries, delay=args.busy_delay)
        )
        if not result["ok"] and mode == "create" and "already" in result.get("stderr", "").lower():
            command = [str(ov_bin), "write", target, "--from-file", str(path), "--mode", "replace", "-o", "json"]
            if args.wait_memory:
                command.extend(["--wait", "--timeout", str(args.timeout)])
            result = run_command_retry_busy(command, retries=args.busy_retries, delay=args.busy_delay)
        if not result["ok"] and not args.dry_run:
            existing_result = ov_existing_content_result(ov_bin, target, text)
            if existing_result:
                existing_result["previous_error"] = result.get("stderr") or result.get("error")
                result = existing_result
        record_result("memory", path, digest, result, method="write", target=target)

    for path in files["resources"]:
        digest = sha256_text(path.read_text(encoding="utf-8"))
        target = ov_target_uri(base_uri, repo, path, "resources")
        if should_skip(path, digest, "add-resource"):
            record_result("resource", path, digest, None, skipped=True, method="add-resource", target=target)
            continue
        command = [
            str(ov_bin),
            "add-resource",
            str(path),
            "--to",
            target,
            "--reason",
            "agent-basics repo OpenViking source import",
            "-o",
            "json",
        ]
        if args.wait_resources:
            command.extend(["--wait", "--timeout", str(args.timeout)])
        result = {"ok": True, "command": command, "stdout": "dry-run", "stderr": "", "returncode": 0} if args.dry_run else run_command(command, timeout=None)
        if not result["ok"] and "already" in result.get("stderr", "").lower() and "exist" in result.get("stderr", "").lower():
            stat_result = run_command([str(ov_bin), "stat", target, "-o", "json"], timeout=None)
            if stat_result["ok"]:
                result = {
                    **result,
                    "ok": True,
                    "already_exists": True,
                    "stat": stat_result,
                }
        record_result("resource", path, digest, result, method="add-resource", target=target)

    for path in files["skills"]:
        digest = sha256_text(path.read_text(encoding="utf-8"))
        if should_skip(path, digest, "add-skill"):
            record_result("skill", path, digest, None, skipped=True, method="add-skill")
            continue
        command = [str(ov_bin), "add-skill", str(path), "--wait", "--timeout", str(args.timeout), "-o", "json"]
        result = {"ok": True, "command": command, "stdout": "dry-run", "stderr": "", "returncode": 0} if args.dry_run else run_command(command, timeout=None)
        record_result("skill", path, digest, result, method="add-skill")

    wait_result = None
    if args.wait and not args.dry_run:
        wait_result = run_command([str(ov_bin), "wait"], timeout=None)

    state.update(
        {
            "version": 1,
            "repo": str(repo),
            "target": base_uri,
            "memory_target": memory_base_uri,
            "last_import": int(time.time()),
        }
    )
    if args.write and not args.dry_run:
        write_ov_import_state(repo, state)

    ok = all(item.get("ok") for item in results)
    payload = {
        "ok": ok,
        "repo": str(repo),
        "target": base_uri,
        "memory_target": memory_base_uri,
        "dry_run": args.dry_run,
        "write_state": args.write,
        "counts": {key: len(value) for key, value in files.items()},
        "parents": parent_results,
        "health": health,
        "results": results,
        "wait": wait_result,
        "state_path": str(ov_import_state_path(repo)),
    }
    print_json(payload)
    return 0 if ok else 1


def empty_ov_find_result() -> dict[str, Any]:
    return {"memories": [], "resources": [], "skills": [], "total": 0}


def ov_find_result_ok(payload: dict[str, Any]) -> bool:
    parsed = payload.get("json")
    return bool(payload.get("ok")) and (not isinstance(parsed, dict) or bool(parsed.get("ok", True)))


def ov_result_items(parsed: Any, key: str) -> list[dict[str, Any]]:
    if not isinstance(parsed, dict):
        return []
    result = parsed.get("result")
    if not isinstance(result, dict):
        return []
    items = result.get(key)
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def merge_ov_find_payloads(payloads: list[dict[str, Any]], *, limit: int) -> dict[str, Any]:
    merged = empty_ov_find_result()
    for key in ["memories", "resources", "skills"]:
        by_uri: dict[str, dict[str, Any]] = {}
        for payload in payloads:
            scope = payload.get("scope")
            for item in ov_result_items(payload.get("json"), key):
                uri = str(item.get("uri", ""))
                if not uri:
                    continue
                candidate = dict(item)
                if scope:
                    candidate.setdefault("search_scope", scope)
                previous = by_uri.get(uri)
                if previous is None or float(candidate.get("score") or 0) > float(previous.get("score") or 0):
                    by_uri[uri] = candidate
        merged[key] = sorted(by_uri.values(), key=lambda item: float(item.get("score") or 0), reverse=True)[:limit]
    merged["total"] = sum(len(merged[key]) for key in ["memories", "resources", "skills"])
    return merged


def ov_repo_search_scopes(repo: Path, memory_base_uri: str = DEFAULT_OV_MEMORY_TARGET) -> list[str]:
    repo_slug = ov_repo_slug(repo)
    scopes = [ov_repo_resource_root(repo)]
    scopes.extend(f"{memory_base_uri.rstrip('/')}/{category}/projects/{repo_slug}" for category in OV_MEMORY_CATEGORIES)
    return scopes


def ov_search_payload(
    repo: Path,
    *,
    query: str,
    limit: int = 5,
    include_global: bool = False,
    uri: str | None = None,
    threshold: float | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    ov_bin, error = ov_bin_or_error()
    if error:
        return error
    assert ov_bin is not None
    if not query.strip():
        return {"ok": False, "error": "query must be non-empty"}
    if limit < 1 or limit > 50:
        return {"ok": False, "error": "limit must be between 1 and 50"}
    if uri and not include_global and not ov_uri_is_repo_scoped(uri, repo):
        return {
            "ok": False,
            "repo": str(repo),
            "uri": uri,
            "error": "URI is outside this repo namespace; pass --include-global to search it anyway",
        }

    scopes = [uri] if uri else ([] if include_global else ov_repo_search_scopes(repo))
    if include_global and not uri:
        command = [str(ov_bin), "find", query, "-o", "json", "-n", str(limit)]
        if threshold is not None:
            command.extend(["--threshold", str(threshold)])
        result = ov_command_payload(command, timeout=timeout)
        payload = result.get("json") if isinstance(result.get("json"), dict) else None
        return {
            "ok": ov_find_result_ok(result),
            "repo": str(repo),
            "repo_slug": ov_repo_slug(repo),
            "query": query,
            "include_global": True,
            "scopes": ["global"],
            "result": payload.get("result") if isinstance(payload, dict) else empty_ov_find_result(),
            "commands": [summarize_command_payload(result)],
        }

    command_payloads = []
    for scope in scopes:
        command = [str(ov_bin), "find", query, "--uri", str(scope), "-o", "json", "-n", str(limit)]
        if threshold is not None:
            command.extend(["--threshold", str(threshold)])
        result = ov_command_payload(command, timeout=timeout)
        result["scope"] = scope
        if isinstance(result.get("json"), dict):
            result["json"] = filter_ov_find_result(result["json"], repo, include_global=False)
        command_payloads.append(result)

    ok = all(ov_find_result_ok(item) for item in command_payloads)
    return {
        "ok": ok,
        "repo": str(repo),
        "repo_slug": ov_repo_slug(repo),
        "query": query,
        "include_global": include_global,
        "scopes": scopes,
        "result": merge_ov_find_payloads(command_payloads, limit=limit),
        "commands": [summarize_command_payload(item) for item in command_payloads],
    }


def command_ov_search(args: argparse.Namespace) -> int:
    payload = ov_search_payload(
        repo_root_from_args(args),
        query=args.query,
        limit=args.limit,
        include_global=args.include_global,
        uri=args.uri,
        threshold=args.threshold,
        timeout=None,
    )
    print_json(payload)
    return 0 if payload.get("ok") else 1


def ov_read_payload(repo: Path, *, uri: str, allow_global: bool = False, timeout: float | None = None) -> dict[str, Any]:
    ov_bin, error = ov_bin_or_error()
    if error:
        return error
    assert ov_bin is not None
    if not uri.strip():
        return {"ok": False, "error": "uri must be non-empty"}
    if not allow_global and not ov_uri_is_repo_scoped(uri, repo):
        return {
            "ok": False,
            "repo": str(repo),
            "uri": uri,
            "error": "URI is outside this repo namespace; pass --allow-global to read it anyway",
        }
    read_result = ov_command_payload([str(ov_bin), "read", uri, "-o", "json"], timeout=timeout, parse_json=False)
    stat_result = ov_command_payload([str(ov_bin), "stat", uri, "-o", "json"], timeout=timeout)
    return {
        "ok": bool(read_result.get("ok")),
        "repo": str(repo),
        "repo_slug": ov_repo_slug(repo),
        "uri": uri,
        "content": read_result.get("stdout", ""),
        "read": summarize_command_payload(read_result),
        "stat": summarize_command_payload(stat_result),
        "stat_json": stat_result.get("json"),
    }


def command_ov_read(args: argparse.Namespace) -> int:
    payload = ov_read_payload(repo_root_from_args(args), uri=args.uri, allow_global=args.allow_global, timeout=None)
    print_json(payload)
    return 0 if payload.get("ok") else 1


def normalize_tags(value: Any) -> list[str]:
    if value is None:
        return []
    raw_items: list[Any]
    if isinstance(value, str):
        raw_items = re.split(r"[,;\n]+", value)
    elif isinstance(value, list):
        raw_items = value
    else:
        raw_items = [value]
    result = []
    seen = set()
    for item in raw_items:
        text = str(item).strip()
        if not text:
            continue
        if text not in seen:
            seen.add(text)
            result.append(text)
    return result


def front_matter_value(value: Any) -> str:
    text = str(value).replace("\n", " ").strip()
    return text


def front_matter_tags(tags: list[str]) -> str:
    return "[" + ", ".join(front_matter_value(tag) for tag in tags) + "]"


def ov_memory_markdown(
    *,
    repo: Path,
    category: str,
    title: str,
    content: str,
    summary: str = "",
    tags: list[str] | None = None,
    status: str = "active",
    timestamp: int | None = None,
    source_paths: list[str] | None = None,
) -> str:
    timestamp = timestamp or int(time.time())
    tags = tags or []
    source_paths = source_paths or []
    lines = [
        "---",
        "record_kind: memory",
        f"ov_category: {category}",
        f"title: {front_matter_value(title)}",
        f"status: {front_matter_value(status or 'active')}",
        f"created: {timestamp}",
        f"updated: {timestamp}",
        f"tags: {front_matter_tags(tags)}",
        f"summary: {front_matter_value(summary)}",
        f"source_paths: {front_matter_tags(source_paths)}",
        "requires_human_review: false",
        "---",
        "",
        f"# {title.strip()}",
        "",
        f"Project: {repo.name}",
    ]
    if summary.strip():
        lines.extend(["", "## Summary", "", summary.strip()])
    lines.extend(["", "## Content", "", content.strip(), ""])
    return "\n".join(lines)


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(2, 1000):
        candidate = path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"could not find unique path near {path}")


def ov_record_payload(
    repo: Path,
    *,
    category: str,
    title: str,
    content: str,
    summary: str = "",
    tags: Any = None,
    status: str = "active",
    source_paths: list[str] | None = None,
    wait: bool = True,
    timeout: int = DEFAULT_OV_VLM_TIMEOUT_SECONDS,
    dry_run: bool = False,
) -> dict[str, Any]:
    if category not in OV_MEMORY_CATEGORIES:
        return {"ok": False, "error": f"category must be one of: {', '.join(OV_MEMORY_CATEGORIES)}"}
    if not title.strip():
        return {"ok": False, "error": "title must be non-empty"}
    if not content.strip():
        return {"ok": False, "error": "content must be non-empty"}
    ov_bin, error = ov_bin_or_error()
    if error and not dry_run:
        return error
    timestamp = int(time.time())
    filename = f"{timestamp}-{slugify(title)}.md"
    source_dir = repo / ".agents" / "memory" / "memories" / category
    source_path = unique_path(source_dir / filename)
    filename = source_path.name
    markdown = ov_memory_markdown(
        repo=repo,
        category=category,
        title=title,
        content=content,
        summary=summary,
        tags=normalize_tags(tags),
        status=status,
        timestamp=timestamp,
        source_paths=source_paths or [],
    )
    target = f"{DEFAULT_OV_MEMORY_TARGET}/{category}/projects/{ov_repo_slug(repo)}/{filename}"
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "repo": str(repo),
            "repo_slug": ov_repo_slug(repo),
            "category": category,
            "source_path": str(source_path),
            "target": target,
            "content": markdown,
        }

    source_dir.mkdir(parents=True, exist_ok=True)
    source_path.write_text(markdown, encoding="utf-8")
    assert ov_bin is not None
    parent_results = ov_mkdir_p(ov_bin, ov_parent_uri(target))
    command = [str(ov_bin), "write", target, "--from-file", str(source_path), "--mode", "create", "-o", "json"]
    if wait:
        command.extend(["--wait", "--timeout", str(timeout)])
    result = run_command_retry_busy(command, retries=120, delay=5)
    if not result["ok"] and "already" in result.get("stderr", "").lower():
        replace_command = [str(ov_bin), "write", target, "--from-file", str(source_path), "--mode", "replace", "-o", "json"]
        if wait:
            replace_command.extend(["--wait", "--timeout", str(timeout)])
        result = run_command_retry_busy(replace_command, retries=120, delay=5)
    return {
        "ok": bool(result.get("ok")),
        "repo": str(repo),
        "repo_slug": ov_repo_slug(repo),
        "category": category,
        "source_path": str(source_path),
        "target": target,
        "parents": parent_results,
        "write": result,
    }


def command_ov_record(args: argparse.Namespace) -> int:
    content = args.content or ""
    source_paths: list[str] = []
    if args.from_file:
        path = Path(args.from_file).expanduser()
        if not path.is_absolute():
            path = repo_root_from_args(args) / path
        content = path.read_text(encoding="utf-8")
        source_paths.append(str(path))
    payload = ov_record_payload(
        repo_root_from_args(args),
        category=args.category,
        title=args.title,
        content=content,
        summary=args.summary or "",
        tags=[*(args.tag or []), *(normalize_tags(args.tags))],
        status=args.status,
        source_paths=source_paths,
        wait=not args.no_wait,
        timeout=args.timeout,
        dry_run=args.dry_run,
    )
    print_json(payload)
    return 0 if payload.get("ok") else 1


def is_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def resource_target_for_input(repo: Path, source: str) -> str:
    repo = repo.resolve()
    root = ov_repo_resource_root(repo).rstrip("/")
    if is_url(source):
        parsed = urllib.parse.urlparse(source)
        target_name = slugify(f"{parsed.netloc}-{parsed.path or 'index'}")
        return f"{root}/resources/urls/{target_name}.md"
    path = Path(source).expanduser()
    if not path.is_absolute():
        path = repo / path
    try:
        rel = path.resolve().relative_to(repo)
        rel_text = rel.as_posix()
    except ValueError:
        rel_text = f"external/{slugify(path.name or path.parent.name)}"
    return f"{root}/resources/{rel_text}"


def ov_add_resource_payload(
    repo: Path,
    *,
    source: str,
    target: str | None = None,
    reason: str = "agent-basics repo resource import",
    instruction: str = "",
    wait: bool = True,
    timeout: int = DEFAULT_OV_VLM_TIMEOUT_SECONDS,
    dry_run: bool = False,
) -> dict[str, Any]:
    if not source.strip():
        return {"ok": False, "error": "path_or_url must be non-empty"}
    ov_bin, error = ov_bin_or_error()
    if error and not dry_run:
        return error
    target = target or resource_target_for_input(repo, source)
    if not ov_uri_is_repo_scoped(target, repo):
        return {"ok": False, "repo": str(repo), "target": target, "error": "target must be inside this repo namespace"}
    command_source = source
    if not is_url(source):
        path = Path(source).expanduser()
        if not path.is_absolute():
            path = repo / path
        if not path.exists():
            return {"ok": False, "source": source, "error": "local resource path does not exist"}
        command_source = str(path)
    if dry_run:
        return {"ok": True, "dry_run": True, "repo": str(repo), "source": command_source, "target": target}
    assert ov_bin is not None
    parent_results = ov_mkdir_p(ov_bin, ov_parent_uri(target))
    stat_result = run_command([str(ov_bin), "stat", target, "-o", "json"], timeout=None)
    if stat_result["ok"]:
        return {
            "ok": True,
            "changed": False,
            "already_exists": True,
            "repo": str(repo),
            "source": command_source,
            "target": target,
            "parents": parent_results,
            "stat": stat_result,
        }
    command = [str(ov_bin), "add-resource", command_source, "--to", target, "--reason", reason, "-o", "json"]
    if instruction:
        command.extend(["--instruction", instruction])
    if wait:
        command.extend(["--wait", "--timeout", str(timeout)])
    result = run_command(command, timeout=None)
    return {
        "ok": bool(result.get("ok")),
        "changed": bool(result.get("ok")),
        "repo": str(repo),
        "source": command_source,
        "target": target,
        "parents": parent_results,
        "write": result,
    }


def command_ov_add_resource(args: argparse.Namespace) -> int:
    payload = ov_add_resource_payload(
        repo_root_from_args(args),
        source=args.path_or_url,
        target=args.target,
        reason=args.reason,
        instruction=args.instruction or "",
        wait=not args.no_wait,
        timeout=args.timeout,
        dry_run=args.dry_run,
    )
    print_json(payload)
    return 0 if payload.get("ok") else 1


def ov_add_skill_payload(
    repo: Path,
    *,
    data: str,
    wait: bool = True,
    timeout: int = DEFAULT_OV_VLM_TIMEOUT_SECONDS,
    dry_run: bool = False,
) -> dict[str, Any]:
    if not data.strip():
        return {"ok": False, "error": "path_or_content must be non-empty"}
    ov_bin, error = ov_bin_or_error()
    if error and not dry_run:
        return error
    source = data
    source_path: str | None = None
    candidate = Path(data).expanduser()
    if not candidate.is_absolute():
        candidate = repo / candidate
    if candidate.exists():
        source_path = str(candidate)
        source = source_path
    if dry_run:
        return {"ok": True, "dry_run": True, "repo": str(repo), "source": source, "source_path": source_path}
    assert ov_bin is not None
    command = [str(ov_bin), "add-skill", source, "-o", "json"]
    if wait:
        command.extend(["--wait", "--timeout", str(timeout)])
    result = run_command(command, timeout=None)
    return {
        "ok": bool(result.get("ok")),
        "changed": bool(result.get("ok")),
        "repo": str(repo),
        "source": source,
        "source_path": source_path,
        "note": "OpenViking add-skill does not expose a target URI; repo attribution should be included in skill content.",
        "write": result,
    }


def command_ov_add_skill(args: argparse.Namespace) -> int:
    payload = ov_add_skill_payload(
        repo_root_from_args(args),
        data=args.path_or_content,
        wait=not args.no_wait,
        timeout=args.timeout,
        dry_run=args.dry_run,
    )
    print_json(payload)
    return 0 if payload.get("ok") else 1


def ov_import_staleness(repo: Path) -> dict[str, Any]:
    files = ov_native_import_files(repo)
    state = load_ov_import_state(repo)
    imports = state.get("imports", {}) if isinstance(state, dict) else {}
    stale = []
    for kind, paths in files.items():
        for path in paths:
            rel = path.relative_to(repo).as_posix()
            digest = sha256_text(path.read_text(encoding="utf-8"))
            previous = imports.get(rel)
            if not isinstance(previous, dict) or previous.get("sha256") != digest or previous.get("ok") is not True:
                stale.append({"kind": kind, "path": rel, "state": previous})
    return {
        "counts": {key: len(value) for key, value in files.items()},
        "stale_count": len(stale),
        "stale": stale,
        "state": state,
        "state_path": str(ov_import_state_path(repo)),
    }


def ov_status_payload(
    repo: Path,
    *,
    online: bool = True,
    providers: bool = False,
    provider: str = DEFAULT_RUNTIME_PROVIDER,
    base_url: str = DEFAULT_OLLAMA_BASE,
) -> dict[str, Any]:
    ov_bin = find_ov_bin()
    ov_config = Path(os.environ.get("AGENT_BASICS_OV_CONFIG", str(DEFAULT_OV_CONFIG))).expanduser()
    ov_cli_config = Path(os.environ.get("AGENT_BASICS_OV_CLI_CONFIG", str(DEFAULT_OV_CLI_CONFIG))).expanduser()
    payload: dict[str, Any] = {
        "ok": bool(ov_bin),
        "repo": str(repo),
        "repo_slug": ov_repo_slug(repo),
        "namespaces": {
            "resource_root": ov_repo_resource_root(repo),
            "memory_roots": {
                category: f"{DEFAULT_OV_MEMORY_TARGET}/{category}/projects/{ov_repo_slug(repo)}"
                for category in OV_MEMORY_CATEGORIES
            },
        },
        "source_store": {
            "path": str(repo / ".agents" / "memory"),
            "exists": (repo / ".agents" / "memory").exists(),
            "canonical": ov_import_staleness(repo),
            "legacy_present": {
                name: (repo / ".agents" / "memory" / name).exists()
                for name in ["memory", "documentations", "templates", "rag"]
            },
        },
        "openviking": {
            "home": str(DEFAULT_OV_HOME),
            "bin": str(ov_bin) if ov_bin else None,
            "bin_exists": bool(ov_bin and ov_bin.exists()),
            "config_path": str(ov_config),
            "config_exists": ov_config.exists(),
            "config": load_json_file(ov_config),
            "cli_config_path": str(ov_cli_config),
            "cli_config_exists": ov_cli_config.exists(),
            "cli_config": load_json_file(ov_cli_config),
            "repo_local_install_present": (repo / ".agents" / "openviking" / "venv").exists(),
        },
    }
    if ov_bin:
        payload["openviking"]["version"] = summarize_command_payload(run_command([str(ov_bin), "version"]))
        if online:
            health = ov_command_payload([str(ov_bin), "health", "-o", "json"], timeout=None)
            status = ov_command_payload([str(ov_bin), "status", "-o", "json"], timeout=None)
            payload["openviking"]["health"] = {
                **summarize_command_payload(health),
                "json": health.get("json"),
            }
            payload["openviking"]["status"] = {
                **summarize_command_payload(status),
                "json": status.get("json"),
            }
            payload["ok"] = bool(health.get("ok")) and bool(status.get("ok"))
    if providers:
        if provider == "lmstudio":
            payload["lmstudio"] = lmstudio_status_payload(base_url, timeout=5)
            payload["ok"] = bool(payload["ok"]) and bool(payload["lmstudio"].get("ok"))
        else:
            payload["ollama"] = ollama_status_payload(base_url, timeout=5)
            payload["ok"] = bool(payload["ok"]) and bool(payload["ollama"].get("ok"))
    if not ov_bin:
        payload["recommendation"] = "Run `agent-basics ov install-system` or install OpenViking under ~/.openviking."
    return payload


def command_ov_status(args: argparse.Namespace) -> int:
    payload = ov_status_payload(
        repo_root_from_args(args),
        online=not args.offline,
        providers=args.providers,
        provider=getattr(args, "provider", DEFAULT_RUNTIME_PROVIDER),
        base_url=args.base_url,
    )
    print_json(payload)
    return 0 if payload.get("ok") else 1


def command_ov_ingest_changed(args: argparse.Namespace) -> int:
    payload_args = argparse.Namespace(
        repo=getattr(args, "repo", None),
        target=args.target,
        memory_target=args.memory_target,
        timeout=args.timeout,
        include_review=args.include_review,
        force=False,
        dry_run=args.dry_run,
        wait=True,
        wait_memory=True,
        wait_resources=True,
        busy_retries=args.busy_retries,
        busy_delay=args.busy_delay,
        write=not args.dry_run,
    )
    return command_ov_import_repo_memory(payload_args)


def ov_source_store_path_is_relevant(path: str) -> bool:
    normalized = path.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    prefix = ".agents/memory/"
    if not normalized.startswith(prefix):
        return False
    relative = normalized[len(prefix) :]
    if not relative or relative.endswith("/.gitkeep"):
        return False
    if relative in {"SCHEMA.md", "INDEX.md", "ADAPTATION.md"}:
        return True
    if not relative.endswith(".md"):
        return False
    return relative.startswith("memories/") or relative.startswith("resources/") or relative.startswith("skills/")


def ov_relevant_source_store_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    relevant = []
    for path in paths:
        normalized = path.replace("\\", "/").strip()
        while normalized.startswith("./"):
            normalized = normalized[2:]
        if ov_source_store_path_is_relevant(normalized) and normalized not in seen:
            seen.add(normalized)
            relevant.append(normalized)
    return relevant


def git_hooks_dir(repo: Path) -> Path | None:
    common_dir_result = run_command(["git", "-C", str(repo), "rev-parse", "--git-common-dir"], timeout=10)
    if common_dir_result.get("ok") and str(common_dir_result.get("stdout", "")).strip():
        raw = str(common_dir_result["stdout"]).splitlines()[-1].strip()
        common_dir = Path(raw)
        if not common_dir.is_absolute():
            common_dir = repo / common_dir
        return common_dir / "hooks"

    git_path = repo / ".git"
    if git_path.is_dir():
        return git_path / "hooks"
    if git_path.is_file():
        text = git_path.read_text(encoding="utf-8", errors="replace").strip()
        prefix = "gitdir:"
        if text.lower().startswith(prefix):
            raw = text[len(prefix) :].strip()
            git_dir = Path(raw)
            if not git_dir.is_absolute():
                git_dir = repo / git_dir
            return git_dir / "hooks"
    return None


def shell_single_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def ov_managed_hook_content(event: str, helper_path: Path) -> str:
    quoted_helper = shell_single_quote(str(helper_path))
    return "\n".join(
        [
            "#!/bin/sh",
            f"# {OV_HOOK_MARKER}",
            "set -eu",
            "repo=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0",
            'if [ -x "$repo/agent-basics" ]; then',
            f'  exec "$repo/agent-basics" --repo "$repo" ov hook {event}',
            "fi",
            "if command -v agent-basics >/dev/null 2>&1; then",
            f'  exec agent-basics --repo "$repo" ov hook {event}',
            "fi",
            f"HELPER=${{AGENT_BASICS_OV_HELPER:-{quoted_helper}}}",
            'PYTHON=${AGENT_BASICS_PYTHON:-python3}',
            f'exec "$PYTHON" "$HELPER" --repo "$repo" ov hook {event}',
            "",
        ]
    )


def ov_install_hooks_payload(repo: Path, *, force: bool = False, helper_path: Path | None = None) -> dict[str, Any]:
    hooks_dir = git_hooks_dir(repo)
    if hooks_dir is None:
        return {
            "ok": False,
            "changed": False,
            "repo": str(repo),
            "error": "repository does not have a .git directory or worktree gitdir file",
        }
    helper = (helper_path or Path(__file__)).resolve()
    hooks_dir.mkdir(parents=True, exist_ok=True)
    results = []
    changed = False
    ok = True
    for name, event in [("pre-commit", "pre-commit"), ("post-merge", "post-merge")]:
        path = hooks_dir / name
        desired = ov_managed_hook_content(event, helper)
        existing = path.read_text(encoding="utf-8", errors="replace") if path.exists() else None
        managed = existing is not None and OV_HOOK_MARKER in existing
        legacy_managed = existing is not None and LEGACY_MEMORY_HOOK_MARKER in existing
        if existing is not None and not managed and not legacy_managed and not force:
            ok = False
            results.append(
                {
                    "ok": False,
                    "hook": name,
                    "path": str(path),
                    "changed": False,
                    "error": "existing hook is not managed by agent-basics; rerun with --force to replace it",
                }
            )
            continue
        if existing == desired:
            path.chmod(0o755)
            results.append({"ok": True, "hook": name, "path": str(path), "changed": False, "managed": True})
            continue
        path.write_text(desired, encoding="utf-8")
        path.chmod(0o755)
        changed = True
        results.append(
            {
                "ok": True,
                "hook": name,
                "path": str(path),
                "changed": True,
                "managed": True,
                "event": event,
                "upgraded_from": "legacy-memory" if legacy_managed else None,
            }
        )
    for name in ["post-commit", "post-checkout"]:
        path = hooks_dir / name
        if not path.exists():
            continue
        existing = path.read_text(encoding="utf-8", errors="replace")
        if LEGACY_MEMORY_HOOK_MARKER not in existing:
            continue
        path.unlink()
        changed = True
        results.append(
            {
                "ok": True,
                "hook": name,
                "path": str(path),
                "changed": True,
                "managed": False,
                "removed_obsolete_legacy_hook": True,
            }
        )
    return {
        "ok": ok,
        "changed": changed,
        "repo": str(repo),
        "hooks_dir": str(hooks_dir),
        "helper_path": str(helper),
        "hooks": results,
    }


def command_ov_install_hooks(args: argparse.Namespace) -> int:
    payload = ov_install_hooks_payload(repo_root_from_args(args), force=args.force)
    print_json(payload)
    return 0 if payload.get("ok") else 1


def ov_hook_changed_paths(repo: Path, event: str) -> dict[str, Any]:
    if event == "pre-commit":
        command = [
            "git",
            "-C",
            str(repo),
            "diff",
            "--cached",
            "--name-only",
            "--diff-filter=ACDMRT",
            "--",
            ".agents/memory",
        ]
    elif event == "post-merge":
        command = [
            "git",
            "-C",
            str(repo),
            "diff-tree",
            "-r",
            "--name-only",
            "--no-commit-id",
            "ORIG_HEAD",
            "HEAD",
            "--",
            ".agents/memory",
        ]
    else:
        return {"ok": False, "event": event, "error": "unsupported hook event"}
    result = run_command(command, timeout=30)
    paths = [line.strip() for line in str(result.get("stdout", "")).splitlines() if line.strip()]
    return {
        "ok": bool(result.get("ok")),
        "event": event,
        "command": summarize_command_payload(result),
        "paths": paths,
        "relevant_paths": ov_relevant_source_store_paths(paths),
    }


def ov_hook_locks_dir(repo: Path) -> Path:
    return repo / ".agents" / "openviking" / "locks"


def ov_hook_ingest_lock_path(repo: Path) -> Path:
    return ov_hook_locks_dir(repo) / "ingest.lock"


def ov_acquire_hook_ingest_lock(repo: Path, *, event: str) -> dict[str, Any]:
    locks_dir = ov_hook_locks_dir(repo)
    lock_path = ov_hook_ingest_lock_path(repo)
    locks_dir.mkdir(parents=True, exist_ok=True)
    token = sha256_text(f"{event}:{os.getpid()}:{time.time()}")
    owner = {
        "event": event,
        "pid": os.getpid(),
        "created": int(time.time()),
        "token": token,
    }
    try:
        lock_path.mkdir()
    except FileExistsError:
        existing = load_json_file(lock_path / "owner.json")
        return {
            "ok": False,
            "locked": True,
            "lock_path": str(lock_path),
            "owner": existing,
            "error": "OpenViking ingest lock is already present",
        }
    (lock_path / "owner.json").write_text(json.dumps(owner, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ok": True, "locked": False, "lock_path": str(lock_path), "owner": owner}


def ov_release_hook_ingest_lock(repo: Path, lock: dict[str, Any]) -> dict[str, Any]:
    lock_path = ov_hook_ingest_lock_path(repo)
    owner_path = lock_path / "owner.json"
    expected_token = None
    owner = lock.get("owner")
    if isinstance(owner, dict):
        expected_token = owner.get("token")
    existing = load_json_file(owner_path)
    if isinstance(existing, dict) and expected_token and existing.get("token") != expected_token:
        return {
            "ok": False,
            "lock_path": str(lock_path),
            "error": "lock owner changed before release",
        }
    try:
        owner_path.unlink()
    except FileNotFoundError:
        pass
    try:
        lock_path.rmdir()
    except OSError as exc:
        return {"ok": False, "lock_path": str(lock_path), "error": str(exc)}
    return {"ok": True, "lock_path": str(lock_path)}


def agent_basics_command(repo: Path) -> str:
    explicit = os.environ.get("AGENT_BASICS_BIN")
    if explicit:
        return explicit
    local = repo / "agent-basics"
    if local.exists():
        return str(local)
    return "agent-basics"


def truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def ov_hook_prompt_enabled(event: str) -> bool:
    mode = os.environ.get("AGENT_BASICS_OV_HOOK_MODE", "").strip().lower()
    if mode in {"auto", "run", "yes", "true", "1"}:
        return False
    if mode == "prompt":
        return True
    return event == "pre-commit" and sys.stdin.isatty()


def ov_prompt_for_ingest(event: str, relevant_paths: list[str]) -> bool:
    preview = ", ".join(relevant_paths[:5])
    if len(relevant_paths) > 5:
        preview = f"{preview}, ..."
    print(
        f"OpenViking source-store changes detected for {event}: {preview}",
        file=sys.stderr,
    )
    print("Run `agent-basics ov ingest-changed` now? [Y/n] ", end="", file=sys.stderr, flush=True)
    answer = sys.stdin.readline().strip().lower()
    return answer in {"", "y", "yes"}


def ov_hook_run_payload(
    repo: Path,
    *,
    event: str,
    include_review: bool = False,
    dry_run: bool = False,
    prompt: bool | None = None,
) -> dict[str, Any]:
    if truthy_env("AGENT_BASICS_OV_HOOK_SKIP"):
        return {
            "ok": True,
            "changed": False,
            "repo": str(repo),
            "event": event,
            "action": "skipped",
            "reason": "AGENT_BASICS_OV_HOOK_SKIP is set",
        }
    changes = ov_hook_changed_paths(repo, event)
    payload: dict[str, Any] = {
        "ok": bool(changes.get("ok")),
        "changed": False,
        "repo": str(repo),
        "event": event,
        "source_store": changes,
    }
    if not changes.get("ok"):
        payload["error"] = "failed to inspect git changes for OpenViking source-store paths"
        return payload
    relevant_paths = changes.get("relevant_paths", [])
    if not relevant_paths:
        payload.update({"ok": True, "action": "none", "reason": "no relevant OpenViking source-store changes"})
        return payload
    should_prompt = ov_hook_prompt_enabled(event) if prompt is None else prompt
    if should_prompt and not ov_prompt_for_ingest(event, list(relevant_paths)):
        payload.update(
            {
                "ok": False,
                "action": "declined",
                "error": "OpenViking source-store changes need `agent-basics ov ingest-changed` before commit",
            }
        )
        return payload
    if dry_run:
        payload.update(
            {
                "ok": True,
                "changed": False,
                "dry_run": True,
                "action": "would_ingest",
                "ingest_command": [agent_basics_command(repo), "--repo", str(repo), "ov", "ingest-changed"],
            }
        )
        return payload
    lock = ov_acquire_hook_ingest_lock(repo, event=event)
    payload["lock"] = lock
    if not lock.get("ok"):
        payload.update({"ok": False, "action": "locked", "error": lock.get("error")})
        return payload
    command = [agent_basics_command(repo), "--repo", str(repo), "ov", "ingest-changed"]
    if include_review:
        command.append("--include-review")
    result: dict[str, Any] | None = None
    release: dict[str, Any] | None = None
    try:
        result = run_command(command, timeout=None)
    finally:
        release = ov_release_hook_ingest_lock(repo, lock)
    payload.update(
        {
            "ok": bool(result and result.get("ok")) and bool(release and release.get("ok")),
            "changed": bool(result and result.get("ok")),
            "action": "ingested",
            "ingest_command": command,
            "ingest": result,
            "lock_release": release,
        }
    )
    return payload


def command_ov_hook(args: argparse.Namespace) -> int:
    payload = ov_hook_run_payload(
        repo_root_from_args(args),
        event=args.event,
        include_review=args.include_review,
        dry_run=args.dry_run,
        prompt=False if args.no_prompt else None,
    )
    print_json(payload)
    return 0 if payload.get("ok") else 1


def lmstudio_status_payload(base_url: str, timeout: float | None = 5) -> dict[str, Any]:
    payload: dict[str, Any] = {"base_url": base_url}
    try:
        api_models = http_json(base_url, "/api/v1/models", timeout=timeout)
        openai_models = http_json(base_url, "/v1/models", timeout=timeout)
    except Exception as exc:
        payload.update({"ok": False, "error": str(exc)})
        return payload
    models = api_models.get("models", [])
    loaded = []
    for model in models:
        for instance in model.get("loaded_instances", []) or []:
            loaded.append({"key": model.get("key"), "id": instance.get("id"), "config": instance.get("config", {})})
    payload.update(
        {
            "ok": True,
            "models": models,
            "openai_models": openai_models.get("data", []),
            "loaded": loaded,
            "loaded_gemma_llms": [item for item in loaded if item.get("key") in GEMMA_LLM_KEYS],
        }
    )
    return payload


def ollama_status_payload(
    base_url: str,
    *,
    chat_model: str = DEFAULT_CHAT_MODEL,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    timeout: float | None = 5,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "base_url": base_url,
        "chat_model": chat_model,
        "embedding_model": embedding_model,
    }
    try:
        tags = http_json(base_url, "/api/tags", timeout=timeout)
        openai_models = http_json(base_url, "/v1/models", timeout=timeout)
    except Exception as exc:
        payload.update({"ok": False, "error": str(exc)})
        return payload
    native_models = tags.get("models", [])
    openai_model_items = openai_models.get("data", [])
    model_ids = {
        item.get("name") for item in native_models if isinstance(item, dict) and item.get("name")
    } | {
        item.get("id") for item in openai_model_items if isinstance(item, dict) and item.get("id")
    }
    payload.update(
        {
            "ok": True,
            "models": native_models,
            "openai_models": openai_model_items,
            "model_ids": sorted(model_ids),
            "chat_available": chat_model in model_ids,
            "embedding_available": embedding_model in model_ids,
        }
    )
    return payload


def command_ollama_status(args: argparse.Namespace) -> int:
    payload = ollama_status_payload(
        args.base_url,
        chat_model=args.model,
        embedding_model=args.embedding_model,
        timeout=args.timeout,
    )
    print_json(payload)
    return 0 if payload.get("ok") else 1


def ollama_pull_payload(args: argparse.Namespace, *, status: dict[str, Any] | None = None) -> dict[str, Any]:
    models = [args.model, args.embedding_model, *getattr(args, "pull_model", [])]
    unique_models = list(dict.fromkeys(model for model in models if model))
    payload: dict[str, Any] = {
        "ok": True,
        "changed": False,
        "models": unique_models,
        "dry_run": bool(getattr(args, "dry_run", False)),
    }
    ollama_bin = shutil_which("ollama")
    if not ollama_bin:
        payload.update({"ok": False, "error": "ollama command was not found"})
        return payload
    status = status or ollama_status_payload(
        args.base_url,
        chat_model=args.model,
        embedding_model=args.embedding_model,
        timeout=args.timeout,
    )
    existing = set(status.get("model_ids", []) or [])
    results = []
    for model in unique_models:
        if model in existing:
            results.append({"model": model, "ok": True, "changed": False, "already_present": True})
            continue
        if getattr(args, "dry_run", False):
            results.append({"model": model, "ok": True, "changed": True, "command": [ollama_bin, "pull", model]})
            payload["changed"] = True
            continue
        result = run_command([ollama_bin, "pull", model], timeout=None)
        results.append({"model": model, "ok": result.get("ok"), "changed": result.get("ok"), "result": result})
        payload["changed"] = bool(payload["changed"]) or bool(result.get("ok"))
        payload["ok"] = bool(payload["ok"]) and bool(result.get("ok"))
    payload["results"] = results
    return payload


def command_ollama_pull(args: argparse.Namespace) -> int:
    payload = ollama_pull_payload(args)
    print_json(payload)
    return 0 if payload.get("ok") else 1


def command_ollama_bootstrap(args: argparse.Namespace) -> int:
    ollama_bin = shutil_which("ollama")
    install_mode = getattr(args, "install", "auto")
    steps: list[dict[str, Any]] = []
    ok = True

    if not ollama_bin:
        if install_mode == "never":
            steps.append({"name": "install", "payload": {"ok": False, "changed": False, "error": "ollama command was not found"}})
            ok = False
        elif getattr(args, "dry_run", False):
            steps.append({"name": "install", "payload": {"ok": True, "changed": True, "command": ["brew", "install", "ollama"]}})
        else:
            brew = shutil_which("brew")
            if not brew:
                steps.append({"name": "install", "payload": {"ok": False, "changed": False, "error": "brew is required to install Ollama automatically"}})
                ok = False
            else:
                install_payload = run_command([brew, "install", "ollama"], timeout=None)
                steps.append({"name": "install", "payload": install_payload})
                ok = ok and bool(install_payload.get("ok"))
                ollama_bin = shutil_which("ollama")
    else:
        steps.append({"name": "install", "payload": {"ok": True, "changed": False, "path": ollama_bin}})

    status = ollama_status_payload(
        args.base_url,
        chat_model=args.model,
        embedding_model=args.embedding_model,
        timeout=args.timeout,
    )
    steps.append({"name": "status", "payload": status})
    if not status.get("ok"):
        ok = False
        steps.append(
            {
                "name": "service",
                "payload": {
                    "ok": False,
                    "changed": False,
                    "error": "Ollama server is not reachable; start the Ollama app or run `ollama serve`.",
                },
            }
        )
    elif getattr(args, "pull", "auto") != "never":
        pull_payload = ollama_pull_payload(args, status=status)
        steps.append({"name": "pull models", "payload": pull_payload})
        ok = ok and bool(pull_payload.get("ok"))

    payload = {
        "ok": ok,
        "changed": any(bool(step["payload"].get("changed")) for step in steps),
        "base_url": args.base_url,
        "provider": "ollama",
        "steps": steps,
    }
    print_json(payload)
    return 0 if payload.get("ok") else 1


def command_lmstudio_status(args: argparse.Namespace) -> int:
    print_json(lmstudio_status_payload(args.base_url, timeout=args.timeout))
    return 0


def parse_hardware_profile(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {"raw_available": bool(text.strip())}
    patterns = {
        "model_name": r"Model Name:\s*(.+)",
        "model_identifier": r"Model Identifier:\s*(.+)",
        "chip": r"Chip:\s*(.+)",
        "memory": r"Memory:\s*(.+)",
        "cpu_cores": r"Total Number of Cores:\s*(.+)",
        "gpu_cores": r"Total Number of Cores:\s*(\d+)\n\s*Vendor:",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            result[key] = match.group(1).strip()
    return result


def hardware_payload() -> dict[str, Any]:
    profiler = run_command(["system_profiler", "SPHardwareDataType", "SPDisplaysDataType"], timeout=20)
    parsed = parse_hardware_profile(profiler.get("stdout", "") if profiler["ok"] else "")
    cpu_count = os.cpu_count() or 1
    memory_gb = None
    memory_text = parsed.get("memory", "")
    match = re.search(r"(\d+(?:\.\d+)?)\s*GB", memory_text)
    if match:
        memory_gb = float(match.group(1))
    return {
        "ok": profiler["ok"],
        "system": platform.system(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python_cpu_count": cpu_count,
        "system_profiler": parsed,
        "recommendation": {
            "chat_model": DEFAULT_CHAT_MODEL,
            "context_length": 131072,
            "gpu": {"ratio": "max"},
            "parallel": 1,
            "cpu_threads": min(cpu_count, 8),
            "kv_cache_quantization": "q4_0",
            "flash_attention": True,
            "temperature": 0,
            "notes": [
                "Use Gemma 4 E2B as the default; E4B is not required.",
                "Do not use the `lms` CLI from Codex on this host because it can launch the Electron app and crash.",
                "Use LM Studio REST/OpenAI-compatible HTTP endpoints after the user starts the server.",
            ],
            "memory_gb": memory_gb,
        },
    }


def command_lmstudio_hardware(args: argparse.Namespace) -> int:
    print_json(hardware_payload())
    return 0


def lmstudio_hardware_gate_payload(
    hardware: dict[str, Any],
    *,
    min_memory_gb: float,
    require_macos: bool = True,
) -> dict[str, Any]:
    reasons = []
    memory_gb = hardware.get("recommendation", {}).get("memory_gb")
    system = hardware.get("system") or platform.system()
    machine = hardware.get("machine") or platform.machine()
    if require_macos and system != "Darwin":
        reasons.append(f"requires macOS/Darwin; detected {system or 'unknown'}")
    if machine not in {"arm64", "aarch64"}:
        reasons.append(f"Apple Silicon is recommended; detected {machine or 'unknown'}")
    if memory_gb is None:
        reasons.append("could not determine unified memory")
    elif float(memory_gb) < min_memory_gb:
        reasons.append(f"requires at least {min_memory_gb:g} GB unified memory; detected {memory_gb:g} GB")
    return {
        "ok": not reasons,
        "min_memory_gb": min_memory_gb,
        "memory_gb": memory_gb,
        "system": system,
        "machine": machine,
        "reasons": reasons,
    }


def find_brew() -> str | None:
    discovered = shutil_which("brew")
    if discovered:
        return discovered
    for candidate in [Path("/opt/homebrew/bin/brew"), Path("/usr/local/bin/brew")]:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def find_lms_bin(override: str | None = None) -> Path:
    if override:
        return Path(override).expanduser()
    discovered = shutil_which("lms")
    if discovered:
        return Path(discovered)
    return DEFAULT_LMS_BIN


def lmstudio_install_payload(
    *,
    app_path: Path,
    cask: str,
    dry_run: bool,
    force: bool,
) -> dict[str, Any]:
    installed = app_path.exists()
    needed = force or not installed
    brew = find_brew()
    command = [brew or "brew", "install", "--cask", cask]
    payload: dict[str, Any] = {
        "ok": True,
        "app_path": str(app_path),
        "installed": installed,
        "needed": needed,
        "cask": cask,
        "command": command,
    }
    if not needed:
        payload["changed"] = False
        payload["message"] = "LM Studio app is already installed"
        return payload
    if dry_run:
        payload["changed"] = True
        payload["dry_run"] = True
        return payload
    if platform.system() != "Darwin":
        payload.update({"ok": False, "changed": False, "error": "LM Studio Homebrew cask install requires macOS"})
        return payload
    if not brew:
        payload.update({"ok": False, "changed": False, "error": "brew is required to install LM Studio"})
        return payload
    result = run_command(command, timeout=None)
    payload["result"] = result
    payload["changed"] = bool(result.get("ok"))
    payload["ok"] = bool(result.get("ok"))
    payload["installed_after"] = app_path.exists()
    return payload


def lmstudio_service_plist_path(label: str) -> Path:
    if label == DEFAULT_LMSTUDIO_SERVICE_LABEL:
        return DEFAULT_LMSTUDIO_SERVICE_PLIST
    return Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"


def lmstudio_service_plist_payload(
    *,
    label: str,
    home: Path,
    lms_bin: Path,
    port: int,
    no_proxy: str,
) -> dict[str, Any]:
    logs = home / "logs"
    return {
        "Label": label,
        "ProgramArguments": [str(lms_bin), "server", "start", "--port", str(port)],
        "WorkingDirectory": str(home),
        "RunAtLoad": True,
        "KeepAlive": True,
        "ProcessType": "Background",
        "StandardOutPath": str(logs / "lmstudio-server.out.log"),
        "StandardErrorPath": str(logs / "lmstudio-server.err.log"),
        "EnvironmentVariables": {
            "NO_PROXY": no_proxy,
            "no_proxy": no_proxy,
        },
    }


def lmstudio_service_payload(args: argparse.Namespace) -> dict[str, Any]:
    action = getattr(args, "service_action", "install")
    home = Path(getattr(args, "lmstudio_home", DEFAULT_LMSTUDIO_HOME)).expanduser()
    label = getattr(args, "label", DEFAULT_LMSTUDIO_SERVICE_LABEL) or DEFAULT_LMSTUDIO_SERVICE_LABEL
    lms_bin = find_lms_bin(getattr(args, "lms_bin", None))
    port = int(getattr(args, "port", DEFAULT_LMSTUDIO_PORT))
    plist_path = Path(getattr(args, "plist", None)).expanduser() if getattr(args, "plist", None) else lmstudio_service_plist_path(label)
    no_proxy = merge_no_proxy(os.environ.get("NO_PROXY") or os.environ.get("no_proxy", ""))
    plist_payload = lmstudio_service_plist_payload(
        label=label,
        home=home,
        lms_bin=lms_bin,
        port=port,
        no_proxy=no_proxy,
    )
    plist_text = ov_service_plist_text(plist_payload)
    changed = ov_service_changed(plist_path, plist_text)
    domain = ov_service_domain()
    target = ov_service_target(label)
    timeout = getattr(args, "timeout", DEFAULT_OV_SERVICE_COMMAND_TIMEOUT_SECONDS)
    install_commands = [
        ["launchctl", "bootstrap", domain, str(plist_path)],
        ["launchctl", "enable", target],
        ["launchctl", "kickstart", "-k", target],
    ]
    payload: dict[str, Any] = {
        "ok": True,
        "action": action,
        "lmstudio_home": str(home),
        "label": label,
        "target": target,
        "plist": str(plist_path),
        "lms_bin": str(lms_bin),
        "port": port,
        "plist_payload": plist_payload,
        "would_change_plist": changed,
    }

    if action == "status":
        command = ["launchctl", "print", target]
        payload["commands"] = [command]
        if getattr(args, "dry_run", False):
            payload["dry_run"] = True
            return payload
        result = run_command(command, timeout=timeout)
        payload["steps"] = [result]
        payload["ok"] = bool(result.get("ok"))
        return payload

    if action == "start":
        command = ["launchctl", "kickstart", "-k", target]
        payload["commands"] = [command]
        if getattr(args, "dry_run", False):
            payload["dry_run"] = True
            return payload
        result = run_command(command, timeout=timeout)
        payload["steps"] = [result]
        payload["ok"] = bool(result.get("ok"))
        return payload

    if action == "stop":
        command = ["launchctl", "bootout", target]
        payload["commands"] = [command]
        if getattr(args, "dry_run", False):
            payload["dry_run"] = True
            return payload
        result = run_command(command, timeout=timeout)
        payload["steps"] = [result]
        payload["ok"] = bool(result.get("ok"))
        return payload

    if action == "uninstall":
        payload["commands"] = [["launchctl", "bootout", target]]
        if getattr(args, "dry_run", False):
            payload["dry_run"] = True
            return payload
        steps = [run_command(["launchctl", "bootout", target], timeout=timeout)]
        if plist_path.exists():
            plist_path.unlink()
            payload["removed_plist"] = True
        payload["steps"] = steps
        payload["ok"] = True
        return payload

    if action not in {"install", "restart"}:
        return {"ok": False, "error": f"unsupported LM Studio service action: {action}"}

    payload["commands"] = install_commands if action == "restart" else [["launchctl", "print", target], *install_commands]
    if getattr(args, "dry_run", False):
        payload["dry_run"] = True
        return payload
    if platform.system() != "Darwin":
        payload.update({"ok": False, "error": "LM Studio service management requires macOS launchctl"})
        return payload
    if not lms_bin.exists() or not os.access(lms_bin, os.X_OK):
        payload.update({"ok": False, "error": "LM Studio lms CLI is not executable"})
        return payload

    backup = None
    try:
        home.mkdir(parents=True, exist_ok=True)
        (home / "logs").mkdir(parents=True, exist_ok=True)
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        if changed:
            if plist_path.exists():
                backup = plist_path.with_name(f"{plist_path.name}.bak.{int(time.time())}")
                backup.write_text(plist_path.read_text(encoding="utf-8"), encoding="utf-8")
            plist_path.write_text(plist_text, encoding="utf-8")
    except OSError as exc:
        payload.update(
            {
                "ok": False,
                "changed": False,
                "error": f"failed to write LM Studio service files: {exc}",
                "exception_type": type(exc).__name__,
            }
        )
        return payload

    if getattr(args, "no_load", False):
        payload.update({"changed": changed, "backup": str(backup) if backup else None, "loaded": False, "no_load": True})
        return payload

    steps = []
    if action == "restart":
        bootout = run_command(["launchctl", "bootout", target], timeout=timeout)
        bootout["optional"] = True
        steps.append(bootout)
        steps.extend(run_command(command, timeout=timeout) for command in install_commands)
    else:
        status = run_command(["launchctl", "print", target], timeout=timeout)
        status["optional"] = True
        steps.append(status)
        if status["ok"] and not changed and not getattr(args, "force", False):
            steps.append(run_command(["launchctl", "kickstart", "-k", target], timeout=timeout))
        else:
            if status["ok"]:
                bootout = run_command(["launchctl", "bootout", target], timeout=timeout)
                bootout["optional"] = True
                steps.append(bootout)
            steps.extend(run_command(command, timeout=timeout) for command in install_commands)

    required_steps = [step for step in steps if not step.get("optional")]
    payload.update(
        {
            "changed": changed,
            "backup": str(backup) if backup else None,
            "loaded": bool(required_steps and all(step["ok"] for step in required_steps)),
            "steps": steps,
            "ok": all(step["ok"] for step in required_steps),
        }
    )
    return payload


def command_lmstudio_service(args: argparse.Namespace) -> int:
    payload = lmstudio_service_payload(args)
    print_json(payload)
    return 0 if payload.get("ok") else 1


def lmstudio_download_models_from_args(args: argparse.Namespace) -> list[str]:
    values = list(getattr(args, "download_model", None) or [])
    if values:
        return values
    return [getattr(args, "model", DEFAULT_CHAT_MODEL), getattr(args, "embedding_model", DEFAULT_EMBEDDING_MODEL)]


def lmstudio_openai_model_ids(status: dict[str, Any]) -> set[str]:
    ids = set()
    for item in status.get("openai_models", []) or []:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            ids.add(item["id"])
    return ids


def lmstudio_wait_server_payload(base_url: str, *, timeout: float, wait_seconds: float) -> dict[str, Any]:
    deadline = time.time() + max(wait_seconds, 0)
    attempts = []
    while True:
        status = lmstudio_status_payload(base_url, timeout=timeout)
        attempts.append({"ok": status.get("ok"), **({"error": status.get("error")} if status.get("error") else {})})
        if status.get("ok") or time.time() >= deadline:
            return {"ok": bool(status.get("ok")), "attempts": attempts, "status": status, "wait_seconds": wait_seconds}
        time.sleep(min(1.0, max(0.1, deadline - time.time())))


def lmstudio_download_models_payload(args: argparse.Namespace, *, status: dict[str, Any] | None = None) -> dict[str, Any]:
    models = lmstudio_download_models_from_args(args)
    dry_run = bool(getattr(args, "dry_run", False))
    base_url = getattr(args, "base_url", DEFAULT_LM_STUDIO_BASE)
    timeout = getattr(args, "timeout", 5)
    if status is None and not dry_run:
        status = lmstudio_status_payload(base_url, timeout=timeout)
    downloaded = lmstudio_openai_model_ids(status or {})
    results = []
    ok = True
    for model in models:
        if model in downloaded:
            results.append({"model": model, "ok": True, "changed": False, "message": "model is already available"})
            continue
        request = {"model": model}
        if dry_run:
            results.append(
                {
                    "model": model,
                    "ok": True,
                    "changed": True,
                    "dry_run": True,
                    "endpoint": "/api/v1/models/download",
                    "request": request,
                }
            )
            continue
        if not status or not status.get("ok"):
            results.append({"model": model, "ok": False, "changed": False, "error": "LM Studio server is not reachable"})
            ok = False
            continue
        try:
            result = http_json(base_url, "/api/v1/models/download", request, timeout=None)
        except Exception as exc:
            results.append({"model": model, "ok": False, "changed": False, "error": str(exc), "request": request})
            ok = False
        else:
            results.append({"model": model, "ok": True, "changed": True, "request": request, "result": result})
    return {
        "ok": ok,
        "changed": any(bool(item.get("changed")) for item in results),
        "base_url": base_url,
        "models": models,
        "results": results,
    }


def lmstudio_jit_payload(args: argparse.Namespace, *, status: dict[str, Any] | None = None) -> dict[str, Any]:
    models = lmstudio_download_models_from_args(args)
    if status is None:
        status = lmstudio_status_payload(getattr(args, "base_url", DEFAULT_LM_STUDIO_BASE), timeout=getattr(args, "timeout", 5))
    downloaded = lmstudio_openai_model_ids(status)
    missing = [model for model in models if model not in downloaded]
    return {
        "ok": bool(status.get("ok")) and not missing,
        "base_url": getattr(args, "base_url", DEFAULT_LM_STUDIO_BASE),
        "jit_loading": True,
        "definition": "downloaded models are exposed through /v1/models and are loaded on first inference request",
        "models": models,
        "available_models": sorted(downloaded),
        "missing_models": missing,
        "loaded_instances": status.get("loaded", []) if status.get("ok") else [],
        "server_reachable": bool(status.get("ok")),
    }


def mode_is_enabled(mode: str, *, needed: bool = True) -> bool:
    return mode == "always" or (mode == "auto" and needed)


def command_lmstudio_bootstrap(args: argparse.Namespace) -> int:
    hardware = hardware_payload()
    gate = lmstudio_hardware_gate_payload(
        hardware,
        min_memory_gb=float(getattr(args, "min_memory_gb", DEFAULT_LMSTUDIO_MIN_MEMORY_GB)),
        require_macos=not getattr(args, "allow_non_macos", False),
    )
    force_hardware = bool(getattr(args, "force_hardware", False))
    dry_run = bool(getattr(args, "dry_run", False))
    best_effort = bool(getattr(args, "best_effort", False))
    if not gate["ok"] and not force_hardware:
        print_json(
            {
                "ok": True,
                "changed": False,
                "skipped": True,
                "reason": "host hardware is below the LM Studio local-runtime threshold",
                "hardware_gate": gate,
                "hardware": hardware,
            }
        )
        return 0

    app_path = Path(getattr(args, "app_path", DEFAULT_LMSTUDIO_APP)).expanduser()
    install_mode = getattr(args, "install", "auto")
    service_mode = getattr(args, "service", "auto")
    configure_mode = getattr(args, "configure", "auto")
    download_mode = getattr(args, "download", "auto")
    install_needed = bool(getattr(args, "force_install", False) or not app_path.exists())
    steps: list[dict[str, Any]] = []
    ok = True

    def add_step(name: str, payload: dict[str, Any]) -> None:
        nonlocal ok
        item = {"name": name, "payload": payload}
        if not payload.get("ok"):
            item["best_effort_ignored_failure"] = best_effort
            ok = ok and best_effort
        else:
            ok = ok and True
        steps.append(item)

    if mode_is_enabled(install_mode, needed=install_needed):
        add_step(
            "install",
            lmstudio_install_payload(
                app_path=app_path,
                cask=getattr(args, "cask", DEFAULT_LMSTUDIO_CASK),
                dry_run=dry_run,
                force=bool(getattr(args, "force_install", False)),
            ),
        )
    else:
        steps.append({"name": "install", "payload": {"ok": True, "changed": False, "skipped": True, "mode": install_mode}})

    if mode_is_enabled(service_mode, needed=True):
        add_step(
            "service install",
            lmstudio_service_payload(
                argparse.Namespace(
                    service_action="install",
                    lmstudio_home=getattr(args, "lmstudio_home", str(DEFAULT_LMSTUDIO_HOME)),
                    lms_bin=getattr(args, "lms_bin", None),
                    port=getattr(args, "port", DEFAULT_LMSTUDIO_PORT),
                    label=getattr(args, "label", DEFAULT_LMSTUDIO_SERVICE_LABEL),
                    plist=getattr(args, "plist", None),
                    timeout=getattr(args, "service_timeout", DEFAULT_OV_SERVICE_COMMAND_TIMEOUT_SECONDS),
                    dry_run=dry_run,
                    force=getattr(args, "force_service", False),
                    no_load=getattr(args, "no_load", False),
                )
            ),
        )
    else:
        steps.append({"name": "service install", "payload": {"ok": True, "changed": False, "skipped": True, "mode": service_mode}})

    if mode_is_enabled(configure_mode, needed=True):
        add_step(
            "configure models",
            command_payload_from_handler(
                command_lmstudio_configure,
                argparse.Namespace(
                    base_url=getattr(args, "base_url", DEFAULT_LM_STUDIO_BASE),
                    lmstudio_home=getattr(args, "lmstudio_home", str(DEFAULT_LMSTUDIO_HOME)),
                    model=getattr(args, "model", DEFAULT_CHAT_MODEL),
                    embedding_model=getattr(args, "embedding_model", DEFAULT_EMBEDDING_MODEL),
                    cpu_threads=0,
                    parallel=1,
                    context_length=0,
                    embedding_context_length=2048,
                    kv_cache_quantization="q4_0",
                    gpu_offload_ratio=1.0,
                    temperature=0,
                    timeout=getattr(args, "timeout", 5),
                    write=not dry_run,
                    backup=True,
                    include_embedding=True,
                    include_routing_defaults=False,
                    verbose_config=False,
                ),
            ),
        )
    else:
        steps.append({"name": "configure models", "payload": {"ok": True, "changed": False, "skipped": True, "mode": configure_mode}})

    if mode_is_enabled(download_mode, needed=True):
        wait_payload = {"ok": True, "skipped": True, "dry_run": True} if dry_run else lmstudio_wait_server_payload(
            getattr(args, "base_url", DEFAULT_LM_STUDIO_BASE),
            timeout=getattr(args, "timeout", 5),
            wait_seconds=getattr(args, "wait_server_seconds", 30),
        )
        add_step("wait server", wait_payload)
        download_status = wait_payload.get("status") if wait_payload.get("ok") else None
        add_step("download models", lmstudio_download_models_payload(args, status=download_status))
        if dry_run:
            jit_payload = {
                "ok": True,
                "dry_run": True,
                "jit_loading": True,
                "models": lmstudio_download_models_from_args(args),
            }
        else:
            jit_status = lmstudio_status_payload(
                getattr(args, "base_url", DEFAULT_LM_STUDIO_BASE),
                timeout=getattr(args, "timeout", 5),
            )
            jit_payload = lmstudio_jit_payload(args, status=jit_status)
        add_step("ensure jit loading", jit_payload)
    else:
        steps.append({"name": "download models", "payload": {"ok": True, "changed": False, "skipped": True, "mode": download_mode}})

    print_json(
        {
            "ok": ok,
            "changed": any(bool(step["payload"].get("changed")) for step in steps),
            "dry_run": dry_run,
            "best_effort": best_effort,
            "hardware_gate": gate,
            "hardware": hardware,
            "steps": steps,
        }
    )
    return 0 if ok else 1


def find_model(api_models: dict[str, Any], model_key: str) -> dict[str, Any] | None:
    for model in api_models.get("models", []):
        if model.get("key") == model_key:
            return model
    return None


def lmstudio_plan_payload(args: argparse.Namespace) -> dict[str, Any]:
    status = lmstudio_status_payload(args.base_url, timeout=args.timeout)
    hardware = hardware_payload()
    model_info = None
    max_context = 131072
    if status.get("ok"):
        model_info = find_model({"models": status.get("models", [])}, args.model)
        if model_info:
            max_context = int(model_info.get("max_context_length") or max_context)
    return {
        "ok": bool(status.get("ok")) and model_info is not None,
        "server": {"base_url": args.base_url, "reachable": bool(status.get("ok"))},
        "model": args.model,
        "model_present": model_info is not None,
        "embedding_model": args.embedding_model,
        "load_request": {
            "model": args.model,
            "context_length": max_context,
            "eval_batch_size": 512,
            "offload_kv_cache_to_gpu": True,
            "flash_attention": True,
            "echo_load_config": True,
        },
        "unsupported_load_recommendations": {
            "gpu": {"ratio": "max"},
            "parallel": 1,
            "cpu_threads": hardware["recommendation"]["cpu_threads"],
            "kv_cache_quantization": "q4_0",
            "note": "LM Studio 0.4 v1 REST load accepts flattened model/context/eval_batch_size/flash_attention/offload_kv_cache_to_gpu fields; these recommendations are not exposed by the current REST load endpoint.",
        },
        "prediction_config": {
            "temperature": 0,
            "max_tokens": args.max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "openviking_memory_routing",
                    "strict": True,
                    "schema": ROUTER_OUTPUT_SCHEMA,
                },
            },
        },
        "hardware": hardware,
        "status": status,
        "persistent_default_config": lmstudio_configure_payload(
            argparse.Namespace(
                lmstudio_home=str(DEFAULT_LMSTUDIO_HOME),
                model=args.model,
                embedding_model=args.embedding_model,
                cpu_threads=hardware["recommendation"]["cpu_threads"],
                parallel=1,
                context_length=max_context,
                embedding_context_length=2048,
                kv_cache_quantization="q4_0",
                gpu_offload_ratio=1.0,
                temperature=0,
                include_routing_defaults=False,
                write=False,
                backup=True,
                include_embedding=True,
                timeout=args.timeout,
                base_url=args.base_url,
            ),
            status=status,
            hardware=hardware,
            emit_full_configs=False,
        ),
    }


def command_lmstudio_plan(args: argparse.Namespace) -> int:
    print_json(lmstudio_plan_payload(args))
    return 0


def lmstudio_configure_target_payload(
    *,
    path: Path,
    desired: dict[str, Any],
    write: bool,
    backup: bool,
    emit_full_config: bool,
    remove_operation_keys: set[str] | None = None,
) -> dict[str, Any]:
    existing = load_json_file(path)
    merged = merge_lmstudio_config(existing, desired, remove_operation_keys=remove_operation_keys)
    mismatches = lmstudio_config_mismatches_by_key(existing, desired, remove_operation_keys=remove_operation_keys)
    changed = existing != merged
    payload: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "changed": changed,
        "mismatches": mismatches,
    }
    if emit_full_config:
        payload["desired"] = desired
        payload["merged"] = merged
    if write and changed:
        payload["backup_path"] = write_json_with_backup(path, merged, backup=backup)
        payload["written"] = True
    elif write:
        payload["written"] = False
    return payload


def lmstudio_configure_payload(
    args: argparse.Namespace,
    *,
    status: dict[str, Any] | None = None,
    hardware: dict[str, Any] | None = None,
    emit_full_configs: bool = True,
) -> dict[str, Any]:
    home = Path(args.lmstudio_home).expanduser()
    hardware = hardware or hardware_payload()
    status = status or lmstudio_status_payload(args.base_url, timeout=args.timeout)
    cpu_threads = args.cpu_threads or hardware["recommendation"]["cpu_threads"]
    context_length = args.context_length
    if context_length <= 0 and status.get("ok"):
        model_info = find_model({"models": status.get("models", [])}, args.model)
        context_length = int(model_info.get("max_context_length") or 131072) if model_info else 131072
    if context_length <= 0:
        context_length = 131072

    chat_desired = lmstudio_desired_chat_config(
        cpu_threads=cpu_threads,
        parallel=args.parallel,
        context_length=context_length,
        kv_cache_quantization=args.kv_cache_quantization,
        gpu_offload_ratio=args.gpu_offload_ratio,
        temperature=args.temperature,
        include_routing_defaults=args.include_routing_defaults,
    )
    remove_operation_keys = set() if args.include_routing_defaults else LMSTUDIO_ROUTING_DEFAULT_KEYS
    targets = [
        lmstudio_configure_target_payload(
            path=path,
            desired=chat_desired,
            write=args.write,
            backup=args.backup,
            emit_full_config=emit_full_configs,
            remove_operation_keys=remove_operation_keys,
        )
        for path in lmstudio_default_config_paths(home, args.model)
    ]

    embedding_targets = []
    if args.include_embedding:
        embedding_desired = lmstudio_desired_embedding_config(
            parallel=1,
            context_length=args.embedding_context_length,
        )
        embedding_targets = [
            lmstudio_configure_target_payload(
                path=path,
                desired=embedding_desired,
                write=args.write,
                backup=args.backup,
                emit_full_config=emit_full_configs,
            )
            for path in lmstudio_default_config_paths(home, args.embedding_model)
        ]

    loaded_gemma = status.get("loaded_gemma_llms", []) if status.get("ok") else []
    conflicting_loaded = [item for item in loaded_gemma if item.get("key") != args.model]
    return {
        "ok": not conflicting_loaded,
        "changed": any(bool(item.get("changed")) for item in [*targets, *embedding_targets]),
        "write": args.write,
        "lmstudio_home": str(home),
        "model": args.model,
        "embedding_model": args.embedding_model if args.include_embedding else None,
        "settings": {
            "cpu_threads": cpu_threads,
            "parallel": args.parallel,
            "context_length": context_length,
            "embedding_context_length": args.embedding_context_length if args.include_embedding else None,
            "kv_cache_quantization": args.kv_cache_quantization,
            "gpu_offload_ratio": args.gpu_offload_ratio,
            "temperature": args.temperature,
            "routing_defaults": "persisted" if args.include_routing_defaults else "request_time_only",
            "cleared_persistent_fields": sorted(remove_operation_keys),
        },
        "targets": targets,
        "embedding_targets": embedding_targets,
        "status": {
            "server_reachable": bool(status.get("ok")),
            "loaded_gemma_llms": loaded_gemma,
            "conflicting_loaded": conflicting_loaded,
        },
        "notes": [
            "This writes LM Studio persisted model defaults observed under ~/.lmstudio/.internal/user-concrete-model-default-config.",
            "LM Studio REST model loading still receives per-load context/eval/flash/offload flags from agent-basics.",
            "OpenAI-compatible chat requests include the system prompt and json_schema response_format explicitly for deterministic routing.",
            "Persistent structured-output and system-prompt defaults are cleared by default because they can conflict with OpenViking's own request-time grammar.",
            "If the model is already loaded, unload and load it again before expecting persisted load defaults to apply.",
        ],
    }


def command_lmstudio_configure(args: argparse.Namespace) -> int:
    payload = lmstudio_configure_payload(args, emit_full_configs=args.verbose_config)
    print_json(payload)
    return 0 if payload["ok"] else 1


def lmstudio_config_mismatches(actual: dict[str, Any], desired: dict[str, Any]) -> list[dict[str, Any]]:
    mismatches = []
    for key in LMSTUDIO_REPORTED_LOAD_KEYS:
        if key not in desired:
            continue
        actual_value = actual.get(key)
        desired_value = desired[key]
        if actual_value != desired_value:
            mismatches.append({"key": key, "actual": actual_value, "desired": desired_value})
    return mismatches


def command_lmstudio_load(args: argparse.Namespace) -> int:
    plan = lmstudio_plan_payload(args)
    if not plan.get("ok"):
        print_json(plan)
        return 1
    loaded_gemma = plan["status"].get("loaded_gemma_llms", [])
    conflicts = [item for item in loaded_gemma if item.get("key") != args.model]
    same_model = [item for item in loaded_gemma if item.get("key") == args.model]
    desired_config = plan["load_request"]
    mismatched = [
        {"target": item, "mismatches": lmstudio_config_mismatches(item.get("config", {}), desired_config)}
        for item in same_model
    ]
    mismatched = [item for item in mismatched if item["mismatches"]]
    if conflicts and not args.unload_conflicts:
        print_json(
            {
                "ok": False,
                "error": "another Gemma LLM is already loaded",
                "conflicts": conflicts,
                "recommendation": "rerun with --unload-conflicts or unload it manually",
            }
        )
        return 1
    if mismatched and not args.reload_mismatched:
        print_json(
            {
                "ok": False,
                "error": "target Gemma LLM is already loaded with different reported settings",
                "mismatched": mismatched,
                "recommendation": "rerun with --reload-mismatched to unload and reload the target model",
            }
        )
        return 1

    unload_targets = [*conflicts, *[item["target"] for item in mismatched]]
    if args.dry_run:
        print_json({"ok": True, "dry_run": True, "request": plan["load_request"], "would_unload": unload_targets})
        return 0
    unload_results = []
    for item in unload_targets:
        unload_results.append(
            {
                "target": item,
                "result": http_json(args.base_url, "/api/v1/models/unload", {"instance_id": item["id"]}, timeout=args.timeout),
            }
        )
    if same_model and not mismatched:
        print_json(
            {
                "ok": True,
                "changed": bool(unload_results),
                "message": "target model is already loaded with requested reported settings",
                "request": plan["load_request"],
                "loaded": same_model,
                "unloaded": unload_results,
            }
        )
        return 0
    try:
        result = http_json(args.base_url, "/api/v1/models/load", plan["load_request"], timeout=None)
    except Exception as exc:
        print_json({"ok": False, "error": str(exc), "request": plan["load_request"]})
        return 1
    print_json({"ok": True, "request": plan["load_request"], "unloaded": unload_results, "result": result})
    return 0


def command_lmstudio_unload(args: argparse.Namespace) -> int:
    status = lmstudio_status_payload(args.base_url, timeout=args.timeout)
    if not status.get("ok"):
        print_json(status)
        return 1
    targets = []
    for item in status.get("loaded", []):
        if args.all or item.get("id") == args.identifier or item.get("key") == args.identifier:
            targets.append(item)
    if not targets:
        print_json({"ok": True, "changed": False, "message": "no matching loaded model", "status": status})
        return 0
    results = []
    for item in targets:
        results.append(
            {
                "target": item,
                "result": http_json(args.base_url, "/api/v1/models/unload", {"instance_id": item["id"]}, timeout=args.timeout),
            }
        )
    print_json({"ok": True, "changed": True, "results": results})
    return 0


def redact(text: str) -> str:
    text = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}\b", "<REDACTED_SECRET>", text)
    text = re.sub(
        r"\b([A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*)=([^\s,;]+)",
        r"\1=<REDACTED_SECRET>",
        text,
        flags=re.IGNORECASE,
    )
    return text


def preingest_candidates(case_name: str, text: str) -> list[dict[str, str]]:
    redacted = redact(text).strip()
    fragments = [redacted]
    if "Workaround:" in redacted:
        fragments = [redacted]
    elif "\n" in redacted:
        fragments = [item.strip() for item in redacted.splitlines() if item.strip()]
    elif len(redacted) > 120:
        fragments = [
            item.strip()
            for item in re.split(r"(?<=[.!?])\s+(?=(?:The user|agent-basics|OpenViking|Decision|LM Studio|Workaround|Source URL|Durable rule|Temporary key)\b)", redacted)
            if item.strip()
        ]
    return [
        {
            "input_id": f"{case_name}.{index + 1}",
            "text": fragment,
            **preingest_hint(fragment),
        }
        for index, fragment in enumerate(fragments)
    ]


def preingest_hint(text: str) -> dict[str, str]:
    lower = text.lower()
    if re.fullmatch(r"(source url:\s*)?https?://\S+", text.strip(), flags=re.IGNORECASE):
        return {
            "suggested_action": "create",
            "suggested_record_kind": "resource",
            "suggested_ov_category": "none",
            "hint_reason": "URL-only source record",
        }
    if "user wants" in lower or "user prefers" in lower or "user dislikes" in lower:
        return {
            "suggested_action": "create",
            "suggested_record_kind": "memory",
            "suggested_ov_category": "preferences",
            "hint_reason": "explicit user preference wording",
        }
    if "crashed" in lower and "workaround:" in lower:
        return {
            "suggested_action": "create",
            "suggested_record_kind": "memory",
            "suggested_ov_category": "cases",
            "hint_reason": "problem and workaround in one candidate",
        }
    if lower.startswith("decision") or "unix time" in lower:
        return {
            "suggested_action": "create",
            "suggested_record_kind": "memory",
            "suggested_ov_category": "events",
            "hint_reason": "decision or timestamped event",
        }
    if " owns " in lower and ("agent-basics" in lower or "openviking" in lower):
        return {
            "suggested_action": "create",
            "suggested_record_kind": "memory",
            "suggested_ov_category": "entities",
            "hint_reason": "system ownership/responsibility statement",
        }
    if any(token in lower for token in ["must never", "never store", "must not be preserved", "do not store"]):
        return {
            "suggested_action": "create",
            "suggested_record_kind": "memory",
            "suggested_ov_category": "patterns",
            "hint_reason": "durable operating/security rule",
        }
    return {
        "suggested_action": "needs_review",
        "suggested_record_kind": "memory",
        "suggested_ov_category": "entities",
        "hint_reason": "fallback review hint",
    }


def routing_cases() -> list[dict[str, Any]]:
    return [
        {
            "name": "harness_direction",
            "text": "The user wants agent-basics to be a thin harness layer over OpenViking. agent-basics owns setup, config, MCP, hooks, migration UX, and instructions. OpenViking owns durable context storage, resources, summaries, vector indexes, and retrieval.",
            "expect": [
                {"record_kind": "memory", "ov_category": "preferences", "keywords": ["thin", "harness", "openviking"]},
                {"record_kind": "memory", "ov_category": "entities", "keywords": ["agent-basics", "setup", "mcp"]},
                {"record_kind": "memory", "ov_category": "entities", "keywords": ["openviking", "retrieval"]},
            ],
        },
        {
            "name": "migration_event",
            "text": "Decision at Unix time 1777852800: make agent-basics an OpenViking-backed repo harness and supersede the custom repo-local mini-RAG once migration is verified.",
            "expect": [
                {"record_kind": "memory", "ov_category": "events", "keywords": ["1777852800", "openviking", "supersede"]},
            ],
        },
        {
            "name": "lmstudio_crash_case",
            "text": "LM Studio 0.4.12 crashed when the `lms` CLI launched the Electron app from Codex. Workaround: do not call `lms` from Codex; ask the user to start the LM Studio server and use REST endpoints only.",
            "expect": [
                {"record_kind": "memory", "ov_category": "cases", "keywords": ["lms", "crashed", "rest"]},
            ],
        },
        {
            "name": "source_record",
            "text": "Source URL: https://github.com/volcengine/OpenViking",
            "expect": [
                {"record_kind": "resource", "ov_category": "none", "keywords": ["github.com/volcengine/openviking"]},
            ],
        },
        {
            "name": "secret_filter",
            "text": "Durable rule: OpenViking records must never store raw secrets. Temporary key OPENAI_API_KEY=sk-test-1234567890 was used once and must not be preserved.",
            "expect": [
                {"record_kind": "memory", "ov_category": "patterns", "keywords": ["never", "secrets"]},
            ],
            "must_not_contain": ["sk-test-1234567890"],
        },
    ]


def validate_router_shape(payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        return ["top-level payload must contain items array"]
    allowed = set(ROUTER_OUTPUT_SCHEMA["properties"]["items"]["items"]["required"])
    for index, item in enumerate(payload["items"]):
        if not isinstance(item, dict):
            errors.append(f"item {index} is not an object")
            continue
        missing = allowed - set(item)
        extra = set(item) - allowed
        if missing:
            errors.append(f"item {index} missing {sorted(missing)}")
        if extra:
            errors.append(f"item {index} extra {sorted(extra)}")
        if item.get("ov_category") not in [*OV_MEMORY_CATEGORIES, "none"]:
            errors.append(f"item {index} invalid ov_category {item.get('ov_category')}")
    return errors


def item_text(item: dict[str, Any]) -> str:
    parts = [str(value) for value in item.values() if not isinstance(value, list)]
    parts.extend(str(value) for value in item.get("tags", []))
    return " ".join(parts).lower()


def score_case(case: dict[str, Any], obj: Any, raw_output: str, elapsed: float) -> dict[str, Any]:
    score = 0
    max_score = 4
    notes: list[str] = []
    shape_errors = validate_router_shape(obj)
    if not shape_errors:
        score += 4
    else:
        notes.extend(shape_errors[:5])
    items = obj.get("items", []) if isinstance(obj, dict) else []
    for expected in case["expect"]:
        max_score += 5
        matched = False
        for item in items:
            if item.get("record_kind") != expected["record_kind"]:
                continue
            if item.get("ov_category") != expected["ov_category"]:
                continue
            text = item_text(item)
            if all(keyword.lower() in text for keyword in expected["keywords"]):
                matched = True
                break
        if matched:
            score += 5
        else:
            notes.append(f"missed {expected['record_kind']}:{expected['ov_category']}")
    for forbidden in case.get("must_not_contain", []):
        max_score += 4
        if forbidden.lower() not in raw_output.lower():
            score += 4
        else:
            notes.append(f"leaked forbidden text: {forbidden}")
    return {
        "case": case["name"],
        "score": score,
        "max_score": max_score,
        "elapsed_seconds": round(elapsed, 3),
        "notes": notes,
        "items": items,
        "raw_output": raw_output,
    }


def command_lmstudio_route_test(args: argparse.Namespace) -> int:
    status = lmstudio_status_payload(args.base_url, timeout=5)
    if not status.get("ok"):
        print_json(
            {
                "ok": False,
                "model": args.model,
                "error": "LM Studio HTTP server is not reachable",
                "status": status,
                "system_prompt": ROUTER_SYSTEM_PROMPT,
                "schema": ROUTER_OUTPUT_SCHEMA,
            }
        )
        return 1
    cases = routing_cases()
    results = []
    for case in cases:
        user_payload = {
            "instruction": "Route these preprocessed candidates into OV-native memory categories or resource records. Respect suggested_action, suggested_record_kind, and suggested_ov_category unless clearly wrong. Keep one output item per durable idea. For URL-only/source records, use record_kind resource and ov_category none. Durable rules are memory patterns unless a more specific OV memory category clearly applies. System ownership and component-responsibility statements are entities, not skills.",
            "candidates": preingest_candidates(case["name"], case["text"]),
        }
        request = {
            "model": args.model,
            "messages": [
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_payload, indent=2, sort_keys=True)},
            ],
            "temperature": 0,
            "max_tokens": args.max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "openviking_memory_routing",
                    "strict": True,
                    "schema": ROUTER_OUTPUT_SCHEMA,
                },
            },
        }
        started = time.time()
        try:
            response = http_json(args.base_url, "/v1/chat/completions", request, timeout=None)
            raw_output = response["choices"][0]["message"]["content"]
            obj = json.loads(raw_output)
        except Exception as exc:
            raw_output = str(exc)
            obj = {}
        results.append(score_case(case, obj, raw_output, time.time() - started))
    score = sum(item["score"] for item in results)
    max_score = sum(item["max_score"] for item in results)
    payload = {
        "ok": score == max_score,
        "model": args.model,
        "score": score,
        "max_score": max_score,
        "score_percent": round((score / max_score) * 100, 1) if max_score else 0,
        "system_prompt": ROUTER_SYSTEM_PROMPT,
        "schema": ROUTER_OUTPUT_SCHEMA,
        "results": results,
    }
    print_json(payload)
    return 0 if payload["ok"] else 1


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]
    meta = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, body


def legacy_to_ov_category(path: Path, legacy_type: str, text: str) -> tuple[str, str, bool]:
    lower = text.lower()
    path_text = path.as_posix()
    if "/memories/profile/" in path_text:
        return "profile", "OV-native profile memory", False
    if "/memories/preferences/" in path_text:
        return "preferences", "OV-native preference memory", False
    if "/memories/entities/" in path_text:
        return "entities", "OV-native entity memory", False
    if "/memories/events/" in path_text:
        return "events", "OV-native event memory", False
    if "/memories/cases/" in path_text:
        return "cases", "OV-native case memory", False
    if "/memories/patterns/" in path_text:
        return "patterns", "OV-native pattern memory", False
    if "/memories/tools/" in path_text:
        return "tools", "OV-native tool memory", False
    if "/memories/skills/" in path_text or "/skills/" in path_text:
        return "skills", "OV-native skill memory or workflow", False
    if "/resources/" in path_text:
        return "none", "OV-native resource, not memory", False
    if "/imports/" in path_text or "/inbox/" in path_text:
        return "none", "copied source material awaiting adaptation", True
    if legacy_type == "preference":
        return "preferences", "user/project preference", False
    if legacy_type == "fact":
        return "entities", "stable project/system fact", False
    if legacy_type == "event":
        return "events", "dated event", False
    if legacy_type == "source":
        return "none", "documentation resource, not memory", False
    if legacy_type == "procedure":
        return "patterns", "repeatable process", False
    if legacy_type == "gotcha":
        return "cases", "problem/caveat/workaround", False
    if legacy_type == "decision":
        if "user wants" in lower or "user prefers" in lower:
            return "preferences", "ongoing preference", True
        return "events", "decision/milestone", False
    if "documentations/sources" in str(path):
        return "none", "documentation resource, not memory", False
    if "documentations/procedures" in str(path):
        return "patterns", "repeatable process", False
    return "entities", "fallback stable record", True


def command_migrate_inventory(args: argparse.Namespace) -> int:
    repo = repo_root_from_args(args)
    memory_root = repo / ".agents" / "memory"
    output_path = repo / ".agents" / "openviking" / "migration-manifest.json"
    records = []
    for path in sorted(memory_root.rglob("*.md")):
        if path.name in {"SCHEMA.md", "INDEX.md", "ADAPTATION.md", "README.md"} or "/templates/" in str(path):
            continue
        text = path.read_text(encoding="utf-8")
        meta, body = parse_front_matter(text)
        legacy_type = meta.get("type", "")
        category, reason, review = legacy_to_ov_category(path, legacy_type, text)
        path_text = str(path)
        if category == "none" and ("documentations/sources" in path_text or "/resources/" in path_text):
            record_kind = "resource"
        elif "/skills/" in path_text and "/memories/skills/" not in path_text:
            record_kind = "skill"
        else:
            record_kind = "memory"
        if category == "none" and record_kind not in {"resource", "skill"}:
            record_kind = "ignore"
        is_ov_native = any(token in path_text for token in ["/memories/", "/resources/", "/skills/"])
        stale = False if is_ov_native else any(token in body.lower() for token in ["memoryhub", "repo-local mini-rag", "compatibility"])
        records.append(
            {
                "legacy_path": str(path.relative_to(repo)),
                "legacy_type": legacy_type or "unknown",
                "title": meta.get("title", path.stem),
                "status": meta.get("status", ""),
                "record_kind": record_kind,
                "ov_category": category,
                "reason": reason,
                "requires_human_review": review or stale,
                "stale_or_transitional": stale,
            }
        )
    payload = {
        "version": 1,
        "generated": int(time.time()),
        "repo": str(repo),
        "policy": "OpenViking native categories are canonical; source records are resources, not memory.",
        "legacy_snapshots": str(repo / ".agents" / "openviking" / "legacy-memory"),
        "records": records,
    }
    if args.write:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            payload["written_to"] = str(output_path)
        except OSError as exc:
            payload["write_error"] = str(exc)
            payload["write_target"] = str(output_path)
            print_json(payload)
            return 1
    print_json(payload)
    return 0


MCP_SERVER_NAME = "agent-basics-openviking"
MCP_SERVER_VERSION = "0.1.0"
MCP_SUPPORTED_PROTOCOL_VERSIONS = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]
MCP_ERROR_PARSE = -32700
MCP_ERROR_INVALID_REQUEST = -32600
MCP_ERROR_METHOD_NOT_FOUND = -32601
MCP_ERROR_INVALID_PARAMS = -32602
MCP_ERROR_INTERNAL = -32603


MCP_CWD_SCHEMA = {
    "type": "string",
    "description": "Preferred current working directory for this tool call. May be the repo root or any directory inside it.",
}

MCP_REPO_PATH_SCHEMA = {
    "type": "string",
    "description": "Backward-compatible alias for cwd. Prefer cwd for new clients.",
}

MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "search",
        "title": "Search repo OpenViking context",
        "description": "Repo-scoped semantic search across OpenViking memories, resources, and skills.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 5},
                "include_global": {
                    "type": "boolean",
                    "default": False,
                    "description": "When true, allow global OpenViking search outside the repo namespace.",
                },
                "cwd": MCP_CWD_SCHEMA,
                "repo_path": MCP_REPO_PATH_SCHEMA,
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "read",
        "title": "Read OpenViking URI",
        "description": "Read exact content from a URI returned by repo-scoped search.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "uri": {"type": "string"},
                "allow_global": {
                    "type": "boolean",
                    "default": False,
                    "description": "When true, allow reads outside the repo namespace.",
                },
                "cwd": MCP_CWD_SCHEMA,
                "repo_path": MCP_REPO_PATH_SCHEMA,
            },
            "required": ["uri"],
            "additionalProperties": False,
        },
    },
    {
        "name": "record",
        "title": "Record durable OpenViking memory",
        "description": "Write a repo source-store memory file and import it into the repo OpenViking memory namespace.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": OV_MEMORY_CATEGORIES},
                "title": {"type": "string"},
                "content": {"type": "string"},
                "summary": {"type": "string"},
                "tags": {"oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]},
                "status": {"type": "string", "default": "active"},
                "wait": {"type": "boolean", "default": True},
                "cwd": MCP_CWD_SCHEMA,
                "repo_path": MCP_REPO_PATH_SCHEMA,
            },
            "required": ["category", "title", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "add_resource",
        "title": "Add repo OpenViking resource",
        "description": "Ingest a local file, directory, or URL into the repo OpenViking resource namespace.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path_or_url": {"type": "string"},
                "reason": {"type": "string"},
                "instruction": {"type": "string"},
                "wait": {"type": "boolean", "default": True},
                "cwd": MCP_CWD_SCHEMA,
                "repo_path": MCP_REPO_PATH_SCHEMA,
            },
            "required": ["path_or_url"],
            "additionalProperties": False,
        },
    },
    {
        "name": "add_skill",
        "title": "Add OpenViking skill",
        "description": "Register a skill file or raw skill content with OpenViking.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path_or_content": {"type": "string"},
                "wait": {"type": "boolean", "default": True},
                "cwd": MCP_CWD_SCHEMA,
                "repo_path": MCP_REPO_PATH_SCHEMA,
            },
            "required": ["path_or_content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "ingest_changed",
        "title": "Import changed repo memory source store",
        "description": "Import reviewed OV-native source-store memories, resources, and skills into OpenViking.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_review": {"type": "boolean", "default": False},
                "cwd": MCP_CWD_SCHEMA,
                "repo_path": MCP_REPO_PATH_SCHEMA,
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "status",
        "title": "Report repo OpenViking status",
        "description": "Report repo namespaces, source-store staleness, OpenViking health, and optional provider health.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "online": {"type": "boolean", "default": True},
                "providers": {"type": "boolean", "default": False},
                "cwd": MCP_CWD_SCHEMA,
                "repo_path": MCP_REPO_PATH_SCHEMA,
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "doctor",
        "title": "Diagnose OpenViking setup",
        "description": "Run the same repo-aware status checks as status, with provider checks disabled by default.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "online": {"type": "boolean", "default": True},
                "providers": {"type": "boolean", "default": False},
                "cwd": MCP_CWD_SCHEMA,
                "repo_path": MCP_REPO_PATH_SCHEMA,
            },
            "additionalProperties": False,
        },
    },
]


class McpError(Exception):
    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def mcp_protocol_version(params: dict[str, Any]) -> str:
    requested = str(params.get("protocolVersion", ""))
    if requested in MCP_SUPPORTED_PROTOCOL_VERSIONS:
        return requested
    return MCP_SUPPORTED_PROTOCOL_VERSIONS[0]


def mcp_json_response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def mcp_json_error(request_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
    if data is not None:
        payload["error"]["data"] = data
    return payload


def mcp_emit(message: dict[str, Any]) -> None:
    print(json.dumps(message, separators=(",", ":"), ensure_ascii=False), flush=True)


def mcp_tool_result(payload: dict[str, Any], *, is_error: bool | None = None) -> dict[str, Any]:
    error = bool(not payload.get("ok")) if is_error is None else is_error
    text = json.dumps(payload, indent=2, sort_keys=True)
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": payload,
        "isError": error,
    }


def mcp_arguments(params: dict[str, Any]) -> dict[str, Any]:
    arguments = params.get("arguments", {})
    if arguments is None:
        return {}
    if not isinstance(arguments, dict):
        raise McpError(MCP_ERROR_INVALID_PARAMS, "tools/call arguments must be an object")
    return arguments


def mcp_string(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise McpError(MCP_ERROR_INVALID_PARAMS, f"`{key}` must be a non-empty string")
    return value


def mcp_bool(arguments: dict[str, Any], key: str, default: bool = False) -> bool:
    value = arguments.get(key, default)
    if not isinstance(value, bool):
        raise McpError(MCP_ERROR_INVALID_PARAMS, f"`{key}` must be a boolean")
    return value


def mcp_int(arguments: dict[str, Any], key: str, default: int, *, minimum: int, maximum: int) -> int:
    value = arguments.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise McpError(MCP_ERROR_INVALID_PARAMS, f"`{key}` must be an integer")
    if value < minimum or value > maximum:
        raise McpError(MCP_ERROR_INVALID_PARAMS, f"`{key}` must be between {minimum} and {maximum}")
    return value


def resolve_repo_from_cwd(value: str | Path) -> Path:
    path = Path(value).expanduser().resolve()
    if path.is_file():
        path = path.parent
    for candidate in [path, *path.parents]:
        if (candidate / ".agents" / "config.toml").exists():
            return candidate
        if (candidate / ".agents").is_dir() and (candidate / "Agents.md").exists():
            return candidate
        if (candidate / ".git").exists():
            return candidate
    return path


def mcp_repo(arguments: dict[str, Any], default_repo: Path) -> Path:
    cwd_value = arguments.get("cwd")
    repo_path_value = arguments.get("repo_path")
    has_cwd = cwd_value is not None and cwd_value != ""
    has_repo_path = repo_path_value is not None and repo_path_value != ""
    if has_cwd:
        if not isinstance(cwd_value, str):
            raise McpError(MCP_ERROR_INVALID_PARAMS, "`cwd` must be a string")
        if has_repo_path:
            if not isinstance(repo_path_value, str):
                raise McpError(MCP_ERROR_INVALID_PARAMS, "`repo_path` must be a string")
            cwd_repo = resolve_repo_from_cwd(cwd_value)
            repo_path = resolve_repo_from_cwd(repo_path_value)
            if cwd_repo != repo_path:
                raise McpError(MCP_ERROR_INVALID_PARAMS, "`cwd` and `repo_path` resolve to different repositories")
        return resolve_repo_from_cwd(cwd_value)
    if has_repo_path:
        if not isinstance(repo_path_value, str):
            raise McpError(MCP_ERROR_INVALID_PARAMS, "`repo_path` must be a string")
        return resolve_repo_from_cwd(repo_path_value)
    return resolve_repo_from_cwd(default_repo)


def ov_ingest_changed_payload(repo: Path, *, include_review: bool = False, dry_run: bool = False) -> dict[str, Any]:
    args = argparse.Namespace(
        repo=str(repo),
        target=None,
        memory_target=DEFAULT_OV_MEMORY_TARGET,
        timeout=DEFAULT_OV_VLM_TIMEOUT_SECONDS,
        include_review=include_review,
        force=False,
        dry_run=dry_run,
        wait=True,
        wait_memory=True,
        wait_resources=True,
        busy_retries=120,
        busy_delay=5,
        write=not dry_run,
    )
    output = io.StringIO()
    with redirect_stdout(output):
        returncode = command_ov_import_repo_memory(args)
    try:
        payload = json.loads(output.getvalue())
    except json.JSONDecodeError:
        payload = {"ok": False, "stdout": output.getvalue(), "error": "ingest output was not JSON"}
    payload.setdefault("ok", returncode == 0)
    payload["returncode"] = returncode
    return payload


def mcp_call_tool(default_repo: Path, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    repo = mcp_repo(arguments, default_repo)
    if name == "search":
        return mcp_tool_result(
            ov_search_payload(
                repo,
                query=mcp_string(arguments, "query"),
                limit=mcp_int(arguments, "limit", 5, minimum=1, maximum=50),
                include_global=mcp_bool(arguments, "include_global", False),
                timeout=None,
            )
        )
    if name == "read":
        return mcp_tool_result(
            ov_read_payload(
                repo,
                uri=mcp_string(arguments, "uri"),
                allow_global=mcp_bool(arguments, "allow_global", False),
                timeout=None,
            )
        )
    if name == "record":
        return mcp_tool_result(
            ov_record_payload(
                repo,
                category=mcp_string(arguments, "category"),
                title=mcp_string(arguments, "title"),
                content=mcp_string(arguments, "content"),
                summary=str(arguments.get("summary", "") or ""),
                tags=arguments.get("tags", []),
                status=str(arguments.get("status", "active") or "active"),
                wait=mcp_bool(arguments, "wait", True),
            )
        )
    if name == "add_resource":
        return mcp_tool_result(
            ov_add_resource_payload(
                repo,
                source=mcp_string(arguments, "path_or_url"),
                reason=str(arguments.get("reason", "agent-basics repo resource import") or "agent-basics repo resource import"),
                instruction=str(arguments.get("instruction", "") or ""),
                wait=mcp_bool(arguments, "wait", True),
            )
        )
    if name == "add_skill":
        return mcp_tool_result(
            ov_add_skill_payload(
                repo,
                data=mcp_string(arguments, "path_or_content"),
                wait=mcp_bool(arguments, "wait", True),
            )
        )
    if name == "ingest_changed":
        return mcp_tool_result(ov_ingest_changed_payload(repo, include_review=mcp_bool(arguments, "include_review", False)))
    if name in {"status", "doctor"}:
        return mcp_tool_result(
            ov_status_payload(
                repo,
                online=mcp_bool(arguments, "online", True),
                providers=mcp_bool(arguments, "providers", False),
            )
        )
    raise McpError(MCP_ERROR_METHOD_NOT_FOUND, f"unknown tool: {name}")


def mcp_handle_request(default_repo: Path, message: dict[str, Any]) -> dict[str, Any] | None:
    if message.get("jsonrpc") != "2.0":
        raise McpError(MCP_ERROR_INVALID_REQUEST, "jsonrpc must be 2.0")
    method = message.get("method")
    request_id = message.get("id")
    is_notification = "id" not in message
    if not isinstance(method, str):
        raise McpError(MCP_ERROR_INVALID_REQUEST, "method must be a string")
    if is_notification:
        return None
    params = message.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise McpError(MCP_ERROR_INVALID_PARAMS, "params must be an object")

    if method == "initialize":
        return mcp_json_response(
            request_id,
            {
                "protocolVersion": mcp_protocol_version(params),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {
                    "name": MCP_SERVER_NAME,
                    "title": "agent-basics OpenViking",
                    "version": MCP_SERVER_VERSION,
                },
                "instructions": (
                    "Use search before answering vague or history-dependent project requests. "
                    "Use record for durable decisions, preferences, facts, cases, events, patterns, tools, and skills. "
                    "Pass cwd on every repo-scoped tool call; it may be the repository root or any directory inside it. "
                    "repo_path is supported only as a backward-compatible alias."
                ),
            },
        )
    if method == "ping":
        return mcp_json_response(request_id, {})
    if method == "tools/list":
        return mcp_json_response(request_id, {"tools": MCP_TOOLS})
    if method == "tools/call":
        name = params.get("name")
        if not isinstance(name, str) or not name:
            raise McpError(MCP_ERROR_INVALID_PARAMS, "tools/call params.name must be a non-empty string")
        return mcp_json_response(request_id, mcp_call_tool(default_repo, name, mcp_arguments(params)))
    raise McpError(MCP_ERROR_METHOD_NOT_FOUND, f"unknown method: {method}")


def mcp_handle_message(default_repo: Path, message: Any) -> list[dict[str, Any]]:
    if isinstance(message, list):
        responses: list[dict[str, Any]] = []
        for item in message:
            responses.extend(mcp_handle_message(default_repo, item))
        return responses
    if not isinstance(message, dict):
        return [mcp_json_error(None, MCP_ERROR_INVALID_REQUEST, "JSON-RPC message must be an object")]
    try:
        response = mcp_handle_request(default_repo, message)
        return [response] if response is not None else []
    except McpError as exc:
        return [mcp_json_error(message.get("id"), exc.code, exc.message, exc.data)]
    except Exception as exc:
        return [mcp_json_error(message.get("id"), MCP_ERROR_INTERNAL, "internal error", str(exc))]


def command_mcp(args: argparse.Namespace) -> int:
    default_repo = repo_root_from_args(args)
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            mcp_emit(mcp_json_error(None, MCP_ERROR_PARSE, "parse error", str(exc)))
            continue
        for response in mcp_handle_message(default_repo, message):
            mcp_emit(response)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-basics-ov")
    parser.add_argument("--repo", help="Repository root for repo-aware operations")
    subparsers = parser.add_subparsers(dest="command", required=True)

    mcp = subparsers.add_parser("mcp")
    mcp.set_defaults(func=command_mcp)

    ov = subparsers.add_parser("ov")
    ov_sub = ov.add_subparsers(dest="ov_command", required=True)
    doctor = ov_sub.add_parser("doctor")
    doctor.add_argument("--online", action="store_true")
    doctor.add_argument("--providers", action="store_true")
    doctor.add_argument("--provider", choices=["ollama", "lmstudio"], default=DEFAULT_RUNTIME_PROVIDER)
    doctor.add_argument("--base-url", default=DEFAULT_OLLAMA_BASE)
    doctor.add_argument("--timeout", type=float, default=5)
    doctor.set_defaults(func=command_ov_doctor)

    install = ov_sub.add_parser("install-system")
    install.add_argument("--home", default=str(DEFAULT_OV_HOME))
    install.add_argument("--python", default="3.12")
    install.add_argument("--package", default="openviking")
    install.add_argument("--force", action="store_true")
    install.set_defaults(func=command_ov_install_system)

    bootstrap = ov_sub.add_parser("bootstrap-system")
    bootstrap.add_argument("--home", default=str(DEFAULT_OV_HOME))
    bootstrap.add_argument("--python", default="3.12")
    bootstrap.add_argument("--package", default="openviking")
    bootstrap.add_argument("--config")
    bootstrap.add_argument("--cli-config")
    bootstrap.add_argument("--provider", choices=["ollama", "lmstudio"], default=DEFAULT_RUNTIME_PROVIDER)
    bootstrap.add_argument("--runtime", choices=["ollama", "lmstudio", "none"], default=DEFAULT_RUNTIME_PROVIDER)
    bootstrap.add_argument("--runtime-best-effort", action="store_true")
    bootstrap.add_argument("--base-url")
    bootstrap.add_argument("--provider-base")
    bootstrap.add_argument("--api-key")
    bootstrap.add_argument("--lmstudio-base", default=None)
    bootstrap.add_argument("--chat-model", default=DEFAULT_CHAT_MODEL)
    bootstrap.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    bootstrap.add_argument("--embedding-dimension", type=int, default=768)
    bootstrap.add_argument("--vlm-timeout", type=int, default=DEFAULT_OV_VLM_TIMEOUT_SECONDS)
    bootstrap.add_argument("--server-url", default="http://127.0.0.1:1933")
    bootstrap.add_argument("--cli-timeout", type=int, default=DEFAULT_OV_VLM_TIMEOUT_SECONDS)
    bootstrap.add_argument("--service", choices=["auto", "always", "never"], default="auto")
    bootstrap.add_argument("--service-best-effort", action="store_true")
    bootstrap.add_argument("--ollama-install", choices=["auto", "always", "never"], default="auto")
    bootstrap.add_argument("--ollama-pull", choices=["auto", "always", "never"], default="auto")
    bootstrap.add_argument("--ollama-timeout", type=float, default=5)
    bootstrap.add_argument("--lmstudio", choices=["auto", "always", "never"], default="never")
    bootstrap.add_argument("--lmstudio-best-effort", action="store_true")
    bootstrap.add_argument("--lmstudio-min-memory-gb", type=float, default=DEFAULT_LMSTUDIO_MIN_MEMORY_GB)
    bootstrap.add_argument("--lmstudio-cask", default=DEFAULT_LMSTUDIO_CASK)
    bootstrap.add_argument("--lmstudio-app-path", default=str(DEFAULT_LMSTUDIO_APP))
    bootstrap.add_argument("--lmstudio-lms-bin")
    bootstrap.add_argument("--lmstudio-wait-server-seconds", type=float, default=30)
    bootstrap.add_argument("--server-bin")
    bootstrap.add_argument("--label", default=DEFAULT_OV_SERVICE_LABEL)
    bootstrap.add_argument("--plist")
    bootstrap.add_argument("--service-timeout", type=float, default=DEFAULT_OV_SERVICE_COMMAND_TIMEOUT_SECONDS)
    bootstrap.add_argument("--force-install", action="store_true")
    bootstrap.add_argument("--force-config", action="store_true")
    bootstrap.add_argument("--force-service", action="store_true")
    bootstrap.add_argument("--no-load", action="store_true")
    bootstrap.add_argument("--dry-run", action="store_true")
    bootstrap.set_defaults(func=command_ov_bootstrap_system)

    config = ov_sub.add_parser("write-default-config")
    config.add_argument("--config", default=str(DEFAULT_OV_CONFIG))
    config.add_argument("--cli-config", default=str(DEFAULT_OV_CLI_CONFIG))
    config.add_argument("--home", default=str(DEFAULT_OV_HOME))
    config.add_argument("--provider", choices=["ollama", "lmstudio"], default=DEFAULT_RUNTIME_PROVIDER)
    config.add_argument("--base-url")
    config.add_argument("--provider-base")
    config.add_argument("--api-key")
    config.add_argument("--lmstudio-base", default=None)
    config.add_argument("--chat-model", default=DEFAULT_CHAT_MODEL)
    config.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    config.add_argument("--embedding-dimension", type=int, default=768)
    config.add_argument("--vlm-timeout", type=int, default=DEFAULT_OV_VLM_TIMEOUT_SECONDS)
    config.add_argument("--server-url", default="http://127.0.0.1:1933")
    config.add_argument("--cli-timeout", type=int, default=DEFAULT_OV_VLM_TIMEOUT_SECONDS)
    config.add_argument("--force", action="store_true")
    config.set_defaults(func=command_ov_write_default_config)

    server = ov_sub.add_parser("server")
    server.add_argument("--server-bin")
    server.add_argument("--config", default=str(DEFAULT_OV_CONFIG))
    server.add_argument("--host")
    server.add_argument("--port", type=int)
    server.add_argument("--workers", type=int)
    server.add_argument("--bot", action="store_true")
    server.add_argument("--with-bot", action="store_true")
    server.add_argument("--dry-run", action="store_true")
    server.set_defaults(func=command_ov_server)

    service = ov_sub.add_parser("service")
    service_sub = service.add_subparsers(dest="service_action", required=True)

    def add_service_args(service_parser: argparse.ArgumentParser) -> None:
        service_parser.add_argument("--home", default=str(DEFAULT_OV_HOME))
        service_parser.add_argument("--server-bin")
        service_parser.add_argument("--config")
        service_parser.add_argument("--label", default=DEFAULT_OV_SERVICE_LABEL)
        service_parser.add_argument("--plist")
        service_parser.add_argument("--timeout", type=float, default=DEFAULT_OV_SERVICE_COMMAND_TIMEOUT_SECONDS)
        service_parser.add_argument("--dry-run", action="store_true")
        service_parser.set_defaults(func=command_ov_service)

    service_install = service_sub.add_parser("install")
    add_service_args(service_install)
    service_install.add_argument("--force", action="store_true")
    service_install.add_argument("--no-load", action="store_true")

    service_status = service_sub.add_parser("status")
    add_service_args(service_status)

    service_start = service_sub.add_parser("start")
    add_service_args(service_start)

    service_stop = service_sub.add_parser("stop")
    add_service_args(service_stop)

    service_restart = service_sub.add_parser("restart")
    add_service_args(service_restart)
    service_restart.add_argument("--force", action="store_true")
    service_restart.add_argument("--no-load", action="store_true")

    service_uninstall = service_sub.add_parser("uninstall")
    add_service_args(service_uninstall)

    import_memory = ov_sub.add_parser("import-repo-memory")
    import_memory.add_argument("--target", default=None)
    import_memory.add_argument("--memory-target", default=DEFAULT_OV_MEMORY_TARGET)
    import_memory.add_argument("--timeout", type=int, default=DEFAULT_OV_VLM_TIMEOUT_SECONDS)
    import_memory.add_argument("--include-review", action="store_true")
    import_memory.add_argument("--force", action="store_true")
    import_memory.add_argument("--dry-run", action="store_true")
    import_memory.add_argument("--wait", action="store_true")
    import_memory.add_argument("--wait-memory", action="store_true")
    import_memory.add_argument("--wait-resources", action="store_true")
    import_memory.add_argument("--busy-retries", type=int, default=120)
    import_memory.add_argument("--busy-delay", type=float, default=5)
    import_memory.add_argument("--write", action="store_true")
    import_memory.set_defaults(func=command_ov_import_repo_memory)

    search = ov_sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--uri")
    search.add_argument("--threshold", type=float)
    search.add_argument("--include-global", action="store_true")
    search.set_defaults(func=command_ov_search)

    read = ov_sub.add_parser("read")
    read.add_argument("uri")
    read.add_argument("--allow-global", action="store_true")
    read.set_defaults(func=command_ov_read)

    record = ov_sub.add_parser("record")
    record.add_argument("category", choices=OV_MEMORY_CATEGORIES)
    record.add_argument("title")
    record.add_argument("--content")
    record.add_argument("--from-file")
    record.add_argument("--summary", default="")
    record.add_argument("--tags", default="")
    record.add_argument("--tag", action="append")
    record.add_argument("--status", default="active")
    record.add_argument("--timeout", type=int, default=DEFAULT_OV_VLM_TIMEOUT_SECONDS)
    record.add_argument("--no-wait", action="store_true")
    record.add_argument("--dry-run", action="store_true")
    record.set_defaults(func=command_ov_record)

    add_resource = ov_sub.add_parser("add-resource")
    add_resource.add_argument("path_or_url")
    add_resource.add_argument("--target")
    add_resource.add_argument("--reason", default="agent-basics repo resource import")
    add_resource.add_argument("--instruction", default="")
    add_resource.add_argument("--timeout", type=int, default=DEFAULT_OV_VLM_TIMEOUT_SECONDS)
    add_resource.add_argument("--no-wait", action="store_true")
    add_resource.add_argument("--dry-run", action="store_true")
    add_resource.set_defaults(func=command_ov_add_resource)

    add_skill = ov_sub.add_parser("add-skill")
    add_skill.add_argument("path_or_content")
    add_skill.add_argument("--timeout", type=int, default=DEFAULT_OV_VLM_TIMEOUT_SECONDS)
    add_skill.add_argument("--no-wait", action="store_true")
    add_skill.add_argument("--dry-run", action="store_true")
    add_skill.set_defaults(func=command_ov_add_skill)

    ingest_changed = ov_sub.add_parser("ingest-changed")
    ingest_changed.add_argument("--target", default=None)
    ingest_changed.add_argument("--memory-target", default=DEFAULT_OV_MEMORY_TARGET)
    ingest_changed.add_argument("--timeout", type=int, default=DEFAULT_OV_VLM_TIMEOUT_SECONDS)
    ingest_changed.add_argument("--include-review", action="store_true")
    ingest_changed.add_argument("--dry-run", action="store_true")
    ingest_changed.add_argument("--busy-retries", type=int, default=120)
    ingest_changed.add_argument("--busy-delay", type=float, default=5)
    ingest_changed.set_defaults(func=command_ov_ingest_changed)

    install_hooks = ov_sub.add_parser("install-hooks")
    install_hooks.add_argument("--force", action="store_true")
    install_hooks.set_defaults(func=command_ov_install_hooks)

    hook = ov_sub.add_parser("hook")
    hook.add_argument("event", choices=["pre-commit", "post-merge"])
    hook.add_argument("--include-review", action="store_true")
    hook.add_argument("--dry-run", action="store_true")
    hook.add_argument("--no-prompt", action="store_true")
    hook.set_defaults(func=command_ov_hook)

    status_parser = ov_sub.add_parser("status")
    status_parser.add_argument("--offline", action="store_true")
    status_parser.add_argument("--providers", action="store_true")
    status_parser.add_argument("--provider", choices=["ollama", "lmstudio"], default=DEFAULT_RUNTIME_PROVIDER)
    status_parser.add_argument("--base-url", default=DEFAULT_OLLAMA_BASE)
    status_parser.set_defaults(func=command_ov_status)

    ollama = subparsers.add_parser("ollama")
    ollama_sub = ollama.add_subparsers(dest="ollama_command", required=True)
    ollama_status = ollama_sub.add_parser("status")
    ollama_status.add_argument("--base-url", default=DEFAULT_OLLAMA_BASE)
    ollama_status.add_argument("--model", default=DEFAULT_CHAT_MODEL)
    ollama_status.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    ollama_status.add_argument("--timeout", type=float, default=5)
    ollama_status.set_defaults(func=command_ollama_status)

    ollama_bootstrap = ollama_sub.add_parser("bootstrap")
    ollama_bootstrap.add_argument("--base-url", default=DEFAULT_OLLAMA_BASE)
    ollama_bootstrap.add_argument("--model", default=DEFAULT_CHAT_MODEL)
    ollama_bootstrap.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    ollama_bootstrap.add_argument("--pull-model", action="append", default=[])
    ollama_bootstrap.add_argument("--install", choices=["auto", "always", "never"], default="auto")
    ollama_bootstrap.add_argument("--pull", choices=["auto", "always", "never"], default="auto")
    ollama_bootstrap.add_argument("--timeout", type=float, default=5)
    ollama_bootstrap.add_argument("--dry-run", action="store_true")
    ollama_bootstrap.set_defaults(func=command_ollama_bootstrap)

    ollama_pull = ollama_sub.add_parser("pull")
    ollama_pull.add_argument("--base-url", default=DEFAULT_OLLAMA_BASE)
    ollama_pull.add_argument("--model", default=DEFAULT_CHAT_MODEL)
    ollama_pull.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    ollama_pull.add_argument("--pull-model", action="append", default=[])
    ollama_pull.add_argument("--timeout", type=float, default=5)
    ollama_pull.add_argument("--dry-run", action="store_true")
    ollama_pull.set_defaults(func=command_ollama_pull)

    lm = subparsers.add_parser("lmstudio")
    lm_sub = lm.add_subparsers(dest="lmstudio_command", required=True)
    status = lm_sub.add_parser("status")
    status.add_argument("--base-url", default=DEFAULT_LM_STUDIO_BASE)
    status.add_argument("--timeout", type=float, default=5)
    status.set_defaults(func=command_lmstudio_status)

    hardware = lm_sub.add_parser("hardware")
    hardware.set_defaults(func=command_lmstudio_hardware)

    bootstrap_lm = lm_sub.add_parser("bootstrap")
    bootstrap_lm.add_argument("--base-url", default=DEFAULT_LM_STUDIO_BASE)
    bootstrap_lm.add_argument("--lmstudio-home", default=str(DEFAULT_LMSTUDIO_HOME))
    bootstrap_lm.add_argument("--model", default=DEFAULT_LMSTUDIO_CHAT_MODEL)
    bootstrap_lm.add_argument("--embedding-model", default=DEFAULT_LMSTUDIO_EMBEDDING_MODEL)
    bootstrap_lm.add_argument("--download-model", action="append", default=[])
    bootstrap_lm.add_argument("--min-memory-gb", type=float, default=DEFAULT_LMSTUDIO_MIN_MEMORY_GB)
    bootstrap_lm.add_argument("--allow-non-macos", action="store_true")
    bootstrap_lm.add_argument("--force-hardware", action="store_true")
    bootstrap_lm.add_argument("--install", choices=["auto", "always", "never"], default="auto")
    bootstrap_lm.add_argument("--service", choices=["auto", "always", "never"], default="auto")
    bootstrap_lm.add_argument("--configure", choices=["auto", "always", "never"], default="auto")
    bootstrap_lm.add_argument("--download", choices=["auto", "always", "never"], default="auto")
    bootstrap_lm.add_argument("--cask", default=DEFAULT_LMSTUDIO_CASK)
    bootstrap_lm.add_argument("--app-path", default=str(DEFAULT_LMSTUDIO_APP))
    bootstrap_lm.add_argument("--lms-bin")
    bootstrap_lm.add_argument("--port", type=int, default=DEFAULT_LMSTUDIO_PORT)
    bootstrap_lm.add_argument("--label", default=DEFAULT_LMSTUDIO_SERVICE_LABEL)
    bootstrap_lm.add_argument("--plist")
    bootstrap_lm.add_argument("--timeout", type=float, default=5)
    bootstrap_lm.add_argument("--service-timeout", type=float, default=DEFAULT_OV_SERVICE_COMMAND_TIMEOUT_SECONDS)
    bootstrap_lm.add_argument("--wait-server-seconds", type=float, default=30)
    bootstrap_lm.add_argument("--force-install", action="store_true")
    bootstrap_lm.add_argument("--force-service", action="store_true")
    bootstrap_lm.add_argument("--no-load", action="store_true")
    bootstrap_lm.add_argument("--best-effort", action="store_true")
    bootstrap_lm.add_argument("--dry-run", action="store_true")
    bootstrap_lm.set_defaults(func=command_lmstudio_bootstrap)

    service_lm = lm_sub.add_parser("service")
    service_lm.add_argument("service_action", choices=["install", "status", "start", "stop", "restart", "uninstall"])
    service_lm.add_argument("--lmstudio-home", default=str(DEFAULT_LMSTUDIO_HOME))
    service_lm.add_argument("--lms-bin")
    service_lm.add_argument("--port", type=int, default=DEFAULT_LMSTUDIO_PORT)
    service_lm.add_argument("--label", default=DEFAULT_LMSTUDIO_SERVICE_LABEL)
    service_lm.add_argument("--plist")
    service_lm.add_argument("--timeout", type=float, default=DEFAULT_OV_SERVICE_COMMAND_TIMEOUT_SECONDS)
    service_lm.add_argument("--dry-run", action="store_true")
    service_lm.add_argument("--force", action="store_true")
    service_lm.add_argument("--no-load", action="store_true")
    service_lm.set_defaults(func=command_lmstudio_service)

    plan = lm_sub.add_parser("plan")
    plan.add_argument("--base-url", default=DEFAULT_LM_STUDIO_BASE)
    plan.add_argument("--model", default=DEFAULT_LMSTUDIO_CHAT_MODEL)
    plan.add_argument("--embedding-model", default=DEFAULT_LMSTUDIO_EMBEDDING_MODEL)
    plan.add_argument("--max-tokens", type=int, default=2200)
    plan.add_argument("--timeout", type=float, default=5)
    plan.set_defaults(func=command_lmstudio_plan)

    configure = lm_sub.add_parser("configure")
    configure.add_argument("--base-url", default=DEFAULT_LM_STUDIO_BASE)
    configure.add_argument("--lmstudio-home", default=str(DEFAULT_LMSTUDIO_HOME))
    configure.add_argument("--model", default=DEFAULT_LMSTUDIO_CHAT_MODEL)
    configure.add_argument("--embedding-model", default=DEFAULT_LMSTUDIO_EMBEDDING_MODEL)
    configure.add_argument("--cpu-threads", type=int, default=0)
    configure.add_argument("--parallel", type=int, default=1)
    configure.add_argument("--context-length", type=int, default=0)
    configure.add_argument("--embedding-context-length", type=int, default=2048)
    configure.add_argument("--kv-cache-quantization", default="q4_0")
    configure.add_argument("--gpu-offload-ratio", type=float, default=1.0)
    configure.add_argument("--temperature", type=float, default=0)
    configure.add_argument("--timeout", type=float, default=5)
    configure.add_argument("--write", action="store_true")
    configure.add_argument("--backup", action=argparse.BooleanOptionalAction, default=True)
    configure.add_argument("--include-embedding", action=argparse.BooleanOptionalAction, default=True)
    configure.add_argument("--include-routing-defaults", action="store_true")
    configure.add_argument("--verbose-config", action="store_true")
    configure.set_defaults(func=command_lmstudio_configure)

    load = lm_sub.add_parser("load")
    load.add_argument("--base-url", default=DEFAULT_LM_STUDIO_BASE)
    load.add_argument("--model", default=DEFAULT_LMSTUDIO_CHAT_MODEL)
    load.add_argument("--embedding-model", default=DEFAULT_LMSTUDIO_EMBEDDING_MODEL)
    load.add_argument("--max-tokens", type=int, default=2200)
    load.add_argument("--timeout", type=float, default=5)
    load.add_argument("--dry-run", action="store_true")
    load.add_argument("--unload-conflicts", action="store_true")
    load.add_argument("--reload-mismatched", action="store_true")
    load.set_defaults(func=command_lmstudio_load)

    unload = lm_sub.add_parser("unload")
    unload.add_argument("identifier", nargs="?", default=DEFAULT_LMSTUDIO_CHAT_MODEL)
    unload.add_argument("--base-url", default=DEFAULT_LM_STUDIO_BASE)
    unload.add_argument("--timeout", type=float, default=5)
    unload.add_argument("--all", action="store_true")
    unload.set_defaults(func=command_lmstudio_unload)

    route_test = lm_sub.add_parser("route-test")
    route_test.add_argument("--base-url", default=DEFAULT_LM_STUDIO_BASE)
    route_test.add_argument("--model", default=DEFAULT_LMSTUDIO_CHAT_MODEL)
    route_test.add_argument("--max-tokens", type=int, default=2200)
    route_test.set_defaults(func=command_lmstudio_route_test)

    migrate = subparsers.add_parser("migrate")
    migrate_sub = migrate.add_subparsers(dest="migrate_command", required=True)
    inventory = migrate_sub.add_parser("memory-to-openviking")
    inventory.add_argument("--write", action="store_true")
    inventory.set_defaults(func=command_migrate_inventory)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
