# agent-basics Operating Manual

This file contains agent-basics-specific operating rules. `Agents.md` contains the base agent contract and must stay at the project root so agents discover it reliably.

## OpenViking Context Backend

- OpenViking is the required target backend for agent-basics memory, documentation, resources, skills, semantic organization, and retrieval.
- Agents should not call OpenViking with ad hoc commands when an agent-basics gateway exists. Use the repo-aware `agent-basics mcp` server or stable `agent-basics ov ...` commands.
- Repository-specific OpenViking config and state should live under `.agents/openviking/` once the gateway is implemented.
- `agent-basics` owns setup, upgrade, validation, repo path resolution, git hooks, migration safety, and agent-facing command/MCP contracts.
- OpenViking owns durable context storage, resource ingestion, summaries, semantic search, and vector indexes.
- Before making context-dependent claims, search OpenViking through the gateway.
- Record durable decisions, facts, preferences, gotchas, events, documentation sources, procedures, and reusable skills through the gateway.
- Do not store secrets in OpenViking entries or agent-basics config. Store secret environment variable names only.

## Gateway Contract

The target agent-facing surfaces are:

- `agent-basics mcp`: repo-aware MCP server for OpenViking-backed tools.
- `agent-basics ov doctor`: check OpenViking installation, repo config, providers, ingest status, and health.
- `agent-basics ov search <query>`: retrieve prior context for vague or specific project requests.
- `agent-basics ov record`: record durable context in the correct OpenViking category.
- `agent-basics ov add-resource <path-or-url>`: ingest documentation or reference material.
- `agent-basics ov add-skill <path>`: register reusable agent workflows.
- `agent-basics ov ingest-changed`: update OpenViking after source instructions, docs, or memory files change.
- `agent-basics ov status`: report repo-specific OpenViking state.

When configuring an MCP-capable agent, prefer a systemwide `agent-basics` command with the target repository root as the working directory:

```json
{
  "mcpServers": {
    "agent-basics": {
      "command": "agent-basics",
      "args": ["mcp"],
      "cwd": "/absolute/path/to/repository"
    }
  }
}
```

For Codex Desktop custom MCP setup, guide the user to Settings -> MCP servers -> Connect to a custom MCP and use:

- Name: `agent-basics`
- Transport: `STDIO`
- Command to launch: `agent-basics`
- Arguments: `mcp`
- Environment variables: only provider secret variables named by `.agents/config.toml` or `.agents/openviking/ov.conf`
- Environment variable passthrough: the same provider secret variables, only when needed
- Working directory: absolute path to the repository root

For this repository, the intended working directory is `/Users/leonardw/Projects/agent-basics`.

## Transitional Compatibility

The current repository still contains the custom `.agents/memory/` markdown tree and generated mini-RAG while OpenViking integration is being built.

Use this layer only as compatibility when OpenViking tooling is unavailable:

- Use the memory MCP server first when the client exposes it.
- Call `memory_search` for prior context.
- Call `memory_record` for durable records.
- Let routine `memory_record` calls defer rebuilds.
- Call `memory_rebuild` once after a batch of memory changes, before relying on new entries in search, or before committing memory changes.
- If MCP is unavailable, use `agent-basics memory ...` or `.agents/memory/rag/agent-memory.py ...`.
- Keep `.agents/memory/INDEX.md` updated whenever adding, moving, or removing compatibility entries.
- Do not write `.agents/memory/**` while `.agents/memory/rag/write.lock/` exists.

Compatibility files are not the long-term architecture. When `agent-basics ov` and the OpenViking-backed MCP server are implemented, migrate useful compatibility memory into OpenViking and demote or remove the custom mini-RAG.

## Configuration

- Durable repo configuration belongs in `.agents/config.toml` and `.agents/openviking/` config files once those files exist.
- Provider URLs, model names, timeouts, runtime paths, and feature flags should be stored in config files, not scattered through shell environment variables.
- Environment variables are allowed for secrets, compatibility inputs, and one-off overrides.
- Never commit raw provider API keys or local-only secrets.
- Local provider defaults currently being tested are:
  - LM Studio base URL: `http://127.0.0.1:1234`
  - Chat/VLM model: `google/gemma-4-e4b`
  - Embedding model: `text-embedding-embeddinggemma-300m-qat`

## Long-Horizon Work

- `ROADMAP.md` records project direction, design choices, milestones, non-goals, and open questions.
- `.agents/TODO.md` records the current work plan and cross-session state.
- For substantial work, update `.agents/TODO.md` before editing files and tick items off as they are completed.
- Preserve useful handoff context in `.agents/TODO.md` or future `.agents/runs/<run-id>/` files when work may continue in another session.
- Future run commands should route through `agent-basics run start/status/checkpoint/finish/handoff`.

## Skills And Stable Commands

- Skills should capture repeated workflows such as prework, memory update, finish work, documentation lookup, and verification.
- Skills should point to stable `agent-basics` commands so users can approve predictable command prefixes.
- Do not rely on optional client-side skills as the only source of baseline behavior. Root `Agents.md`, this operating manual, MCP tools, CLI checks, and git hooks remain the repo contract.

## Documentation Discipline

- Find up-to-date documentation for any library, framework, API, tool, or programming language used in the project.
- Record source URLs in OpenViking resources through `agent-basics ov add-resource` when the gateway exists.
- While the compatibility layer is still in use, record important sources under `.agents/memory/documentations/sources/`.
- While writing code, refer to recorded documentation sources before relying on memory for external APIs.
- Add a new source record when a consulted external reference matters for future work.
