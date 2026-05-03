#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SERVER_NAME = "agent-basics-memory"
SERVER_VERSION = "0.1.0"
SUPPORTED_PROTOCOL_VERSIONS = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]

SCRIPT_PATH = Path(__file__).resolve()
RAG_DIR = SCRIPT_PATH.parent
ROOT = SCRIPT_PATH.parents[3] if len(SCRIPT_PATH.parents) >= 4 else Path.cwd()
MEMORY_CLI = RAG_DIR / "agent-memory.py"

ERROR_PARSE = -32700
ERROR_INVALID_REQUEST = -32600
ERROR_METHOD_NOT_FOUND = -32601
ERROR_INVALID_PARAMS = -32602
ERROR_INTERNAL = -32603


TOOLS: list[dict[str, Any]] = [
    {
        "name": "memory_search",
        "title": "Search agent-basics memory",
        "description": "Search repo-local agent-basics memory with the generated hybrid RAG index.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "memory_record",
        "title": "Record agent-basics memory",
        "description": "Create a structured repo-local memory or documentation entry, update INDEX.md, and rebuild the RAG index.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["decision", "event", "fact", "gotcha", "preference", "procedure", "source"],
                },
                "title": {"type": "string"},
                "content": {"type": "string"},
                "summary": {"type": "string"},
                "tags": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}},
                    ],
                    "default": "",
                },
                "status": {"type": "string"},
                "url": {"type": "string"},
                "no_rebuild": {"type": "boolean", "default": False},
            },
            "required": ["type", "title", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "memory_doctor",
        "title": "Check agent-basics memory health",
        "description": "Report memory layout, config, manifest, index, and optional embedding endpoint health.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "online": {
                    "type": "boolean",
                    "default": False,
                    "description": "When true, call the configured embedding endpoint.",
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "memory_rebuild",
        "title": "Rebuild agent-basics memory index",
        "description": "Rebuild the generated SQLite RAG index from repo-local markdown memory.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "memory_validate",
        "title": "Validate agent-basics memory",
        "description": "Validate the repo-local memory layout and entry front matter.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


class McpError(Exception):
    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def protocol_version(params: dict[str, Any]) -> str:
    requested = str(params.get("protocolVersion", ""))
    if requested in SUPPORTED_PROTOCOL_VERSIONS:
        return requested
    return SUPPORTED_PROTOCOL_VERSIONS[0]


def json_response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def json_error(request_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
    if data is not None:
        payload["error"]["data"] = data
    return payload


def emit(message: dict[str, Any]) -> None:
    print(json.dumps(message, separators=(",", ":"), ensure_ascii=False), flush=True)


def tool_result(text: str, structured: dict[str, Any] | None = None, is_error: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "content": [{"type": "text", "text": text}],
        "isError": is_error,
    }
    if structured is not None:
        result["structuredContent"] = structured
    return result


def require_cli() -> None:
    if not MEMORY_CLI.is_file():
        raise McpError(ERROR_INTERNAL, f"missing memory CLI: {MEMORY_CLI}")


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    require_cli()
    return subprocess.run(
        [sys.executable, str(MEMORY_CLI), *args],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def parse_json_stdout(output: str) -> Any:
    if not output.strip():
        return None
    return json.loads(output)


def cli_tool_result(completed: subprocess.CompletedProcess[str], json_key: str | None = None) -> dict[str, Any]:
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    is_error = completed.returncode != 0
    text_parts = []
    if stdout:
        text_parts.append(stdout)
    if stderr:
        text_parts.append(stderr)
    text = "\n\n".join(text_parts) or ("Command failed" if is_error else "OK")

    structured: dict[str, Any] = {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    if json_key and stdout:
        try:
            structured[json_key] = parse_json_stdout(stdout)
        except json.JSONDecodeError:
            structured["json_parse_error"] = True

    return tool_result(text, structured, is_error)


def as_arguments(params: dict[str, Any]) -> dict[str, Any]:
    arguments = params.get("arguments", {})
    if arguments is None:
        return {}
    if not isinstance(arguments, dict):
        raise McpError(ERROR_INVALID_PARAMS, "tools/call arguments must be an object")
    return arguments


def require_string(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise McpError(ERROR_INVALID_PARAMS, f"`{key}` must be a non-empty string")
    return value


def optional_string(arguments: dict[str, Any], key: str) -> str | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise McpError(ERROR_INVALID_PARAMS, f"`{key}` must be a string")
    return value


def optional_bool(arguments: dict[str, Any], key: str, default: bool = False) -> bool:
    value = arguments.get(key, default)
    if not isinstance(value, bool):
        raise McpError(ERROR_INVALID_PARAMS, f"`{key}` must be a boolean")
    return value


def optional_limit(arguments: dict[str, Any]) -> int:
    value = arguments.get("limit", 5)
    if not isinstance(value, int) or isinstance(value, bool):
        raise McpError(ERROR_INVALID_PARAMS, "`limit` must be an integer")
    if value < 1 or value > 20:
        raise McpError(ERROR_INVALID_PARAMS, "`limit` must be between 1 and 20")
    return value


def tags_argument(arguments: dict[str, Any]) -> str:
    value = arguments.get("tags", "")
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return ", ".join(value)
    raise McpError(ERROR_INVALID_PARAMS, "`tags` must be a string or array of strings")


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "memory_search":
        query = require_string(arguments, "query")
        completed = run_cli(["search", query, "--limit", str(optional_limit(arguments)), "--json"])
        return cli_tool_result(completed, "results")

    if name == "memory_record":
        entry_type = require_string(arguments, "type")
        title = require_string(arguments, "title")
        content = require_string(arguments, "content")
        args = ["record", entry_type, title, "--content", content, "--tags", tags_argument(arguments)]
        for option in ["summary", "status", "url"]:
            value = optional_string(arguments, option)
            if value is not None:
                args.extend([f"--{option.replace('_', '-')}", value])
        if optional_bool(arguments, "no_rebuild", False):
            args.append("--no-rebuild")
        completed = run_cli(args)
        return cli_tool_result(completed)

    if name == "memory_doctor":
        args = ["doctor"]
        if optional_bool(arguments, "online", False):
            args.append("--online")
        completed = run_cli(args)
        return cli_tool_result(completed, "doctor")

    if name == "memory_rebuild":
        completed = run_cli(["rebuild"])
        return cli_tool_result(completed)

    if name == "memory_validate":
        completed = run_cli(["validate"])
        return cli_tool_result(completed)

    raise McpError(ERROR_METHOD_NOT_FOUND, f"unknown tool: {name}")


def handle_request(message: dict[str, Any]) -> dict[str, Any] | None:
    if message.get("jsonrpc") != "2.0":
        raise McpError(ERROR_INVALID_REQUEST, "jsonrpc must be 2.0")
    method = message.get("method")
    request_id = message.get("id")
    is_notification = "id" not in message

    if not isinstance(method, str):
        raise McpError(ERROR_INVALID_REQUEST, "method must be a string")

    if is_notification:
        return None

    params = message.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise McpError(ERROR_INVALID_PARAMS, "params must be an object")

    if method == "initialize":
        return json_response(
            request_id,
            {
                "protocolVersion": protocol_version(params),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {
                    "name": SERVER_NAME,
                    "title": "agent-basics Memory",
                    "version": SERVER_VERSION,
                },
                "instructions": "Use memory_search before answering requests that depend on prior project context. Use memory_record for durable decisions, facts, preferences, gotchas, events, sources, and procedures.",
            },
        )

    if method == "ping":
        return json_response(request_id, {})

    if method == "tools/list":
        return json_response(request_id, {"tools": TOOLS})

    if method == "tools/call":
        name = params.get("name")
        if not isinstance(name, str) or not name:
            raise McpError(ERROR_INVALID_PARAMS, "tools/call params.name must be a non-empty string")
        return json_response(request_id, call_tool(name, as_arguments(params)))

    raise McpError(ERROR_METHOD_NOT_FOUND, f"unknown method: {method}")


def handle_message(message: Any) -> list[dict[str, Any]]:
    if isinstance(message, list):
        responses: list[dict[str, Any]] = []
        for item in message:
            responses.extend(handle_message(item))
        return responses

    if not isinstance(message, dict):
        return [json_error(None, ERROR_INVALID_REQUEST, "JSON-RPC message must be an object")]

    try:
        response = handle_request(message)
        return [response] if response is not None else []
    except McpError as exc:
        return [json_error(message.get("id"), exc.code, exc.message, exc.data)]
    except Exception as exc:
        return [json_error(message.get("id"), ERROR_INTERNAL, "internal error", str(exc))]


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            emit(json_error(None, ERROR_PARSE, "parse error", str(exc)))
            continue

        for response in handle_message(message):
            emit(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
