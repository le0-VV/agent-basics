# agent-basics Operating Manual

This file contains agent-basics-specific operating rules. `Agents.md` contains the base agent contract.

## Memory And Documentation

- `.agents/memory/` is the only canonical memory and documentation source tree created by agent-basics.
- Treat markdown under `.agents/memory/` as source of truth. Treat RAG indexes, vector databases, model caches, and embedding API runtime files as generated retrieval support.
- Read `.agents/memory/SCHEMA.md` before creating or changing memory files.
- Use `.agents/memory/templates/` when recording new entries.
- Search `.agents/memory/INDEX.md`, then the project memory RAG, whenever the user refers to previous work, preferences, prior conversations, vague project context, or decisions not visible in the current chat.
- Use an MCP memory server first when one is configured. Until then, use `.agents/memory/rag/agent-memory.py search "<query>"`.
- Store durable memories under `.agents/memory/memory/`.
- Store documentation sources, procedures, and references under `.agents/memory/documentations/`.
- Record source URLs for external libraries, tools, APIs, frameworks, and standards under `.agents/memory/documentations/sources/`.
- Keep `.agents/memory/INDEX.md` updated whenever you add, move, or remove entries.
- Do not write memory or documentation files while `.agents/memory/rag/write.lock/` exists. Wait until the lock is released, then re-check the relevant source files before editing.

## RAG Configuration

- `.agents/memory/rag/config.json` is the durable RAG configuration file.
- Use `config.json` to find the embedding provider, base URL, model name, dimensions, runtime settings, and API key environment variable.
- Environment variables are setup inputs, secret pointers, or one-off overrides. Do not rely on them as the durable project configuration.
- Never commit raw embedding provider secret values. Store only the environment variable name, such as `AGENT_BASICS_EMBEDDING_API_KEY`.
- `runtime.embedding_timeout_seconds: 0` means wait indefinitely for local embedding API validation and RAG embedding calls.
- `runtime.embedding_minimum_dimensions` defaults to `64` and rejects embedding models that are too small for useful retrieval.
- Validate the embedding setup after installation by calling the configured `/v1/embeddings` endpoint or by running `.agents/memory/rag/agent-memory.py doctor --online`.

## Memory CLI

Use `.agents/memory/rag/agent-memory.py` for repo-local memory operations:

- `validate`: check layout and front matter.
- `rebuild`: rebuild the generated SQLite RAG cache.
- `search "<query>"`: run hybrid embedding and full-text retrieval.
- `record <type> <title>`: create a structured memory entry, update `INDEX.md`, and rebuild the index.
- `doctor --online`: report layout, config, manifest, index, and embedding endpoint health.
- `install-hooks`: install local git hooks for memory validation and stale-index rebuilds.

## Recording Rules

- Store project decisions under `.agents/memory/memory/decisions/`.
- Store durable facts under `.agents/memory/memory/facts/`.
- Store user or project preferences under `.agents/memory/memory/preferences/`.
- Store recurring pitfalls under `.agents/memory/memory/gotchas/`.
- Store dated events under `.agents/memory/memory/events/`.
- Store reusable procedures under `.agents/memory/documentations/procedures/`.
- Store reference material under `.agents/memory/documentations/references/`.
- Keep one durable idea per file.
- Do not store secrets.

## Documentation Discipline

- Find up-to-date documentation for any library, framework, API, tool, or programming language used in the project.
- Record documentation source URLs under `.agents/memory/documentations/sources/`.
- While writing code, refer to documentation sources recorded under `.agents/memory/documentations/`.
- Add a new source record when you consult a new external reference that matters for future work.
