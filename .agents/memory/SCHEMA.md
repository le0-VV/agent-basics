# Memory Schema

`.agents/memory/` is the repo-owned source store for OpenViking-facing memory, resources, and skills.

OpenViking is the required runtime backend for durable memory, documentation resources, semantic organization, vector indexes, and retrieval. The files in this directory are project-owned source material that agents and setup tooling can inspect, adapt, ingest, and version-control. The OpenViking package, workspace, generated summaries, and vector database remain outside the repository unless the user explicitly configures otherwise.

## Directory Contract

```text
.agents/memory/
  SCHEMA.md
  INDEX.md
  ADAPTATION.md
  inbox/
  imports/
  memories/
    profile/
    preferences/
    entities/
    events/
    cases/
    patterns/
    tools/
    skills/
  resources/
    sources/
    procedures/
    references/
  skills/
  sessions/
```

## OpenViking Source Rules

- Every source entry should be markdown unless it is a resource file that needs to stay in its original format.
- Every entry must start with YAML front matter.
- Every entry must have `id`, `record_kind`, `ov_category`, `title`, `status`, `created`, `updated`, `tags`, and `summary`.
- Use Unix timestamp seconds for `created`, `updated`, and event timestamps.
- Keep one durable idea per file.
- Preserve source paths in `source_paths` when adapting legacy memory.
- Prefer short, searchable headings.
- Link related entries with relative paths.
- Record source URLs for external documentation.
- Do not store secrets.
- Use `requires_human_review: true` when a record is stale, transitional, conflicts with existing knowledge, or changes user intent.

## Record Kinds

- `memory`: durable user, project, system, tool, case, pattern, or skill knowledge for OpenViking memory.
- `resource`: documentation, references, source URLs, and other files that should be ingested as OpenViking resources.
- `skill`: reusable workflows that should be registered with OpenViking as skills.
- `ignore`: preserved migration material that should not be ingested.

## OpenViking Categories

- `profile`: stable user identity or attributes.
- `preferences`: what the user wants, prefers, dislikes, or habitually asks agents to do.
- `entities`: named things and stable attributes, including projects, systems, tools, repositories, people, organizations, and configured technologies.
- `events`: time-bound things that happened, are happening, or are planned.
- `cases`: specific problem, cause, solution, workaround, or outcome.
- `patterns`: reusable process or method for similar situations.
- `tools`: tool usage insights, parameters, success/failure patterns, and optimization.
- `skills`: reusable workflow or skill execution strategy.
- `none`: resources, ignored material, or records that should not become OpenViking memory.

## Adaptation Workflow

Agents adapting an existing project must follow `.agents/memory/ADAPTATION.md`.

High-level rules:

1. Copy existing memory/documentation material into `.agents/memory/imports/<unix-timestamp>-<source>/` or `.agents/openviking/legacy-memory/<unix-timestamp>/` before changing it.
2. Split durable material into one independently updatable idea per file under `memories/<ov_category>/`, `resources/`, or `skills/`.
3. Preserve provenance with `source_paths`.
4. Mark stale compatibility records with `requires_human_review: true` instead of silently importing them.
5. Ingest through `agent-basics ov ...` or the OpenViking-backed MCP gateway.
6. Verify with OpenViking retrieval before demoting legacy material.

Setup must not delete `.agents/memory/`. For fresh repositories, setup creates the OV source-store directories only. For older repositories, setup snapshots legacy compatibility directories such as `templates/`, `memory/`, `documentations/`, and `rag/` under `.agents/openviking/legacy-memory/<unix-timestamp>/` before agents adapt useful content into this schema.

## Transitional Compatibility

The older agent-basics compatibility mini-RAG used these legacy paths:

```text
.agents/memory/
  templates/
  memory/
  documentations/
  rag/
```

Those paths may still exist in target repositories as compatibility fallback. They are compatibility input, not the target source-store shape. This repository keeps the active source store OpenViking-native; the pre-migration compatibility snapshot is preserved at `.agents/openviking/legacy-memory/1777901050/`, and the fallback implementation source lives under `compat/memory-rag/`.

Compatibility writers must still respect `.agents/memory/rag/write.lock/` while the legacy mini-RAG is in use:

- Memory writers must wait while it exists.
- Indexers must create it before hashing, chunking, embedding, or replacing indexes.
- Indexers must remove it only after the generated index is consistent with source markdown.
- If the lock is stale because a process crashed, use a deliberate repair command rather than deleting it opportunistically.

## Compatibility Memory MCP

The OpenViking-backed `agent-basics mcp` gateway is the normal MCP surface. `compat/memory-rag/memory-mcp.py` is the source-checkout fallback implementation. Setup copies it to `.agents/memory/rag/memory-mcp.py` in target repositories only when `AGENT_BASICS_INSTALL_COMPAT_MEMORY=1` is used.

Supported tools:

- `memory_search`: run hybrid embedding and full-text retrieval.
- `memory_record`: create a structured memory entry and update `INDEX.md`; rebuild is deferred by default.
- `memory_doctor`: report layout, config, manifest, index, and optional embedding endpoint health.
- `memory_rebuild`: rebuild the generated SQLite RAG cache.
- `memory_validate`: check layout and entry front matter.

Agents should prefer OpenViking-backed MCP tools. Use compatibility MCP tools only when OpenViking is unavailable, then direct compatibility CLI calls.

## Compatibility Memory CLI

`agent-basics ov ...` is the OpenViking wrapper. `agent-basics memory` and `compat/memory-rag/agent-memory.py` are compatibility commands for hooks, setup, and fallback use. Explicit compatibility installs still place a repo-local copy at `.agents/memory/rag/agent-memory.py`.

Supported commands:

- `validate`: check layout and entry front matter.
- `rebuild`: rebuild the generated SQLite RAG cache.
- `search <query>`: run hybrid embedding and full-text retrieval.
- `record <type> <title>`: create a structured memory entry, update `INDEX.md`, and rebuild the index unless `--no-rebuild` is passed.
- `doctor`: report layout, embedding, and index health.
- `install-hooks`: install local git hooks that validate memory before commit and warn when the generated index is stale. Set `AGENT_BASICS_HOOK_AUTO_REBUILD=1` only when hook-triggered embedding calls are acceptable.

Generated files such as `index.sqlite` and `manifest.json` are rebuildable cache state and should not be committed.

## Compatibility RAG Configuration

`.agents/memory/rag/config.json` records the active compatibility embedding provider and durable mini-RAG runtime settings. Long-term OpenViking provider settings should move to `.agents/config.toml` and `.agents/openviking/` config.

The `embedding` object stores:

- `provider`
- `base_url`
- `model`
- `dimensions`
- `api_key_env`

Repo-local HuggingFace mode additionally stores these fields in `embedding`:

- `service_dir`
- `start_command`
- `cache_dir`

The `runtime` object stores:

- `embedding_timeout_seconds`
- `embedding_batch_size`
- `embedding_minimum_dimensions`
- `hook_auto_rebuild`

The API key value must stay in the environment and must not be committed.
