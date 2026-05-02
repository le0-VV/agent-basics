# Roadmap

`agent-basics` should become a repo-native memory setup tool for agent-ready projects. The project source of truth is structured markdown under `.agents/memory/`; generated RAG state helps agents retrieve vague or semantically related context.

## Product Principles

- `setup-macos.sh` remains the one-command entry point for macOS users.
- `.agents/memory/` is the canonical memory and documentation source tree.
- Memory entries are predictable markdown files with front matter, templates, and a maintained index.
- RAG indexes, embedding databases, model caches, and embedding API virtualenvs are generated support state and must be rebuildable from markdown.
- Setup requires an embedding provider: either an existing OpenAI-compatible embeddings API or a HuggingFace model that setup can pull and run locally.
- Existing user instructions must be treated as valuable project data. Setup should provide review, ordering, and merge controls before changing them.

## Memory Layout

Use one visible project-local memory tree:

```text
.agents/
├── INSTRUCTIONS.md
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
        ├── embedding.json
        ├── index.sqlite
        ├── manifest.json
        └── write.lock/
```

## Embedding Setup

Setup supports two required paths.

Existing API mode:

1. Read `AGENT_BASICS_EMBEDDING_BASE_URL`.
2. Read `AGENT_BASICS_EMBEDDING_MODEL`.
3. Optionally read the secret from `AGENT_BASICS_EMBEDDING_API_KEY` or another env var named by `AGENT_BASICS_EMBEDDING_API_KEY_ENV`.
4. Call `/v1/embeddings`.
5. Verify the response has OpenAI-compatible shape and a finite numeric vector.
6. Write `.agents/memory/rag/embedding.json`.

HuggingFace local mode:

1. Read `AGENT_BASICS_EMBEDDING_HF_MODEL` as either `owner/model` or `https://huggingface.co/owner/model`.
2. Install a repo-local virtualenv under `.agents/memory/rag/embedding-api/venv`.
3. Install `sentence-transformers`, `fastapi`, and `uvicorn`.
4. Pull the model into `.agents/memory/rag/embedding-api/models`.
5. Verify the model loads and produces finite vectors with enough dimensions.
6. Generate a small OpenAI-compatible embedding API.
7. Write `.agents/memory/rag/embedding.json`.

## RAG And Locking

The RAG layer is a generated cache over `.agents/memory/`.

Current v1 behavior:

- Use `.agents/memory/rag/write.lock/` as the exclusive lock directory.
- Memory writers must wait while the lock exists.
- Indexers hold the lock while hashing, chunking, embedding, and replacing generated indexes.
- Index replacement is atomic.
- `.agents/memory/rag/agent-memory.py` provides `validate`, `rebuild`, `search`, `record`, `doctor`, and `install-hooks`.
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
- Existing `.agents/INSTRUCTIONS.md`
- agent-basics proposed `.agents/INSTRUCTIONS.md`

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

Prefer block-level ordering with line-level highlighting:

- Headings and bullet groups are movable blocks.
- Individual lines remain selectable for fine-grained conflict resolution.
- The output preview should show exactly what will be written.

## Setup Flow

1. Start from `setup-macos.sh`.
2. Create `.agents/memory/` and its source-of-truth layout.
3. Scan for existing `Agents.md`, `.agents/INSTRUCTIONS.md`, `.agents/memory/SCHEMA.md`, `.agents/memory/INDEX.md`, and memory templates.
4. If any markdown file conflicts with the embedded template, prompt for keep, replace, append, manual merge, or save-beside.
5. Copy legacy `.agents/DOCUMENTATIONS.md` and `.agents/MEMORY.md` content into `.agents/memory/` migration entries when those files exist.
6. Configure embeddings through existing API mode or HuggingFace local mode.
7. Write `.agents/memory/rag/embedding.json`.
8. Copy `.agents/memory/rag/agent-memory.py` into the target project.
9. Add generated runtime paths to `.gitignore`.
10. Initialize git when needed.
11. Install local git hooks.
12. Build the initial RAG index.
13. Report final paths and next agent migration tasks.

## CLI Modes

- `agent-basics <directory>`: interactive setup.
- `agent-basics --dry-run <directory>`: detect setup status and show pending file changes without writing.
- `agent-basics --merge-ui <directory>`: open the markdown merge UI directly.
- `agent-basics --doctor <directory>`: verify memory layout, embedding API, and generated RAG health.

Non-interactive mode should remain conservative. It can validate and fail with a clear report, but it should not overwrite or merge instruction files without an explicit reviewed plan.

## Demo Milestone

The first demo is a static browser prototype that proves the markdown merge interaction:

- Two file tabs: `Agents.md` and `.agents/INSTRUCTIONS.md`
- Existing and proposed line sources
- Green identical-line highlighting
- Red differing-line highlighting
- Pick, remove, and reorder controls
- Final markdown preview

This demo is not the production migration engine. It is a UX checkpoint before adding local server wiring, file writes, backup/session persistence, and memory/RAG validation.
