# agent-basics Operating Manual

This file contains agent-basics-specific operating rules. `Agents.md` contains the base agent contract.

## Memory And Documentation

- `.agents/memory/` is the only canonical memory and documentation source tree created by agent-basics.
- Treat markdown under `.agents/memory/` as source of truth. Treat RAG indexes, vector databases, model caches, and embedding API runtime files as generated retrieval support.
- Read `.agents/memory/SCHEMA.md` before creating or changing memory files.
- Use `.agents/memory/templates/` when recording new entries.
- Use the memory MCP server as the primary interface for memory retrieval and recording.
- Call `memory_search` whenever the user refers to previous work, preferences, prior conversations, vague project context, or decisions not visible in the current chat.
- Call `memory_record` for durable decisions, facts, preferences, gotchas, events, documentation sources, and procedures.
- If MCP is unavailable, search `.agents/memory/INDEX.md` and use `.agents/memory/rag/agent-memory.py` as the fallback.
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
- Validate the embedding setup after installation through `memory_doctor` with `online: true`, or by running `.agents/memory/rag/agent-memory.py doctor --online` when MCP is unavailable.

## Memory MCP

Configure capable agents to run the memory MCP server. Prefer the systemwide command when agent-basics was installed through Homebrew:

```json
{
  "mcpServers": {
    "agent-basics-memory": {
      "command": "agent-basics-memory-mcp",
      "cwd": "."
    }
  }
}
```

When the systemwide command is not installed, use the absolute repo-local `.agents/memory/rag/memory-mcp.py` path instead.

For Codex Desktop custom MCP setup, guide the user to Settings -> MCP servers -> Connect to a custom MCP and use:

- Name: `agent-basics-memory`
- Transport: `STDIO`
- Command to launch: `agent-basics-memory-mcp` when installed, otherwise the absolute path to `.agents/memory/rag/memory-mcp.py`
- Arguments: none
- Environment variables: only add the embedding API key variable if `.agents/memory/rag/config.json` names one in `embedding.api_key_env`
- Environment variable passthrough: the same API key variable, only when needed
- Working directory: absolute path to the repository root

For this repository, the command can be `agent-basics-memory-mcp` after Homebrew install, or `/Users/leonardw/Projects/agent-basics/.agents/memory/rag/memory-mcp.py` from the checkout. The working directory is `/Users/leonardw/Projects/agent-basics`.

Keep MCP configuration guidance in this operating manual and memory procedures. Do not rely on a separate `Skills.md` for baseline agent-basics behavior because skills are optional client-side additions, while MCP memory setup is part of the repo contract.

Available MCP tools:

- `memory_search`: run hybrid embedding and full-text retrieval.
- `memory_record`: create a structured memory entry, update `INDEX.md`, and rebuild the index.
- `memory_doctor`: report layout, config, manifest, index, and embedding endpoint health.
- `memory_rebuild`: rebuild the generated SQLite RAG cache.
- `memory_validate`: check layout and front matter.

## Memory CLI

Use `agent-basics-memory` when installed, or `.agents/memory/rag/agent-memory.py` from the checkout, for setup, git hooks, manual recovery, and fallback operations when MCP is not available:

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
