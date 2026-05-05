# agent-basics Operating Manual

This file contains agent-basics-specific operating rules. `Agents.md` contains the base agent contract and must stay at the project root so agents discover it reliably.

## OpenViking Context Backend

- OpenViking is the required target backend for agent-basics memory, documentation, resources, skills, semantic organization, and retrieval.
- Agents should not call OpenViking with ad hoc commands when an agent-basics gateway exists. Use the repo-aware `agent-basics mcp` server or stable `agent-basics ov ...` commands.
- Repository-specific OpenViking metadata, import state, and locks live under `.agents/openviking/`. The OpenViking package and workspace live in the user-level installation, normally `~/.openviking`, not inside each repository.
- `agent-basics` owns setup, upgrade, validation, repo path resolution, git hooks, migration safety, and agent-facing command/MCP contracts.
- OpenViking owns durable context storage, resource ingestion, summaries, semantic search, and vector indexes.
- Before making context-dependent claims, search OpenViking through the gateway.
- Record durable decisions, facts, preferences, gotchas, events, documentation sources, procedures, and reusable skills through the gateway.
- Do not store secrets in OpenViking entries or agent-basics config. Store secret environment variable names only.

## Gateway Contract

The target agent-facing surfaces are:

- `agent-basics mcp`: repo-aware MCP server for OpenViking-backed tools.
- `agent-basics ov doctor`: check OpenViking installation, repo config, providers, ingest status, and health.
- `agent-basics ov bootstrap-system`: install OpenViking under `~/.openviking` when missing, write default config, and install the macOS LaunchAgent when available.
- `agent-basics ov install-system`: low-level repair command for only the OpenViking package installation.
- `agent-basics ov write-default-config`: low-level repair command for default `~/.openviking/ov.conf` and `~/.openviking/ovcli.conf` for LM Studio Gemma 4 E2B plus EmbeddingGemma.
- `agent-basics ov service install`: install and load the configured user-level OpenViking HTTP server as a macOS LaunchAgent.
- `agent-basics ov server`: start the configured user-level OpenViking HTTP server in the foreground for debugging.
- `agent-basics ov import-repo-memory`: write `.agents/memory/` OV-native memories into OpenViking memory categories and ingest resources/skills.
- `agent-basics ov search <query>`: retrieve prior context for vague or specific project requests.
- `agent-basics ov record`: record durable context in the correct OpenViking category.
- `agent-basics ov add-resource <path-or-url>`: ingest documentation or reference material.
- `agent-basics ov add-skill <path>`: register reusable agent workflows.
- `agent-basics ov ingest-changed`: update OpenViking after source instructions, docs, or memory files change.
- `agent-basics ov install-hooks`: install repo-local hooks that refresh OpenViking after source-store changes.
- `agent-basics ov status`: report repo-specific OpenViking state.

When configuring an MCP-capable agent, prefer a systemwide `agent-basics` command without a fixed working directory. Agents should pass their current working directory through the `cwd` tool argument on each repo-scoped call:

```json
{
  "mcpServers": {
    "agent-basics": {
      "command": "agent-basics",
      "args": ["mcp"]
    }
  }
}
```

For Codex Desktop custom MCP setup, guide the user to Settings -> MCP servers -> Connect to a custom MCP and use:

- Name: `agent-basics`
- Transport: `STDIO`
- Command to launch: `agent-basics`
- Arguments: `mcp`
- Environment variables: only provider secret variables named by `.agents/config.toml` or the user-level `~/.openviking/ov.conf`
- Environment variable passthrough: the same provider secret variables, only when needed
- Working directory: leave unset/default
- Tool calls: pass `cwd` as the repository root or any directory inside it

## Legacy Compatibility

This repository still contains the older `.agents/memory/` markdown mini-RAG source files because this repo is also an agent-basics development checkout. Fresh setup does not install that legacy mini-RAG unless `AGENT_BASICS_INSTALL_COMPAT_MEMORY=1` is set.

Use this layer only as fallback compatibility when OpenViking tooling is unavailable and work must continue:

- Prefer the OpenViking-backed `agent-basics mcp` server for normal work.
- Use the compatibility memory MCP server only if it is explicitly configured.
- Call compatibility `memory_search` for prior context only when OpenViking search is unavailable.
- Call compatibility `memory_record` for durable records only when OpenViking recording is unavailable.
- Let routine `memory_record` calls defer rebuilds.
- Call `memory_rebuild` once after a batch of memory changes, before relying on new entries in search, or before committing memory changes.
- If MCP is unavailable, use `agent-basics memory ...` or `.agents/memory/rag/agent-memory.py ...`.
- Keep `.agents/memory/INDEX.md` updated whenever adding, moving, or removing compatibility entries.
- Do not write `.agents/memory/**` while `.agents/memory/rag/write.lock/` exists.

Compatibility files are not the long-term architecture. Useful compatibility memory should be adapted into `.agents/memory/memories/`, `.agents/memory/resources/`, or `.agents/memory/skills/`, ingested through OpenViking, and then treated as legacy source-checkout fallback.

## Configuration

- Durable repo configuration belongs in `.agents/config.toml` and repo metadata belongs in `.agents/openviking/`.
- OpenViking provider URLs, model names, timeouts, runtime paths, and feature flags belong in the user-level `~/.openviking/ov.conf`, not scattered through shell environment variables.
- Environment variables are allowed for secrets, compatibility inputs, and one-off overrides.
- Never commit raw provider API keys or local-only secrets.
- Local provider defaults currently being tested are:
  - LM Studio base URL: `http://127.0.0.1:1234`
  - Chat/VLM model: `google/gemma-4-e2b`
  - Embedding model: `text-embedding-embeddinggemma-300m-qat`

## Long-Horizon Work

- `ROADMAP.md` records project direction, design choices, milestones, non-goals, and open questions.
- `.agents/TODO.md` records the current work plan and cross-session state.
- For substantial work, update `.agents/TODO.md` before editing files and tick items off as they are completed.
- Preserve useful handoff context in `.agents/TODO.md`, OpenViking records, commits, pull requests, or chat handoff notes when work may continue in another session.
- Pre-work and finish-work routines are instruction-driven. agent-basics does not try to enforce them with a local run-state command.

## Skills And Stable Commands

- Skills should capture repeated workflows such as prework, memory update, finish work, documentation lookup, and verification.
- Skills should point to stable `agent-basics` commands so users can approve predictable command prefixes.
- Do not rely on optional client-side skills as the only source of baseline behavior. Root `Agents.md`, this operating manual, MCP tools, CLI checks, and git hooks remain the repo contract.

## Documentation Discipline

- Find up-to-date documentation for any library, framework, API, tool, or programming language used in the project.
- Record source URLs in OpenViking resources through `agent-basics ov add-resource` when the gateway exists.
- Record important sources under `.agents/memory/resources/` when maintaining repo-owned source-store files. Use legacy `.agents/memory/documentations/sources/` only while explicitly operating the compatibility layer.
- While writing code, refer to recorded documentation sources before relying on memory for external APIs.
- Add a new source record when a consulted external reference matters for future work.
