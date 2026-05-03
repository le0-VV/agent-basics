# agent-basics

1 command to setup a directory for reliable agent workflows.

> **THIS SETUP WILL INCREASE TOKEN USAGE IN EXCHANGE FOR MORE RELIABLE AGENT OPERATIONS**

`agent-basics` keeps memory and documentation source in the repository. It sets up one `.agents/memory/` tree, validates an embedding provider, and leaves generated RAG/index state rebuildable from markdown.

## How it works

The command checks for the existence of, and if needed adds, the following structure:

```text
.
├── .agents
│   ├── AGENT-BASICS.md
│   ├── TODO.md
│   └── memory
│       ├── SCHEMA.md
│       ├── INDEX.md
│       ├── templates
│       │   ├── decision.md
│       │   ├── fact.md
│       │   ├── preference.md
│       │   ├── source.md
│       │   ├── procedure.md
│       │   ├── gotcha.md
│       │   └── event.md
│       ├── memory
│       │   ├── decisions
│       │   ├── facts
│       │   ├── preferences
│       │   ├── gotchas
│       │   └── events
│       ├── documentations
│       │   ├── sources
│       │   ├── procedures
│       │   └── references
│       └── rag
│           ├── agent-memory.py
│           ├── memory-mcp.py
│           ├── config.json
│           ├── index.sqlite
│           └── manifest.json
├── .gitignore
└── Agents.md
```

Markdown under `.agents/memory/` is the source of truth. RAG indexes, vector stores, model caches, and embedding API virtualenvs are generated support state. Agents should use the repo-local MCP server for memory access and use the CLI only for setup, hooks, manual recovery, or MCP fallback.

If legacy `.agents/DOCUMENTATIONS.md` or `.agents/MEMORY.md` files exist, setup copies their content into `.agents/memory/` migration entries without deleting the original files.

## Embedding setup

Setup requires one of two embedding configurations.

Use an existing OpenAI-compatible embeddings API:

```bash
export AGENT_BASICS_EMBEDDING_BASE_URL="http://127.0.0.1:1234/v1"
export AGENT_BASICS_EMBEDDING_MODEL="text-embedding-embeddinggemma-300m-qat"
export AGENT_BASICS_EMBEDDING_API_KEY=""
./setup-macos.sh /path/to/project
```

Setup writes durable RAG runtime settings into `.agents/memory/rag/config.json`. `runtime.embedding_timeout_seconds: 0` means wait indefinitely for embedding API responses. Set it to a positive number of seconds if you want setup and RAG commands to fail faster.

Environment variables are still accepted for noninteractive setup, secrets, and one-off overrides, but they are not the durable project configuration.

Or provide a HuggingFace model id or URL. Setup installs a repo-local Python virtualenv, pulls the model, verifies that it can produce finite vectors, and writes a small OpenAI-compatible API under `.agents/memory/rag/embedding-api/`.

```bash
export AGENT_BASICS_EMBEDDING_HF_MODEL="Qwen/Qwen3-Embedding-0.6B"
./setup-macos.sh /path/to/project
```

Start the generated local API with:

```bash
.agents/memory/rag/embedding-api/start.sh
```

The generated service exposes:

- `GET /health`
- `GET /v1/models`
- `POST /v1/embeddings`

The script writes root `Agents.md`, `.agents/AGENT-BASICS.md`, `.agents/memory/SCHEMA.md`, `.agents/memory/INDEX.md`, and memory templates from embedded text. When an existing markdown file differs from the template, it prompts per file to keep the existing file, replace it after creating a backup, append the template after creating a backup, manually merge both versions in `$EDITOR`, use a local web merge UI, or save the incoming template beside the existing file as `*.agent-basics.new`.

For `.gitignore`, the script is non-interactive: it appends transient memory/RAG paths only when missing.

## Memory MCP

Setup installs `.agents/memory/rag/memory-mcp.py` into each project. Configure MCP-capable agents with the repository root as `cwd`:

```json
{
  "mcpServers": {
    "agent-basics-memory": {
      "command": ".agents/memory/rag/memory-mcp.py",
      "cwd": "/path/to/project"
    }
  }
}
```

For Codex Desktop custom MCP setup:

- Name: `agent-basics-memory`
- Transport: `STDIO`
- Command to launch: absolute path to `.agents/memory/rag/memory-mcp.py`
- Arguments: none
- Environment variables: leave blank unless `config.json` names an API key variable
- Environment variable passthrough: same API key variable only when needed
- Working directory: absolute path to the repository root

Available tools:

- `memory_search`: search prior project context with hybrid embeddings and full-text retrieval.
- `memory_record`: record durable memories and rebuild the index.
- `memory_doctor`: inspect layout, config, index freshness, and embedding endpoint health.
- `memory_rebuild`: rebuild the generated SQLite RAG index.
- `memory_validate`: validate memory layout and front matter.

## Memory CLI

Setup also installs `.agents/memory/rag/agent-memory.py` into each project for setup, git hooks, manual recovery, and fallback use when MCP is unavailable.

Common commands:

```bash
.agents/memory/rag/agent-memory.py validate
.agents/memory/rag/agent-memory.py rebuild
.agents/memory/rag/agent-memory.py search "what did we decide about memory?"
.agents/memory/rag/agent-memory.py record decision "Use repo-local memory" --content "Markdown remains source of truth."
.agents/memory/rag/agent-memory.py doctor --online
```

The generated index uses SQLite FTS plus embedding vectors from the configured embedding API. Setup also installs local git hooks:

- `pre-commit`: validate changed `.agents/memory/` entries.
- `post-commit`: rebuild the index after committed memory changes.
- `post-merge` and `post-checkout`: rebuild when the memory tree is stale after branch changes.

## Install via custom Homebrew tap

```bash
brew tap le0-VV/agent-basics
brew install --HEAD le0-VV/agent-basics/agent-basics
```

### Upgrade

```bash
brew update
brew upgrade agent-basics
```

## The files

- ### Agents.md

  The project-root agent entrypoint. Keep this file at the repository root so agents discover it reliably. It contains the base agent contract and points to `.agents/AGENT-BASICS.md` for agent-basics operating details.

- ### `.agents/AGENT-BASICS.md`

  The agent-basics operating manual: memory layout, RAG config, memory CLI, recording rules, and documentation discipline.

- ### `.agents/memory/SCHEMA.md`

  The contract for memory/documentation entries, required front matter, locking behavior, and embedding configuration.

- ### `.agents/memory/INDEX.md`

  Human-readable map of the memory tree. Agents update this when adding, moving, or removing entries.

- ### `.agents/memory/templates/`

  Entry templates for decisions, facts, preferences, documentation sources, procedures, gotchas, and events.

- ### `.agents/memory/rag/`

  Generated retrieval support plus project RAG config. `config.json` records the active embedding provider and runtime settings. Local HuggingFace model APIs are generated under `embedding-api/`.
  Agents should access this through `memory-mcp.py` first.

- ### TODO.md

  The instructions tell agents to use this TODO to record and stick to their work plan. This helps agents work coherently and stay on track after context compaction. It is untracked by git by design.
