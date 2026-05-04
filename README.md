# agent-basics

1 command to set up a repository for reliable agent programming work.

> **THIS SETUP WILL INCREASE TOKEN USAGE IN EXCHANGE FOR MORE RELIABLE AGENT OPERATIONS**

`agent-basics` is a repo-local programming harness. Its direction is to make one user-level OpenViking installation the required memory, documentation, resource, skill, semantic organization, and retrieval backend, while `agent-basics` owns the repository contract around that backend.

The current implementation still includes a custom `.agents/memory/` markdown tree and generated mini-RAG. Treat that layer as transitional compatibility until the OpenViking gateway is implemented and migration is complete.

## Direction

`agent-basics` should provide one stable command:

```bash
agent-basics setup /path/to/project
agent-basics upgrade /path/to/project
agent-basics doctor --online
agent-basics mcp
agent-basics ov doctor
agent-basics ov install-system
agent-basics ov write-default-config --force
agent-basics ov search "what did we decide about memory?"
agent-basics ov record
agent-basics ov add-resource ./docs/api.md
agent-basics ov add-skill .agents/skills/finish-work.md
agent-basics ov ingest-changed
agent-basics lmstudio status
agent-basics lmstudio hardware
agent-basics lmstudio plan
agent-basics lmstudio load --dry-run
agent-basics lmstudio route-test
agent-basics migrate memory-to-openviking --write
agent-basics run start --task "ship the feature"
agent-basics run status
agent-basics run checkpoint
agent-basics run finish
agent-basics verify
agent-basics commit
```

Target responsibilities:

- `agent-basics` installs, verifies, configures, and wraps a user-level OpenViking installation, normally under `~/.openviking`.
- `agent-basics` writes and safely upgrades root `Agents.md`, `.agents/AGENT-BASICS.md`, `.agents/config.toml`, `.agents/openviking/`, `.agents/skills/`, and `.agents/runs/`.
- `agent-basics mcp` exposes repo-aware OpenViking tools for search, record, resource ingest, skill ingest, changed-file ingest, and health checks.
- OpenViking owns durable memory, documentation resources, semantic summaries, embedding indexes, vector search, and context organization.
- Root `Agents.md` remains the agent entrypoint.
- `.agents/AGENT-BASICS.md` remains the agent-basics operating manual.
- `ROADMAP.md` records long-horizon project direction.
- `.agents/TODO.md` records current cross-session work state.

## Current Compatibility Commands

These commands exist today and are kept while the OpenViking-backed gateway is being built:

```bash
agent-basics setup /path/to/project
agent-basics upgrade /path/to/project
agent-basics memory validate
agent-basics memory rebuild
agent-basics memory search "what did we decide about memory?"
agent-basics memory doctor --online
agent-basics mcp
```

`setup` and `upgrade` run the same safe setup flow. Re-running setup on an existing repository is the supported upgrade path for older agent-basics layouts: overlapping markdown files prompt for keep, replace, append, manual merge, web merge, or save-beside.

## Target Repository Layout

```text
.
├── Agents.md
├── ROADMAP.md
├── Skills.md
└── .agents/
    ├── AGENT-BASICS.md
    ├── TODO.md
    ├── config.toml
    ├── openviking/
    │   ├── repo.json
    │   ├── migration-manifest.json
    │   └── locks/
    ├── skills/
    │   ├── prework.md
    │   ├── memory-update.md
    │   └── finish-work.md
    ├── runs/
    │   └── <run-id>/
    │       ├── state.json
    │       ├── CHECKPOINT.md
    │       └── handoff.md
    ├── merge-sessions/
    └── backups/
```

The current compatibility layout also creates `.agents/memory/`:

```text
.agents/memory/
  SCHEMA.md
  INDEX.md
  templates/
  memory/
  documentations/
  rag/
    agent-memory.py
    memory-mcp.py
    config.json
    index.sqlite
    manifest.json
```

Markdown under `.agents/memory/` remains the compatibility source of truth until migration. Generated RAG indexes, vector stores, model caches, and embedding API virtualenvs are rebuildable support state.

## OpenViking Gateway

The planned gateway keeps OpenViking executable details out of normal agent workflows:

- `agent-basics ov doctor`: verify the user-level OpenViking installation, repo config, provider health, and ingest state.
- `agent-basics ov install-system`: install OpenViking under `~/.openviking` when it is missing.
- `agent-basics ov write-default-config`: write a default `~/.openviking/ov.conf` for LM Studio Gemma 4 E2B plus EmbeddingGemma.
- `agent-basics ov search <query>`: search memory, docs, resources, and skills.
- `agent-basics ov record`: record durable context into the right OpenViking category.
- `agent-basics ov add-resource <path-or-url>`: ingest project documentation or external sources.
- `agent-basics ov add-skill <path>`: register reusable agent workflows.
- `agent-basics ov ingest-changed`: update OpenViking after relevant files change.
- `agent-basics ov status`: report repo-specific OpenViking state.

MCP-capable agents should use the repo-aware MCP server instead of invoking raw OpenViking directly:

```json
{
  "mcpServers": {
    "agent-basics": {
      "command": "agent-basics",
      "args": ["mcp"],
      "cwd": "/path/to/project"
    }
  }
}
```

For Codex Desktop custom MCP setup:

- Name: `agent-basics`
- Transport: `STDIO`
- Command to launch: `agent-basics`
- Arguments: `mcp`
- Environment variables: provider secret variables only, as named by agent-basics/OpenViking config
- Environment variable passthrough: the same provider secret variables, only when needed
- Working directory: absolute path to the repository root

## Setup And Migration

The target setup flow should:

1. Detect project root and git state.
2. Detect existing `Agents.md`, `.agents/AGENT-BASICS.md`, legacy `.agents/INSTRUCTIONS.md`, `.agents/memory/`, and existing OpenViking state.
3. Check whether OpenViking is installed.
4. Install OpenViking or stop with clear instructions when installation is not allowed.
5. Configure repo-local OpenViking metadata under `.agents/openviking/`.
6. Configure LLM/VLM and embedding providers.
7. Verify providers with a doctor check.
8. Write or safely merge root `Agents.md`.
9. Write or safely merge `.agents/AGENT-BASICS.md`.
10. Write `.agents/config.toml`.
11. Create `.agents/TODO.md`, `.agents/skills/`, `.agents/runs/`, `.agents/backups/`, and `.agents/merge-sessions/`.
12. Configure `agent-basics mcp` where possible.
13. Install git hooks.
14. Ingest initial project instructions and selected documentation into OpenViking.
15. Report final paths, health, and next agent actions.

The current setup script already handles markdown conflicts safely. When an existing markdown file differs from the agent-basics template, it prompts per file to keep, replace with backup, append with backup, manually merge in `$EDITOR`, use a local web merge UI, or save the incoming template beside the existing file as `*.agent-basics.new`.

If legacy `.agents/DOCUMENTATIONS.md` or `.agents/MEMORY.md` files exist, the compatibility setup copies their content into `.agents/memory/` migration entries without deleting the original files.

## Compatibility Embedding Setup

Compatibility mini-RAG setup requires one embedding configuration.

Use an existing OpenAI-compatible embeddings API:

```bash
agent-basics setup /path/to/project \
  --embedding-mode api \
  --embedding-base-url http://127.0.0.1:1234/v1 \
  --embedding-model text-embedding-embeddinggemma-300m-qat
```

Setup validates these values and writes durable mini-RAG runtime settings into `.agents/memory/rag/config.json`. `runtime.embedding_timeout_seconds: 0` means wait indefinitely for local embedding API responses. Set it to a positive number of seconds with `--embedding-timeout` if you want setup and RAG commands to fail faster.

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

## Install Via Custom Homebrew Tap

```bash
brew tap le0-VV/agent-basics
brew install --HEAD le0-VV/agent-basics/agent-basics
```

This builds and installs one binary:

- `agent-basics setup [DIR]`: set up or upgrade a repository, including older agent-basics layouts with overlapping markdown files.
- `agent-basics ov doctor`: inspect the user-level OpenViking installation and config.
- `agent-basics ov install-system`: install OpenViking under `~/.openviking`.
- `agent-basics ov write-default-config`: write the default LM Studio-backed OpenViking config.
- `agent-basics lmstudio status|hardware|plan|load|unload|route-test`: inspect and manage LM Studio through REST/OpenAI-compatible HTTP only.
- `agent-basics migrate memory-to-openviking`: inventory legacy `.agents/memory/` records into OV-native categories.
- `agent-basics memory ...`: run compatibility memory/RAG operations for the current working repository.
- `agent-basics mcp`: run the stdio MCP server for the current working repository. This is currently compatibility memory-backed and should become OpenViking-backed.

Upgrade with:

```bash
brew update
brew upgrade agent-basics
```

## Key Files

- `Agents.md`: project-root agent entrypoint. Keep this file at the repository root so agents discover it reliably.
- `.agents/AGENT-BASICS.md`: agent-basics operating manual for the OpenViking-backed harness direction and current compatibility layer.
- `ROADMAP.md`: long-horizon architecture, milestones, and non-goals.
- `.agents/TODO.md`: current agent work plan and cross-session state. It is untracked by git by design.
- `.agents/config.toml`: target durable repo config.
- `.agents/openviking/`: target repo-local OpenViking metadata, migration manifests, and locks. The OpenViking install and workspace stay under `~/.openviking` unless the user explicitly chooses another user-level location.
- `.agents/skills/` or `Skills.md`: target repeated workflows that point to stable `agent-basics` commands.
- `.agents/runs/`: target long-horizon run state and handoff files.
- `.agents/memory/`: transitional compatibility memory, documentation, and mini-RAG files.

## LM Studio Safety

On macOS, `agent-basics` should not use the `lms` CLI from Codex or other sandboxed agent hosts. On this machine, `lms` launched the LM Studio Electron app and crashed during AppKit registration. The safe path is:

1. The user starts LM Studio and its local server.
2. Agents call `agent-basics lmstudio status` to verify HTTP reachability.
3. Agents call `agent-basics lmstudio plan` to inspect the proposed E2B load settings.
4. Agents call `agent-basics lmstudio load` only when model loading through REST is desired.

The default local model plan is Gemma 4 E2B with max context, max GPU offload, concurrency 1, KV cache quantization `q4_0`, flash attention enabled, and temperature 0 for routing tests.
