# Roadmap

`agent-basics` should become a repo-native memory setup tool for agent-ready projects. The project source of truth is structured markdown under `.agents/memory/`; generated RAG state helps agents retrieve vague or semantically related context.

## Product Principles

- `agent-basics` is the one-command entry point for macOS users; `setup-macos.sh` remains the setup implementation detail.
- `.agents/memory/` is the canonical memory and documentation source tree.
- Memory entries are predictable markdown files with front matter, templates, and a maintained index.
- RAG indexes, embedding databases, model caches, and embedding API virtualenvs are generated support state and must be rebuildable from markdown.
- Agent-facing memory access should go through the memory MCP server first; direct CLI usage is for setup, hooks, manual recovery, and fallback.
- Homebrew installs one stable systemwide `agent-basics` command so users can configure MCP once as `agent-basics mcp` and set only the repository working directory.
- Setup requires an embedding provider: either an existing OpenAI-compatible embeddings API or a HuggingFace model that setup can pull and run locally.
- Existing user instructions must be treated as valuable project data. Setup should provide review, ordering, and merge controls before changing them.

## Memory Layout

Use one visible project-local memory tree:

```text
.agents/
├── AGENT-BASICS.md
├── TODO.md
└── memory/
    ├── SCHEMA.md
    ├── INDEX.md
    ├── templates/
    │   ├── decision.md
    │   ├── fact.md
    │   ├── preference.md
    │   ├── source.md
    │   ├── procedure.md
    │   ├── gotcha.md
    │   └── event.md
    ├── memory/
    │   ├── decisions/
    │   ├── facts/
    │   ├── preferences/
    │   ├── gotchas/
    │   └── events/
    ├── documentations/
    │   ├── sources/
    │   ├── procedures/
    │   └── references/
    └── rag/
        ├── agent-memory.py
        ├── memory-mcp.py
        ├── config.json
        ├── index.sqlite
        ├── manifest.json
        └── write.lock/
```

## Embedding Setup

Setup supports two required paths.

Existing API mode:

1. Read setup inputs from `agent-basics setup --embedding-mode api`.
2. Read `--embedding-base-url`.
3. Read `--embedding-model`.
4. Optionally read the secret from the env var named by `--embedding-api-key-env`.
5. Call `/v1/embeddings`.
6. Verify the response has OpenAI-compatible shape and a finite numeric vector.
7. Write `.agents/memory/rag/config.json`.

HuggingFace local mode:

1. Read setup inputs from `agent-basics setup --embedding-mode huggingface`.
2. Read `--embedding-hf-model` as either `owner/model` or `https://huggingface.co/owner/model`.
3. Install a repo-local virtualenv under `.agents/memory/rag/embedding-api/venv`.
4. Install `sentence-transformers`, `fastapi`, and `uvicorn`.
5. Pull the model into `.agents/memory/rag/embedding-api/models`.
6. Verify the model loads and produces finite vectors with enough dimensions.
7. Generate a small OpenAI-compatible embedding API.
8. Write `.agents/memory/rag/config.json`.

## RAG And Locking

The RAG layer is a generated cache over `.agents/memory/`.

Current v1 behavior:

- Use `.agents/memory/rag/write.lock/` as the exclusive lock directory.
- Memory writers must wait while the lock exists.
- Indexers hold the lock while hashing, chunking, embedding, and replacing generated indexes.
- Index replacement is atomic.
- `agent-basics mcp` exposes `memory_search`, `memory_record`, `memory_doctor`, `memory_rebuild`, and `memory_validate` as the primary agent-facing interface when installed.
- `agent-basics memory ...` provides CLI support for setup, hooks, manual recovery, and fallback operations when installed.
- `.agents/memory/rag/memory-mcp.py` and `.agents/memory/rag/agent-memory.py` remain repo-local fallbacks for source checkouts and generated hooks.
- Setup installs git hooks that validate memory before commit and rebuild the index after committed memory changes.
- Stale lock repair should be explicit, not automatic.

Initial retrieval is hybrid:

- Full-text search for exact terms, file paths, commands, URLs, tags, and package names.
- Embeddings for vague or semantically similar user requests.
- Metadata filters from front matter.
- Results must cite source markdown paths and snippets.

## Migration UI

Build an interactive local web UI for existing projects that already contain agent instruction files.

The first supported scope is intentionally narrow:

- Existing `Agents.md`
- agent-basics proposed `Agents.md`
- Existing `.agents/AGENT-BASICS.md` or legacy `.agents/INSTRUCTIONS.md`
- agent-basics proposed `.agents/AGENT-BASICS.md`

The UI should let users:

- Compare existing and proposed markdown.
- See identical lines highlighted in green.
- See differing or conflicting lines highlighted in red.
- Pick which lines or blocks belong in the final file.
- Reorder selected instructions before writing the final file.
- Preserve custom instruction ordering.
- Preview the final markdown before applying changes.
- Apply changes only after creating backups under `.agents/memory/backups/`.
- Save an unresolved merge session under `.agents/memory/merge-sessions/`.
- Setup should offer this local web merge UI directly from markdown conflict prompts, with `$EDITOR` as a fallback.

Prefer block-level ordering with line-level highlighting:

- Headings and bullet groups are movable blocks.
- Individual lines remain selectable for fine-grained conflict resolution.
- The output preview should show exactly what will be written.

## Setup Flow

1. Start from `agent-basics setup`; internally it runs `setup-macos.sh`.
2. Create `.agents/memory/` and its source-of-truth layout.
3. Scan for existing root `Agents.md`, `.agents/AGENT-BASICS.md`, legacy `.agents/INSTRUCTIONS.md`, `.agents/memory/SCHEMA.md`, `.agents/memory/INDEX.md`, and memory templates.
4. If any markdown file conflicts with the embedded template, prompt for keep, replace, append, manual merge, or save-beside.
5. Copy legacy `.agents/DOCUMENTATIONS.md` and `.agents/MEMORY.md` content into `.agents/memory/` migration entries when those files exist.
6. Configure embeddings through existing API mode or HuggingFace local mode.
7. Write `.agents/memory/rag/config.json`.
8. Copy `.agents/memory/rag/agent-memory.py` and `.agents/memory/rag/memory-mcp.py` into the target project.
9. Add generated runtime paths to `.gitignore`.
10. Initialize git when needed.
11. Install local git hooks.
12. Build the initial RAG index.
13. Report final paths and next agent migration tasks.

## CLI Modes

- `agent-basics setup [directory]`: interactive setup for a new repository.
- `agent-basics upgrade [directory]`: rerun setup on an existing repository and safely handle overlapping files.
- `agent-basics [directory]`: compatibility shortcut for setup.
- `agent-basics memory <command>`: run memory/RAG operations such as `validate`, `rebuild`, `search`, `record`, `doctor`, and `install-hooks`.
- `agent-basics doctor [--online]`: shortcut for memory health checks.
- `agent-basics mcp`: run the stdio memory MCP server for the current working repository.
- `agent-basics --repo <directory> <command>`: run an operation against another repository.

Planned:

- `agent-basics setup --dry-run <directory>`: detect setup status and show pending file changes without writing.
- `agent-basics setup --merge-ui <directory>`: open the markdown merge UI directly.

Non-interactive mode should remain conservative. It can validate and fail with a clear report, but it should not overwrite or merge instruction files without an explicit reviewed plan.

## Demo Milestone

The first demo is a static browser prototype that proves the markdown merge interaction:

- Two file tabs: root `Agents.md` and `.agents/AGENT-BASICS.md`
- Existing and proposed line sources
- Green identical-line highlighting
- Red differing-line highlighting
- Pick, remove, and reorder controls
- Final markdown preview

This demo is not the production migration engine. It is a UX checkpoint before adding local server wiring, file writes, backup/session persistence, and memory/RAG validation.
