#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_LM_STUDIO_BASE = "http://127.0.0.1:1234"
DEFAULT_CHAT_MODEL = "google/gemma-4-e2b"
DEFAULT_EMBEDDING_MODEL = "text-embedding-embeddinggemma-300m-qat"
DEFAULT_OV_HOME = Path.home() / ".openviking"
DEFAULT_OV_BIN = DEFAULT_OV_HOME / "venv" / "bin" / "ov"
DEFAULT_OV_CONFIG = DEFAULT_OV_HOME / "ov.conf"
DEFAULT_OV_SERVER = DEFAULT_OV_HOME / "venv" / "bin" / "openviking-server"
GEMMA_LLM_KEYS = {"google/gemma-4-e2b", "google/gemma-4-e4b"}

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

Source records and URLs are not memories. Mark them as record_kind "resource" unless the item also contains durable memory.

Tie-breakers:
- Prefer preferences over entities when the text says the user wants/prefers/dislikes something.
- Prefer entities over preferences when the text describes what a project/system/tool is or how it is configured.
- Prefer events for accepted/rejected decisions, milestones, current work, planned work, or dated facts.
- Prefer cases for concrete failures and fixes.
- Prefer patterns for repeatable instructions.
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


def load_json_file(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        return {"_error": str(exc)}


def command_ov_doctor(args: argparse.Namespace) -> int:
    repo = repo_root_from_args(args)
    ov_bin = find_ov_bin()
    ov_config = Path(os.environ.get("AGENT_BASICS_OV_CONFIG", str(DEFAULT_OV_CONFIG))).expanduser()
    config = load_json_file(ov_config)
    payload: dict[str, Any] = {
        "ok": True,
        "repo": str(repo),
        "openviking": {
            "home": str(DEFAULT_OV_HOME),
            "bin": str(ov_bin) if ov_bin else None,
            "bin_exists": bool(ov_bin and ov_bin.exists()),
            "config_path": str(ov_config),
            "config_exists": ov_config.exists(),
            "config": config,
            "install_scope": "user" if ov_bin and str(ov_bin).startswith(str(DEFAULT_OV_HOME)) else "path",
            "repo_local_install_present": (repo / ".agents" / "openviking" / "venv").exists(),
        },
    }
    payload["openviking"]["version"] = run_command([str(ov_bin), "version"]) if ov_bin else None
    if args.online and ov_bin:
        payload["openviking"]["health"] = run_command([str(ov_bin), "health"], timeout=None)
        payload["openviking"]["status"] = run_command([str(ov_bin), "status", "-o", "json"], timeout=None)
    if args.providers:
        payload["lmstudio"] = lmstudio_status_payload(args.base_url, timeout=args.timeout)

    if not ov_bin:
        payload["ok"] = False
        payload["openviking"]["recommendation"] = "Run `agent-basics ov install-system` or install OpenViking under ~/.openviking."
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
    if path.exists() and not args.force:
        print_json({"ok": False, "error": f"{path} exists; pass --force to replace it"})
        return 1
    payload = {
        "storage": {"workspace": str(Path(args.home).expanduser() / "workspace")},
        "log": {"level": "INFO", "output": "stdout"},
        "embedding": {
            "dense": {
                "provider": "openai",
                "model": args.embedding_model,
                "api_key": "lm-studio",
                "api_base": f"{args.lmstudio_base.rstrip('/')}/v1",
                "dimension": args.embedding_dimension,
            },
            "max_concurrent": 1,
            "text_source": "content_only",
            "max_input_tokens": 2048,
        },
        "vlm": {
            "provider": "openai",
            "model": args.chat_model,
            "api_key": "lm-studio",
            "api_base": f"{args.lmstudio_base.rstrip('/')}/v1",
            "max_concurrent": 1,
            "timeout": 0,
        },
        "server": {"host": "127.0.0.1", "port": 1933},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print_json({"ok": True, "path": str(path), "config": payload})
    return 0


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
            "model_key": args.model,
            "identifier": args.model,
            "load_config": {
                "context_length": max_context,
                "gpu": {"ratio": "max"},
                "offload_kv_cache_to_gpu": True,
                "flash_attention": True,
                "use_fp16_for_kv_cache": False,
                "llama_k_cache_quantization_type": "q4_0",
                "llama_v_cache_quantization_type": "q4_0",
                "parallel": 1,
            },
            "echo_load_config": True,
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
    }


def command_lmstudio_plan(args: argparse.Namespace) -> int:
    print_json(lmstudio_plan_payload(args))
    return 0


def command_lmstudio_load(args: argparse.Namespace) -> int:
    plan = lmstudio_plan_payload(args)
    if not plan.get("ok"):
        print_json(plan)
        return 1
    loaded_gemma = plan["status"].get("loaded_gemma_llms", [])
    conflicts = [item for item in loaded_gemma if item.get("key") != args.model]
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
    for item in conflicts:
        http_json(args.base_url, "/api/v1/models/unload", {"instance_id": item["id"]}, timeout=args.timeout)
    if args.dry_run:
        print_json({"ok": True, "dry_run": True, "request": plan["load_request"]})
        return 0
    try:
        result = http_json(args.base_url, "/api/v1/models/load", plan["load_request"], timeout=None)
    except Exception as exc:
        print_json({"ok": False, "error": str(exc), "request": plan["load_request"]})
        return 1
    print_json({"ok": True, "request": plan["load_request"], "result": result})
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


def routing_cases() -> list[dict[str, Any]]:
    return [
        {
            "name": "harness_direction",
            "text": "The user wants agent-basics to be a thin harness layer over OpenViking. agent-basics owns setup, config, MCP, hooks, migration UX, and run state. OpenViking owns durable context storage, resources, summaries, vector indexes, and retrieval.",
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
            "instruction": "Route the candidate into OV-native memory categories or resource records.",
            "candidate": {"input_id": case["name"], "text": redact(case["text"])},
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
        if path.name in {"SCHEMA.md", "INDEX.md"} or "/templates/" in str(path):
            continue
        text = path.read_text(encoding="utf-8")
        meta, body = parse_front_matter(text)
        legacy_type = meta.get("type", "")
        category, reason, review = legacy_to_ov_category(path, legacy_type, text)
        record_kind = "resource" if category == "none" and "documentations/sources" in str(path) else "memory"
        if category == "none" and record_kind != "resource":
            record_kind = "ignore"
        stale = any(token in body.lower() for token in ["memoryhub", "repo-local mini-rag", "compatibility"])
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-basics-ov")
    parser.add_argument("--repo", help="Repository root for repo-aware operations")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ov = subparsers.add_parser("ov")
    ov_sub = ov.add_subparsers(dest="ov_command", required=True)
    doctor = ov_sub.add_parser("doctor")
    doctor.add_argument("--online", action="store_true")
    doctor.add_argument("--providers", action="store_true")
    doctor.add_argument("--base-url", default=DEFAULT_LM_STUDIO_BASE)
    doctor.add_argument("--timeout", type=float, default=5)
    doctor.set_defaults(func=command_ov_doctor)

    install = ov_sub.add_parser("install-system")
    install.add_argument("--home", default=str(DEFAULT_OV_HOME))
    install.add_argument("--python", default="3.12")
    install.add_argument("--package", default="openviking")
    install.add_argument("--force", action="store_true")
    install.set_defaults(func=command_ov_install_system)

    config = ov_sub.add_parser("write-default-config")
    config.add_argument("--config", default=str(DEFAULT_OV_CONFIG))
    config.add_argument("--home", default=str(DEFAULT_OV_HOME))
    config.add_argument("--lmstudio-base", default=DEFAULT_LM_STUDIO_BASE)
    config.add_argument("--chat-model", default=DEFAULT_CHAT_MODEL)
    config.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    config.add_argument("--embedding-dimension", type=int, default=768)
    config.add_argument("--force", action="store_true")
    config.set_defaults(func=command_ov_write_default_config)

    lm = subparsers.add_parser("lmstudio")
    lm_sub = lm.add_subparsers(dest="lmstudio_command", required=True)
    status = lm_sub.add_parser("status")
    status.add_argument("--base-url", default=DEFAULT_LM_STUDIO_BASE)
    status.add_argument("--timeout", type=float, default=5)
    status.set_defaults(func=command_lmstudio_status)

    hardware = lm_sub.add_parser("hardware")
    hardware.set_defaults(func=command_lmstudio_hardware)

    plan = lm_sub.add_parser("plan")
    plan.add_argument("--base-url", default=DEFAULT_LM_STUDIO_BASE)
    plan.add_argument("--model", default=DEFAULT_CHAT_MODEL)
    plan.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    plan.add_argument("--max-tokens", type=int, default=2200)
    plan.add_argument("--timeout", type=float, default=5)
    plan.set_defaults(func=command_lmstudio_plan)

    load = lm_sub.add_parser("load")
    load.add_argument("--base-url", default=DEFAULT_LM_STUDIO_BASE)
    load.add_argument("--model", default=DEFAULT_CHAT_MODEL)
    load.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    load.add_argument("--max-tokens", type=int, default=2200)
    load.add_argument("--timeout", type=float, default=5)
    load.add_argument("--dry-run", action="store_true")
    load.add_argument("--unload-conflicts", action="store_true")
    load.set_defaults(func=command_lmstudio_load)

    unload = lm_sub.add_parser("unload")
    unload.add_argument("identifier", nargs="?", default=DEFAULT_CHAT_MODEL)
    unload.add_argument("--base-url", default=DEFAULT_LM_STUDIO_BASE)
    unload.add_argument("--timeout", type=float, default=5)
    unload.add_argument("--all", action="store_true")
    unload.set_defaults(func=command_lmstudio_unload)

    route_test = lm_sub.add_parser("route-test")
    route_test.add_argument("--base-url", default=DEFAULT_LM_STUDIO_BASE)
    route_test.add_argument("--model", default=DEFAULT_CHAT_MODEL)
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
