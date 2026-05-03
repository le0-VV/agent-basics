# agent-basics

1 command to setup a directory for reliable agent workflows.

> **THIS SETUP WILL INCREASE TOKEN USAGE IN EXCHANGE FOR MORE RELIABLE AGENT OPERATIONS**

`agent-basics` keeps memory and documentation source in the repository. It sets up one `.agents/memory/` tree, validates an embedding provider, and leaves generated RAG/index state rebuildable from markdown.

## Command interface

`agent-basics` is the only installed command. Homebrew builds it as a Rust binary that embeds the setup, memory CLI, and MCP implementation.

```bash
agent-basics setup /path/to/project
agent-basics upgrade /path/to/project
agent-basics memory validate
agent-basics memory rebuild
agent-basics memory search "what did we decide about memory?"
agent-basics memory doctor --online
agent-basics mcp
```

`setup` and `upgrade` run the same safe setup flow. Re-running it on an existing repository is the supported upgrade path for older agent-basics layouts: overlapping markdown files prompt for keep, replace, append, manual merge, web merge, or save-beside.

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

Markdown under `.agents/memory/` is the source of truth. RAG indexes, vector stores, model caches, and embedding API virtualenvs are generated support state. Agents should use the memory MCP server for memory access and use the CLI only for setup, hooks, manual recovery, or MCP fallback.

If legacy `.agents/DOCUMENTATIONS.md` or `.agents/MEMORY.md` files exist, setup copies their content into `.agents/memory/` migration entries without deleting the original files.

## Embedding setup

Setup requires one of two embedding configurations.

Use an existing OpenAI-compatible embeddings API:

```bash
agent-basics setup /path/to/project \
  --embedding-mode api \
  --embedding-base-url http://127.0.0.1:1234/v1 \
  --embedding-model text-embedding-embeddinggemma-300m-qat
```

Setup validates these values and writes durable RAG runtime settings into `.agents/memory/rag/config.json`. `runtime.embedding_timeout_seconds: 0` means wait indefinitely for embedding API responses. Set it to a positive number of seconds with `--embedding-timeout` if you want setup and RAG commands to fail faster.

If an embedding provider needs a secret, keep the secret in your shell and pass only the variable name:

```bash
export MY_EMBEDDING_API_KEY="..."
agent-basics setup /path/to/project \
  --embedding-mode api \
  --embedding-base-url https://embedding.example/v1 \
  --embedding-model my-embedding-model \
  --embedding-api-key-env MY_EMBEDDING_API_KEY
```

Environment variables are still accepted as setup inputs, secret pointers, and one-off overrides, but they are not the durable project configuration.

Or provide a HuggingFace model id or URL. Setup installs a repo-local Python virtualenv, pulls the model, verifies that it can produce finite vectors, and writes a small OpenAI-compatible API under `.agents/memory/rag/embedding-api/`.

```bash
agent-basics setup /path/to/project \
  --embedding-mode huggingface \
  --embedding-hf-model Qwen/Qwen3-Embedding-0.6B
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

Homebrew installs one systemwide `agent-basics` command. Setup also copies `.agents/memory/rag/memory-mcp.py` into each project as a repo-local fallback.

Configure MCP-capable agents with the repository root as `cwd`:

```json
{
  "mcpServers": {
    "agent-basics-memory": {
      "command": "agent-basics",
      "args": ["mcp"],
      "cwd": "/path/to/project"
    }
  }
}
```

For Codex Desktop custom MCP setup:

- Name: `agent-basics-memory`
- Transport: `STDIO`
- Command to launch: `agent-basics` when installed, otherwise the absolute path to `.agents/memory/rag/memory-mcp.py`
- Arguments: `mcp` when using `agent-basics`; none when using the repo-local fallback script
- Environment variables: leave blank unless `config.json` names an API key variable
- Environment variable passthrough: same API key variable only when needed
- Working directory: absolute path to the repository root

Available tools:

- `memory_search`: search prior project context with hybrid embeddings and full-text retrieval.
- `memory_record`: record durable memories with structured fields and rebuild the index.
- `memory_doctor`: inspect layout, config, index freshness, and embedding endpoint health.
- `memory_rebuild`: rebuild the generated SQLite RAG index.
- `memory_validate`: validate memory layout and front matter.

## Memory CLI

Homebrew exposes memory operations under `agent-basics memory`. Setup also installs `.agents/memory/rag/agent-memory.py` into each project for git hooks, manual recovery, and fallback use when the systemwide command is unavailable.

Common commands:

```bash
agent-basics memory validate
agent-basics memory rebuild
agent-basics memory search "what did we decide about memory?"
agent-basics memory record decision "Use repo-local memory" \
  --content "Markdown remains source of truth." \
  --rationale "Agents need predictable repo-local context."
agent-basics memory doctor --online
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

This builds and installs one binary:

- `agent-basics setup [DIR]`: set up or upgrade a repository, including older agent-basics layouts with overlapping markdown files.
- `agent-basics memory ...`: run memory/RAG operations for the current working repository.
- `agent-basics mcp`: run the stdio MCP server for the current working repository.

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
  Agents should access this through `agent-basics mcp` first.

- ### TODO.md

  The instructions tell agents to use this TODO to record and stick to their work plan. This helps agents work coherently and stay on track after context compaction. It is untracked by git by design.
