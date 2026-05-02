#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional, Union


ROOT = Path.cwd()
MEMORY_ROOT = ROOT / ".agents" / "memory"
RAG_DIR = MEMORY_ROOT / "rag"
DB_PATH = RAG_DIR / "index.sqlite"
TMP_DB_PATH = RAG_DIR / "index.tmp.sqlite"
MANIFEST_PATH = RAG_DIR / "manifest.json"
RAG_CONFIG_PATH = RAG_DIR / "config.json"
LEGACY_EMBEDDING_CONFIG_PATH = RAG_DIR / "embedding.json"
LOCK_DIR = RAG_DIR / "write.lock"
TOOL_PATH = RAG_DIR / "agent-memory.py"

DEFAULT_RUNTIME_CONFIG = {
    "embedding_batch_size": 16,
    "embedding_timeout_seconds": 0,
    "embedding_minimum_dimensions": 64,
}

REQUIRED_FILES = [
    MEMORY_ROOT / "SCHEMA.md",
    MEMORY_ROOT / "INDEX.md",
]

REQUIRED_DIRS = [
    MEMORY_ROOT / "templates",
    MEMORY_ROOT / "memory" / "decisions",
    MEMORY_ROOT / "memory" / "facts",
    MEMORY_ROOT / "memory" / "preferences",
    MEMORY_ROOT / "memory" / "gotchas",
    MEMORY_ROOT / "memory" / "events",
    MEMORY_ROOT / "documentations" / "sources",
    MEMORY_ROOT / "documentations" / "procedures",
    MEMORY_ROOT / "documentations" / "references",
    RAG_DIR,
]

REQUIRED_FRONTMATTER = ["id", "type", "title", "status", "created", "updated", "tags", "summary"]

TYPE_DIRECTORIES = {
    "decision": MEMORY_ROOT / "memory" / "decisions",
    "fact": MEMORY_ROOT / "memory" / "facts",
    "preference": MEMORY_ROOT / "memory" / "preferences",
    "gotcha": MEMORY_ROOT / "memory" / "gotchas",
    "event": MEMORY_ROOT / "memory" / "events",
    "source": MEMORY_ROOT / "documentations" / "sources",
    "procedure": MEMORY_ROOT / "documentations" / "procedures",
}

INDEX_SECTIONS = {
    "decision": "Decisions",
    "fact": "Facts",
    "preference": "Preferences",
    "gotcha": "Gotchas",
    "event": "Events",
    "source": "Documentation Sources",
    "procedure": "Procedures",
}

DEFAULT_STATUSES = {
    "decision": "accepted",
    "event": "recorded",
}


class AgentBasicsError(RuntimeError):
    pass


def relpath(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "entry"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if value and not value.endswith("\n\n"):
        value = value.rstrip("\n") + "\n\n"
    path.write_text(value, encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]
    metadata: dict[str, Any] = {}
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            metadata[key] = [item.strip().strip("'\"") for item in inner.split(",") if item.strip()]
        else:
            metadata[key] = value.strip("'\"")
    return metadata, body


def render_tags(tags: Union[str, list[str]]) -> str:
    if isinstance(tags, str):
        values = [item.strip() for item in tags.split(",") if item.strip()]
    else:
        values = tags
    return "[" + ", ".join(values) + "]"


def sentence_summary(content: str) -> str:
    flattened = re.sub(r"\s+", " ", content).strip()
    if not flattened:
        return "Recorded agent-basics memory entry."
    match = re.search(r"(.{1,180}?)([.!?](?:\s|$)|$)", flattened)
    return (match.group(1) if match else flattened[:180]).strip()


def iter_entry_files() -> list[Path]:
    files: list[Path] = []
    for root in [MEMORY_ROOT / "memory", MEMORY_ROOT / "documentations"]:
        if root.exists():
            files.extend(path for path in root.rglob("*.md") if path.is_file())
    return sorted(files)


def iter_indexed_files() -> list[Path]:
    files: list[Path] = []
    files.extend(path for path in REQUIRED_FILES if path.exists())
    files.extend(iter_entry_files())
    return sorted(dict.fromkeys(files))


def validate_layout() -> list[str]:
    errors: list[str] = []
    for directory in REQUIRED_DIRS:
        if not directory.is_dir():
            errors.append(f"missing directory: {relpath(directory)}")
    for file_path in REQUIRED_FILES:
        if not file_path.is_file():
            errors.append(f"missing file: {relpath(file_path)}")
    return errors


def validate_entries() -> list[str]:
    errors: list[str] = []
    seen_ids: dict[str, Path] = {}
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    for path in iter_entry_files():
        metadata, _ = parse_frontmatter(read_text(path))
        display_path = relpath(path)
        if not metadata:
            errors.append(f"{display_path}: missing YAML front matter")
            continue

        for key in REQUIRED_FRONTMATTER:
            value = metadata.get(key)
            if key not in metadata or value == "" or value == []:
                errors.append(f"{display_path}: missing required front matter key `{key}`")

        entry_id = str(metadata.get("id", ""))
        if entry_id:
            if entry_id in seen_ids:
                errors.append(f"{display_path}: duplicate id `{entry_id}` also used by {relpath(seen_ids[entry_id])}")
            seen_ids[entry_id] = path

        entry_type = str(metadata.get("type", ""))
        if entry_type and entry_type not in TYPE_DIRECTORIES:
            errors.append(f"{display_path}: unsupported type `{entry_type}`")
        elif entry_type:
            expected_root = TYPE_DIRECTORIES[entry_type].resolve()
            if expected_root not in path.resolve().parents:
                errors.append(f"{display_path}: type `{entry_type}` belongs under {relpath(expected_root)}")

        for key in ["created", "updated"]:
            value = str(metadata.get(key, ""))
            if value and not date_pattern.match(value):
                errors.append(f"{display_path}: `{key}` must use YYYY-MM-DD")

        tags = metadata.get("tags")
        if tags is not None and not isinstance(tags, list):
            errors.append(f"{display_path}: `tags` must be a YAML-style list such as [memory, rag]")

    return errors


def validate_or_raise() -> None:
    errors = validate_layout() + validate_entries()
    if errors:
        raise AgentBasicsError("\n".join(errors))


def normalize_rag_config(config: dict[str, Any], source_path: Path) -> dict[str, Any]:
    if "embedding" in config:
        embedding = config.get("embedding")
        runtime = config.get("runtime", {})
    else:
        embedding = config
        runtime = {}

    if not isinstance(embedding, dict):
        raise AgentBasicsError(f"{relpath(source_path)} missing `embedding` object")
    if not isinstance(runtime, dict):
        raise AgentBasicsError(f"{relpath(source_path)} `runtime` must be an object")

    for key in ["base_url", "model", "dimensions"]:
        if key not in embedding:
            raise AgentBasicsError(f"{relpath(source_path)} missing embedding `{key}`")

    normalized_runtime = dict(DEFAULT_RUNTIME_CONFIG)
    normalized_runtime.update(runtime)
    return {
        "version": int(config.get("version", 1)),
        "embedding": embedding,
        "runtime": normalized_runtime,
    }


def load_rag_config(required: bool = True) -> dict[str, Any]:
    config = read_json(RAG_CONFIG_PATH, None)
    if config is not None:
        return normalize_rag_config(config, RAG_CONFIG_PATH)

    legacy_config = read_json(LEGACY_EMBEDDING_CONFIG_PATH, None)
    if legacy_config is not None:
        return normalize_rag_config({"version": 1, "embedding": legacy_config, "runtime": {}}, LEGACY_EMBEDDING_CONFIG_PATH)

    if required:
        raise AgentBasicsError(f"missing RAG config: {relpath(RAG_CONFIG_PATH)}")
    return {}


def load_embedding_config(required: bool = True) -> dict[str, Any]:
    config = load_rag_config(required=required)
    return config.get("embedding", {}) if config else {}


def load_runtime_config() -> dict[str, Any]:
    config = load_rag_config(required=False)
    if not config:
        return dict(DEFAULT_RUNTIME_CONFIG)
    return dict(config["runtime"])


def embedding_timeout() -> Optional[float]:
    runtime = load_runtime_config()
    raw = os.environ.get("AGENT_BASICS_EMBEDDING_TIMEOUT", str(runtime["embedding_timeout_seconds"]))
    if raw in {"", "0", "none", "None"}:
        return None
    return float(raw)


def embedding_batch_size() -> int:
    runtime = load_runtime_config()
    return int(os.environ.get("AGENT_BASICS_EMBEDDING_BATCH_SIZE", str(runtime["embedding_batch_size"])))


def embed_texts(texts: list[str], config: dict[str, Any]) -> list[list[float]]:
    if not texts:
        return []

    base_url = str(config["base_url"]).rstrip("/")
    model = str(config["model"])
    api_key_env = str(config.get("api_key_env", ""))
    api_key = os.environ.get(api_key_env, "") if api_key_env else ""
    payload = {
        "model": model,
        "input": texts,
    }
    request = urllib.request.Request(
        f"{base_url}/embeddings",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if api_key:
        request.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(request, timeout=embedding_timeout()) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AgentBasicsError(f"embedding API returned HTTP {exc.code}: {body}") from exc
    except Exception as exc:
        raise AgentBasicsError(f"embedding API request failed: {exc}") from exc

    data = response_payload.get("data")
    if not isinstance(data, list) or len(data) != len(texts):
        raise AgentBasicsError("embedding API response did not return one vector per input")

    vectors: list[list[float]] = []
    for index, item in enumerate(data):
        vector = item.get("embedding") if isinstance(item, dict) else None
        if not isinstance(vector, list) or not vector:
            raise AgentBasicsError(f"embedding API returned invalid vector at index {index}")
        if not all(isinstance(value, (int, float)) and math.isfinite(float(value)) for value in vector):
            raise AgentBasicsError(f"embedding API returned non-finite vector values at index {index}")
        vectors.append([float(value) for value in vector])
    return vectors


@contextlib.contextmanager
def memory_lock(wait: bool = True):
    RAG_DIR.mkdir(parents=True, exist_ok=True)
    last_notice = 0.0
    acquired = False
    while not acquired:
        try:
            LOCK_DIR.mkdir()
            write_json(
                LOCK_DIR / "owner.json",
                {
                    "pid": os.getpid(),
                    "started_at": utc_now(),
                    "command": " ".join(sys.argv),
                },
            )
            acquired = True
        except FileExistsError:
            if not wait:
                raise AgentBasicsError(f"memory lock is held: {relpath(LOCK_DIR)}")
            now = time.monotonic()
            if now - last_notice >= 10:
                print(f"Waiting for memory lock: {relpath(LOCK_DIR)}", file=sys.stderr)
                last_notice = now
            time.sleep(1)
    try:
        yield
    finally:
        with contextlib.suppress(FileNotFoundError):
            for child in LOCK_DIR.iterdir():
                child.unlink()
            LOCK_DIR.rmdir()


def headings_and_chunks(path: Path, text: str, max_chars: int = 2400) -> list[dict[str, Any]]:
    metadata, body = parse_frontmatter(text)
    title = str(metadata.get("title") or path.stem.replace("-", " ").title())
    prefix_parts = [
        f"path: {relpath(path)}",
        f"title: {title}",
    ]
    for key in ["type", "status", "summary"]:
        if metadata.get(key):
            prefix_parts.append(f"{key}: {metadata[key]}")
    if metadata.get("tags"):
        prefix_parts.append("tags: " + ", ".join(str(item) for item in metadata["tags"]))
    prefix = "\n".join(prefix_parts) + "\n\n"

    sections: list[tuple[str, list[str]]] = []
    current_heading = title
    current_lines: list[str] = []
    for line in body.splitlines():
        if line.startswith("#"):
            if current_lines:
                sections.append((current_heading, current_lines))
            current_heading = line.lstrip("#").strip() or title
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_heading, current_lines))
    if not sections:
        sections = [(title, [body])]

    chunks: list[dict[str, Any]] = []
    for heading, lines in sections:
        section_text = prefix + "\n".join(lines).strip()
        if len(section_text) <= max_chars:
            chunks.append({"heading": heading, "content": section_text})
            continue
        paragraphs = re.split(r"\n\s*\n", section_text)
        buffer: list[str] = []
        current_len = 0
        for paragraph in paragraphs:
            paragraph_len = len(paragraph)
            if buffer and current_len + paragraph_len + 2 > max_chars:
                chunks.append({"heading": heading, "content": "\n\n".join(buffer).strip()})
                buffer = []
                current_len = 0
            buffer.append(paragraph)
            current_len += paragraph_len + 2
        if buffer:
            chunks.append({"heading": heading, "content": "\n\n".join(buffer).strip()})
    return chunks


def source_hashes() -> dict[str, str]:
    return {relpath(path): sha256_text(read_text(path)) for path in iter_indexed_files()}


def config_hash() -> str:
    config = load_rag_config(required=False)
    embedding = config.get("embedding", {}) if config else {}
    safe_config = {key: embedding.get(key) for key in ["provider", "base_url", "model", "dimensions", "api_key_env"]}
    return sha256_text(json.dumps(safe_config, sort_keys=True))


def build_chunks() -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for path in iter_indexed_files():
        text = read_text(path)
        metadata, _ = parse_frontmatter(text)
        digest = sha256_text(text)
        for index, chunk in enumerate(headings_and_chunks(path, text)):
            chunk_id = sha256_text(f"{relpath(path)}:{index}:{digest}")
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "path": relpath(path),
                    "heading": chunk["heading"],
                    "chunk_index": index,
                    "content": chunk["content"],
                    "metadata": metadata,
                    "source_hash": digest,
                }
            )
    return chunks


def create_index(chunks: list[dict[str, Any]], vectors: list[list[float]]) -> None:
    if TMP_DB_PATH.exists():
        TMP_DB_PATH.unlink()
    connection = sqlite3.connect(TMP_DB_PATH)
    try:
        connection.execute("PRAGMA journal_mode=OFF")
        connection.execute(
            """
            CREATE TABLE chunks (
                rowid INTEGER PRIMARY KEY,
                chunk_id TEXT NOT NULL UNIQUE,
                path TEXT NOT NULL,
                heading TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                source_hash TEXT NOT NULL,
                vector_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE VIRTUAL TABLE chunks_fts USING fts5(chunk_id UNINDEXED, path, heading, content)"
        )
        if len(chunks) != len(vectors):
            raise AgentBasicsError("embedding count did not match chunk count")
        for chunk, vector in zip(chunks, vectors):
            connection.execute(
                """
                INSERT INTO chunks (
                    chunk_id, path, heading, chunk_index, content, metadata_json, source_hash, vector_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk["chunk_id"],
                    chunk["path"],
                    chunk["heading"],
                    chunk["chunk_index"],
                    chunk["content"],
                    json.dumps(chunk["metadata"], sort_keys=True),
                    chunk["source_hash"],
                    json.dumps(vector),
                ),
            )
            connection.execute(
                "INSERT INTO chunks_fts (chunk_id, path, heading, content) VALUES (?, ?, ?, ?)",
                (chunk["chunk_id"], chunk["path"], chunk["heading"], chunk["content"]),
            )
        connection.commit()
    finally:
        connection.close()

    if DB_PATH.exists():
        DB_PATH.unlink()
    TMP_DB_PATH.replace(DB_PATH)


def rebuild_index(assume_locked: bool = False) -> None:
    def work() -> None:
        validate_or_raise()
        config = load_embedding_config(required=True)
        chunks = build_chunks()
        vectors: list[list[float]] = []
        batch_size = embedding_batch_size()
        for offset in range(0, len(chunks), batch_size):
            batch = chunks[offset : offset + batch_size]
            vectors.extend(embed_texts([chunk["content"] for chunk in batch], config))
        create_index(chunks, vectors)
        write_json(
            MANIFEST_PATH,
            {
                "updated": utc_now(),
                "chunk_count": len(chunks),
                "source_hashes": source_hashes(),
                "embedding_config_hash": config_hash(),
            },
        )
        print(f"Rebuilt memory index: {relpath(DB_PATH)} ({len(chunks)} chunks)")

    if assume_locked:
        work()
    else:
        with memory_lock():
            work()


def index_is_stale() -> bool:
    manifest = read_json(MANIFEST_PATH, None)
    if not DB_PATH.exists() or not isinstance(manifest, dict):
        return True
    return manifest.get("source_hashes") != source_hashes() or manifest.get("embedding_config_hash") != config_hash()


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    length = min(len(a), len(b))
    dot = sum(a[index] * b[index] for index in range(length))
    norm_a = math.sqrt(sum(a[index] * a[index] for index in range(length)))
    norm_b = math.sqrt(sum(b[index] * b[index] for index in range(length)))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


def fts_query(query: str) -> str:
    terms = [term for term in re.findall(r"[A-Za-z0-9_./:-]+", query) if len(term) > 1]
    return " OR ".join(f'"{term}"' for term in terms[:10])


def search_index(query: str, limit: int, json_output: bool) -> None:
    if index_is_stale():
        raise AgentBasicsError("memory index is missing or stale; run `.agents/memory/rag/agent-memory.py rebuild`")

    config = load_embedding_config(required=True)
    query_vector = embed_texts([query], config)[0]
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            "SELECT chunk_id, path, heading, content, metadata_json, vector_json FROM chunks"
        ).fetchall()
        fts_scores: dict[str, float] = {}
        query_expression = fts_query(query)
        if query_expression:
            try:
                fts_rows = connection.execute(
                    "SELECT chunk_id, bm25(chunks_fts) AS rank FROM chunks_fts WHERE chunks_fts MATCH ? LIMIT 50",
                    (query_expression,),
                ).fetchall()
                for rank, row in enumerate(fts_rows):
                    fts_scores[str(row["chunk_id"])] = 1.0 / (rank + 1)
            except sqlite3.OperationalError:
                fts_scores = {}
    finally:
        connection.close()

    results: list[dict[str, Any]] = []
    for row in rows:
        vector = json.loads(row["vector_json"])
        vector_score = cosine(query_vector, vector)
        keyword_score = fts_scores.get(str(row["chunk_id"]), 0.0)
        score = (0.78 * vector_score) + (0.22 * keyword_score)
        results.append(
            {
                "score": score,
                "vector_score": vector_score,
                "keyword_score": keyword_score,
                "path": row["path"],
                "heading": row["heading"],
                "content": row["content"],
                "metadata": json.loads(row["metadata_json"]),
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    selected = results[:limit]
    if json_output:
        print(json.dumps(selected, indent=2, sort_keys=True))
        return

    for item in selected:
        snippet = re.sub(r"\s+", " ", item["content"]).strip()[:360]
        print(f"- {item['path']} :: {item['heading']} (score {item['score']:.3f})")
        print(f"  {snippet}")


def update_index_file(entry_type: str, title: str, path: Path) -> None:
    section = INDEX_SECTIONS[entry_type]
    link = f"- [{title}]({path.relative_to(MEMORY_ROOT).as_posix()})"
    index_path = MEMORY_ROOT / "INDEX.md"
    text = read_text(index_path)
    if link in text:
        return
    heading = f"## {section}"
    position = text.find(heading)
    if position == -1:
        write_text(index_path, text.rstrip() + f"\n\n{heading}\n\n{link}\n")
        return
    next_heading = text.find("\n## ", position + len(heading))
    section_end = len(text) if next_heading == -1 else next_heading
    before = text[:section_end].rstrip()
    after = text[section_end:]
    if "- None yet." in before[position:]:
        before = before[:position] + before[position:].replace("- None yet.", link, 1)
    else:
        before = before + "\n" + link
    write_text(index_path, before + "\n" + after.lstrip("\n"))


def render_entry(entry_type: str, title: str, summary: str, tags: str, status: str, content: str, source_url: str) -> str:
    current_date = today()
    entry_id = f"{entry_type}-{current_date.replace('-', '')}-{slugify(title)}"
    frontmatter = [
        "---",
        f"id: {entry_id}",
        f"type: {entry_type}",
        f"title: {title}",
        f"status: {status}",
        f"created: {current_date}",
        f"updated: {current_date}",
        f"tags: {render_tags(tags)}",
        f"summary: {summary}",
    ]
    if source_url:
        frontmatter.append(f"url: {source_url}")
    if entry_type == "event":
        frontmatter.append(f"event_date: {current_date}")
    frontmatter.append("---")

    section = {
        "decision": "## Decision",
        "fact": "## Fact",
        "preference": "## Preference",
        "gotcha": "## Problem",
        "event": "## Event",
        "source": "## Notes",
        "procedure": "## Steps",
    }[entry_type]

    lines = frontmatter + ["", f"# {title}", "", section, "", content.strip() or summary, "", "## Related", "", "- None."]
    return "\n".join(lines) + "\n"


def record_entry(args: argparse.Namespace) -> None:
    entry_type = args.type
    title = args.title.strip()
    if not title:
        raise AgentBasicsError("title is required")
    content = args.content
    if content is None and not sys.stdin.isatty():
        content = sys.stdin.read()
    content = content or ""
    summary = args.summary or sentence_summary(content or title)
    status = args.status or DEFAULT_STATUSES.get(entry_type, "active")
    directory = TYPE_DIRECTORIES[entry_type]
    target = directory / f"{today().replace('-', '')}-{slugify(title)}.md"
    suffix = 2
    while target.exists():
        target = directory / f"{today().replace('-', '')}-{slugify(title)}-{suffix}.md"
        suffix += 1

    with memory_lock():
        write_text(target, render_entry(entry_type, title, summary, args.tags, status, content, args.url or ""))
        update_index_file(entry_type, title, target)
        print(f"Recorded {entry_type}: {relpath(target)}")
        if not args.no_rebuild:
            rebuild_index(assume_locked=True)


def install_git_hooks() -> None:
    git_dir = subprocess.check_output(["git", "rev-parse", "--git-dir"], text=True).strip()
    hooks_dir = (ROOT / git_dir / "hooks").resolve()
    hooks_dir.mkdir(parents=True, exist_ok=True)
    backup_dir = MEMORY_ROOT / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    hook_names = ["pre-commit", "post-commit", "post-merge", "post-checkout"]
    for hook_name in hook_names:
        hook_path = hooks_dir / hook_name
        backup_command = ""
        if hook_path.exists() and "agent-basics memory hook" not in hook_path.read_text(encoding="utf-8", errors="ignore"):
            backup_path = backup_dir / f"git-hook-{hook_name}.{int(time.time())}.bak"
            shutil.copy2(hook_path, backup_path)
            backup_command = f'\n"{backup_path}" "$@"\n'
            print(f"Backed up existing git hook: {relpath(backup_path)}")
        hook_path.write_text(
            f"""#!/usr/bin/env bash
set -euo pipefail
# agent-basics memory hook
ROOT="$(git rev-parse --show-toplevel)"
{backup_command}
exec "$ROOT/.agents/memory/rag/agent-memory.py" hook {hook_name} "$@"
""",
            encoding="utf-8",
        )
        hook_path.chmod(0o755)
        print(f"Installed git hook: {hook_name}")


def changed_memory_files_for_head() -> list[str]:
    try:
        output = subprocess.check_output(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD", "--", ".agents/memory"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return []
    return [line for line in output.splitlines() if line.strip()]


def staged_memory_files() -> list[str]:
    try:
        output = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only", "--", ".agents/memory"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return []
    return [line for line in output.splitlines() if line.strip()]


def run_hook(name: str) -> None:
    if name == "pre-commit":
        if LOCK_DIR.exists():
            with memory_lock():
                pass
        if staged_memory_files():
            validate_or_raise()
            print("agent-basics memory validation passed")
        return

    if name in {"post-commit", "post-merge", "post-checkout"}:
        should_check = name != "post-commit" or bool(changed_memory_files_for_head())
        if should_check and index_is_stale():
            try:
                rebuild_index()
            except AgentBasicsError as exc:
                print(f"agent-basics memory index update failed: {exc}", file=sys.stderr)
        return

    raise AgentBasicsError(f"unknown hook: {name}")


def command_validate(_: argparse.Namespace) -> None:
    validate_or_raise()
    print("Memory layout and entries are valid")


def command_rebuild(_: argparse.Namespace) -> None:
    rebuild_index()


def command_search(args: argparse.Namespace) -> None:
    search_index(args.query, args.limit, args.json)


def command_doctor(args: argparse.Namespace) -> None:
    errors = validate_layout() + validate_entries()
    stale = index_is_stale()
    rag_config = load_rag_config(required=False)
    config = rag_config.get("embedding", {}) if rag_config else {}
    runtime = rag_config.get("runtime", dict(DEFAULT_RUNTIME_CONFIG)) if rag_config else dict(DEFAULT_RUNTIME_CONFIG)
    status = {
        "layout_valid": not errors,
        "errors": errors,
        "config_path": relpath(RAG_CONFIG_PATH if RAG_CONFIG_PATH.exists() else LEGACY_EMBEDDING_CONFIG_PATH),
        "runtime": runtime,
        "embedding_config": bool(config),
        "index_exists": DB_PATH.exists(),
        "index_stale": stale,
        "manifest_exists": MANIFEST_PATH.exists(),
    }
    if args.online and config:
        try:
            vector = embed_texts(["agent-basics doctor"], config)[0]
            status["embedding_online"] = True
            status["embedding_dimensions"] = len(vector)
        except AgentBasicsError as exc:
            status["embedding_online"] = False
            status["embedding_error"] = str(exc)
    print(json.dumps(status, indent=2, sort_keys=True))
    if errors or not config or stale:
        raise SystemExit(1)


def command_record(args: argparse.Namespace) -> None:
    record_entry(args)


def command_install_hooks(_: argparse.Namespace) -> None:
    install_git_hooks()


def command_hook(args: argparse.Namespace) -> None:
    run_hook(args.name)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="agent-basics repo-local memory manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate memory layout and front matter")
    validate_parser.set_defaults(func=command_validate)

    rebuild_parser = subparsers.add_parser("rebuild", help="rebuild the generated memory RAG index")
    rebuild_parser.set_defaults(func=command_rebuild)

    search_parser = subparsers.add_parser("search", help="search memory with hybrid FTS and embeddings")
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=5)
    search_parser.add_argument("--json", action="store_true")
    search_parser.set_defaults(func=command_search)

    doctor_parser = subparsers.add_parser("doctor", help="report memory and index health")
    doctor_parser.add_argument("--online", action="store_true", help="call the embedding endpoint")
    doctor_parser.set_defaults(func=command_doctor)

    record_parser = subparsers.add_parser("record", help="record a structured memory entry")
    record_parser.add_argument("type", choices=sorted(TYPE_DIRECTORIES))
    record_parser.add_argument("title")
    record_parser.add_argument("--summary")
    record_parser.add_argument("--tags", default="")
    record_parser.add_argument("--status")
    record_parser.add_argument("--content")
    record_parser.add_argument("--url")
    record_parser.add_argument("--no-rebuild", action="store_true")
    record_parser.set_defaults(func=command_record)

    install_hooks_parser = subparsers.add_parser("install-hooks", help="install local git hooks")
    install_hooks_parser.set_defaults(func=command_install_hooks)

    hook_parser = subparsers.add_parser("hook", help=argparse.SUPPRESS)
    hook_parser.add_argument("name", choices=["pre-commit", "post-commit", "post-merge", "post-checkout"])
    hook_parser.set_defaults(func=command_hook)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
        return 0
    except AgentBasicsError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
