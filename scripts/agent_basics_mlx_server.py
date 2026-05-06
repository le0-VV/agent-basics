#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gc
import json
import time
import uuid
from threading import Lock, Thread
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


DEFAULT_CHAT_MODEL = "mlx-community/gemma-4-e2b-it-4bit"
DEFAULT_EMBEDDING_MODEL = "mlx-community/embeddinggemma-300m-4bit"
PRELOAD_MODES = {"none", "chat", "embedding", "all"}
STARTUP_STRUCTURED_OUTPUT_CHECKS = {"none", "openviking-router"}

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
                    "action": {"type": "string", "enum": ["create", "append", "ignore", "needs_review"]},
                    "record_kind": {"type": "string", "enum": ["memory", "resource", "ignore"]},
                    "ov_category": {"type": "string", "enum": [*OV_MEMORY_CATEGORIES, "none"]},
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


def router_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "openviking_memory_routing",
            "strict": True,
            "schema": ROUTER_OUTPUT_SCHEMA,
        },
    }


ROUTER_ITEM_REQUIRED_FIELDS = set(ROUTER_OUTPUT_SCHEMA["properties"]["items"]["items"]["required"])


def preview_text(text: str, limit: int = 500) -> str:
    compact = " ".join(text.strip().split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}..."


def startup_router_prompt(response_format: dict[str, Any]) -> str:
    instruction = response_format_instruction(response_format)
    return (
        f"system: {ROUTER_SYSTEM_PROMPT}\n"
        f"system: {instruction}\n"
        "user: Route this candidate into the OpenViking router schema.\n"
        "Return exactly one item inside a top-level JSON object with the key items.\n\n"
        "Candidate:\n"
        "input_id: startup_check\n"
        "text: The user wants agent-basics MLX runtime to start at macOS login, preload the chat and "
        "embedding models, and use OpenViking router structured output when recording durable context."
    )


def validate_router_payload(payload: Any, *, require_items: bool) -> tuple[bool, str | None, int]:
    if not isinstance(payload, dict):
        return False, "top-level JSON is not an object", 0
    items = payload.get("items")
    if not isinstance(items, list):
        return False, "items is not an array", 0
    if require_items and not items:
        return False, "items is empty", 0
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            return False, f"items[{index}] is not an object", len(items)
        missing = sorted(ROUTER_ITEM_REQUIRED_FIELDS.difference(item))
        if missing:
            return False, f"items[{index}] missing required fields: {', '.join(missing)}", len(items)
        if item.get("record_kind") == "resource" and item.get("ov_category") != "none":
            return False, f"items[{index}] resource must use ov_category none", len(items)
        if item.get("record_kind") in {"memory", "resource"} and item.get("action") == "ignore":
            return False, f"items[{index}] non-ignored records cannot use action ignore", len(items)
    return True, None, len(items)


class ModelListItem(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "agent-basics"


def model_dict(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


class ChatMessage(BaseModel):
    role: str
    content: Any


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: float | None = 0
    max_tokens: int | None = 512
    stream: bool | None = False
    response_format: dict[str, Any] | None = None


class EmbeddingRequest(BaseModel):
    model: str
    input: str | list[str] | list[int] | list[list[int]]
    encoding_format: str | None = "float"


class RuntimeState:
    def __init__(self, chat_model: str, embedding_model: str, unload_idle_seconds: int) -> None:
        self.chat_model_id = chat_model
        self.embedding_model_id = embedding_model
        self.unload_idle_seconds = unload_idle_seconds
        self.lock = Lock()
        self.chat: tuple[Any, Any, Any, Any, Any] | None = None
        self.embedding: tuple[Any, Any, Any] | None = None
        self.last_used = time.time()
        self.startup: dict[str, Any] = {"preload": "not_started"}

    def touch(self) -> None:
        self.last_used = time.time()

    def clear_runtime_cache(self) -> None:
        gc.collect()
        try:
            import mlx.core as mx

            clear_cache = getattr(mx, "clear_cache", None)
            if clear_cache is None:
                clear_cache = mx.metal.clear_cache
            clear_cache()
        except Exception:
            pass

    def maybe_unload(self) -> None:
        if self.unload_idle_seconds <= 0:
            return
        if time.time() - self.last_used < self.unload_idle_seconds:
            return
        with self.lock:
            if time.time() - self.last_used < self.unload_idle_seconds:
                return
            self.chat = None
            self.embedding = None
            self.clear_runtime_cache()

    def load_chat(self) -> tuple[Any, Any, Any, Any, Any]:
        self.maybe_unload()
        with self.lock:
            self.touch()
            if self.chat is not None:
                return self.chat
            from mlx_vlm import generate, load
            from mlx_vlm.prompt_utils import apply_chat_template

            try:
                from mlx_vlm.utils import load_config
            except Exception:
                load_config = None

            model, processor = load(self.chat_model_id)
            config = getattr(model, "config", None)
            if config is None and load_config is not None:
                config = load_config(self.chat_model_id)
            self.chat = (model, processor, config, apply_chat_template, generate)
            return self.chat

    def load_embedding(self) -> tuple[Any, Any, Any]:
        self.maybe_unload()
        with self.lock:
            self.touch()
            if self.embedding is not None:
                return self.embedding
            try:
                from mlx_embeddings import load
            except Exception:
                from mlx_embeddings.utils import load
            import mlx.core as mx

            model, tokenizer = load(self.embedding_model_id)
            self.embedding = (model, tokenizer, mx)
            return self.embedding

    def preload(self, mode: str, structured_output_check: str) -> dict[str, Any]:
        started = time.time()
        payload: dict[str, Any] = {
            "preload": "running",
            "mode": mode,
            "structured_output_check": structured_output_check,
            "started": int(started),
            "chat_loaded": False,
            "embedding_loaded": False,
        }
        self.startup = payload
        structured_error: str | None = None
        try:
            if mode in {"chat", "all"} or structured_output_check != "none":
                model, processor, config, apply_chat_template, generate = self.load_chat()
                payload["chat_loaded"] = True
                if structured_output_check == "openviking-router":
                    response_format = router_response_format()
                    prompt = startup_router_prompt(response_format)
                    formatted_prompt = apply_template(processor, config, apply_chat_template, prompt, num_images=0)
                    text = generate_text(
                        generate,
                        model,
                        processor,
                        formatted_prompt,
                        [],
                        max_tokens=256,
                        temperature=0,
                    )
                    normalized = normalize_response_text(text, response_format)
                    parsed = json.loads(normalized)
                    ok, error, item_count = validate_router_payload(parsed, require_items=True)
                    payload["structured_output"] = {
                        "ok": ok,
                        "items": item_count,
                    }
                    if not ok:
                        structured_error = error or "router payload failed validation"
                        payload["structured_output"]["error"] = structured_error
                        payload["structured_output"]["raw_preview"] = preview_text(normalized)
                self.clear_runtime_cache()
            if mode in {"embedding", "all"}:
                self.load_embedding()
                payload["embedding_loaded"] = True
                self.clear_runtime_cache()
            if structured_error:
                raise RuntimeError(f"OpenViking router structured-output startup check failed: {structured_error}")
            payload["preload"] = "complete"
            payload["ok"] = True
        except Exception as exc:
            payload["preload"] = "failed"
            payload["ok"] = False
            payload["error"] = str(exc)
            payload["exception_type"] = type(exc).__name__
            self.clear_runtime_cache()
        payload["elapsed_seconds"] = round(time.time() - started, 3)
        payload["finished"] = int(time.time())
        self.startup = payload
        return payload


def normalize_text_input(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    raise HTTPException(status_code=400, detail="agent-basics MLX embeddings currently require string input")


def text_and_images_from_content(content: Any) -> tuple[str, list[str]]:
    if isinstance(content, str):
        return content, []
    if not isinstance(content, list):
        return str(content), []
    text_parts: list[str] = []
    images: list[str] = []
    for part in content:
        if isinstance(part, str):
            text_parts.append(part)
            continue
        if not isinstance(part, dict):
            text_parts.append(str(part))
            continue
        kind = part.get("type")
        if kind in {"text", "input_text"}:
            text_parts.append(str(part.get("text", "")))
        elif kind in {"image_url", "input_image"}:
            image_url = part.get("image_url")
            if isinstance(image_url, dict):
                url = image_url.get("url")
            else:
                url = image_url or part.get("url")
            if url:
                images.append(str(url))
    return "\n".join(item for item in text_parts if item), images


def prompt_from_messages(messages: list[ChatMessage]) -> tuple[str, list[str]]:
    lines: list[str] = []
    images: list[str] = []
    for message in messages:
        text, message_images = text_and_images_from_content(message.content)
        images.extend(message_images)
        if text.strip():
            lines.append(f"{message.role}: {text.strip()}")
    return "\n".join(lines).strip(), images


def response_format_instruction(response_format: dict[str, Any] | None) -> str | None:
    if not response_format:
        return None
    response_type = response_format.get("type")
    if response_type == "json_object":
        return "Return only one valid JSON object. Do not wrap it in markdown or code fences. Do not include prose."
    if response_type == "json_schema":
        schema = response_format.get("json_schema", response_format)
        schema_text = json.dumps(schema, ensure_ascii=True, separators=(",", ":"))
        return (
            "Return only valid JSON that conforms to this JSON schema. "
            "Do not wrap it in markdown or code fences. Do not include prose.\n"
            f"JSON schema: {schema_text}"
        )
    return None


def json_candidate_from_text(text: str) -> str | None:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        json.loads(stripped)
        return stripped
    except Exception:
        pass

    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            candidate = "\n".join(lines[1:-1]).strip()
            try:
                json.loads(candidate)
                return candidate
            except Exception:
                pass

    starts = [index for index, char in enumerate(stripped) if char in "[{"]
    for start in starts:
        opener = stripped[start]
        closer = "}" if opener == "{" else "]"
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(stripped)):
            char = stripped[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
                if depth == 0:
                    candidate = stripped[start : index + 1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except Exception:
                        break
    return None


def normalize_response_text(text: str, response_format: dict[str, Any] | None) -> str:
    if not response_format or response_format.get("type") not in {"json_object", "json_schema"}:
        return text
    return json_candidate_from_text(text) or text


def apply_template(
    processor: Any,
    config: Any,
    apply_chat_template: Any,
    prompt: str,
    *,
    num_images: int,
) -> str:
    try:
        return apply_chat_template(processor, config, prompt, num_images=num_images)
    except TypeError:
        try:
            return apply_chat_template(processor, config, prompt)
        except TypeError:
            return prompt


def generate_text(
    generate: Any,
    model: Any,
    processor: Any,
    prompt: str,
    images: list[str],
    *,
    max_tokens: int,
    temperature: float,
) -> str:
    kwargs = {"verbose": False, "max_tokens": max_tokens, "temperature": temperature}
    attempts = []
    if images:
        attempts.extend(
            [
                lambda: generate(model, processor, prompt, image=images, **kwargs),
                lambda: generate(model, processor, prompt, images, **kwargs),
            ]
        )
    attempts.extend(
        [
            lambda: generate(model, processor, prompt, **kwargs),
            lambda: generate(model, processor, prompt, [], **kwargs),
        ]
    )
    last_error: Exception | None = None
    for attempt in attempts:
        try:
            result = attempt()
        except Exception as exc:
            last_error = exc
            continue
        if isinstance(result, str):
            return result
        if hasattr(result, "text"):
            return str(result.text)
        return str(result)
    raise RuntimeError(str(last_error or "generation failed"))


def make_app(
    chat_model: str,
    embedding_model: str,
    unload_idle_seconds: int,
    preload_models: str,
    startup_structured_output_check: str,
) -> FastAPI:
    app = FastAPI(title="agent-basics MLX runtime")
    state = RuntimeState(chat_model, embedding_model, unload_idle_seconds)

    @app.on_event("startup")
    def startup_preload() -> None:
        if preload_models == "none" and startup_structured_output_check == "none":
            state.startup = {"preload": "disabled", "ok": True}
            return
        thread = Thread(
            target=state.preload,
            args=(preload_models, startup_structured_output_check),
            name="agent-basics-mlx-preload",
            daemon=True,
        )
        thread.start()

    @app.get("/health")
    def health() -> dict[str, Any]:
        state.maybe_unload()
        return {
            "ok": True,
            "provider": "agent-basics-mlx",
            "chat_model": chat_model,
            "embedding_model": embedding_model,
            "loaded": {
                "chat": state.chat is not None,
                "embedding": state.embedding is not None,
            },
            "unload_idle_seconds": unload_idle_seconds,
            "preload_models": preload_models,
            "startup_structured_output_check": startup_structured_output_check,
            "startup": state.startup,
        }

    @app.get("/v1/models")
    def models() -> dict[str, Any]:
        return {
            "object": "list",
            "data": [
                model_dict(ModelListItem(id=chat_model)),
                model_dict(ModelListItem(id=embedding_model)),
            ],
        }

    @app.post("/v1/embeddings")
    async def embeddings(request: EmbeddingRequest) -> dict[str, Any]:
        if request.model != embedding_model:
            raise HTTPException(status_code=404, detail=f"embedding model is not configured: {request.model}")
        texts = normalize_text_input(request.input)
        try:
            model, tokenizer, mx = state.load_embedding()
            encoded = tokenizer(texts, padding=True, truncation=True, return_tensors="mlx")
            output = model(encoded["input_ids"], encoded["attention_mask"])
            vectors = output.text_embeds
            mx.eval(vectors)
            data = vectors.tolist()
            state.touch()
        finally:
            state.clear_runtime_cache()
        return {
            "object": "list",
            "data": [
                {"object": "embedding", "index": index, "embedding": vector}
                for index, vector in enumerate(data)
            ],
            "model": embedding_model,
            "usage": {"prompt_tokens": 0, "total_tokens": 0},
        }

    @app.post("/v1/chat/completions")
    async def chat_completions(request: ChatCompletionRequest) -> JSONResponse:
        if request.stream:
            raise HTTPException(status_code=400, detail="streaming chat completions are not supported")
        if request.model != chat_model:
            raise HTTPException(status_code=404, detail=f"chat model is not configured: {request.model}")
        prompt, images = prompt_from_messages(request.messages)
        if not prompt:
            raise HTTPException(status_code=400, detail="messages must contain text")
        instruction = response_format_instruction(request.response_format)
        if instruction:
            prompt = f"system: {instruction}\n{prompt}"
        try:
            model, processor, config, apply_chat_template, generate = state.load_chat()
            formatted_prompt = apply_template(processor, config, apply_chat_template, prompt, num_images=len(images))
            try:
                text = generate_text(
                    generate,
                    model,
                    processor,
                    formatted_prompt,
                    images,
                    max_tokens=request.max_tokens or 512,
                    temperature=request.temperature or 0,
                )
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"MLX generation failed: {exc}") from exc
            text = normalize_response_text(text, request.response_format)
            state.touch()
        finally:
            state.clear_runtime_cache()
        created = int(time.time())
        return JSONResponse(
            {
                "id": f"chatcmpl-{uuid.uuid4().hex}",
                "object": "chat.completion",
                "created": created,
                "model": chat_model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": text},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }
        )

    return app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-basics-mlx-server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--chat-model", default=DEFAULT_CHAT_MODEL)
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--unload-idle-seconds", type=int, default=0)
    parser.add_argument("--preload-models", choices=sorted(PRELOAD_MODES), default="none")
    parser.add_argument(
        "--startup-structured-output-check",
        choices=sorted(STARTUP_STRUCTURED_OUTPUT_CHECKS),
        default="none",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    import uvicorn

    app = make_app(
        args.chat_model,
        args.embedding_model,
        args.unload_idle_seconds,
        args.preload_models,
        args.startup_structured_output_check,
    )
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
