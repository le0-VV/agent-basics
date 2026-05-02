# Memory Schema

`.agents/memory/` is the project-owned source of truth for agent memory and documentation.

Generated RAG indexes, vector stores, model caches, and embedding API virtualenvs are support artifacts. They must be rebuildable from markdown in this directory.

## Directory Contract

```text
.agents/memory/
  SCHEMA.md
  INDEX.md
  templates/
    decision.md
    fact.md
    preference.md
    source.md
    procedure.md
    gotcha.md
    event.md
  memory/
    decisions/
    facts/
    preferences/
    gotchas/
    events/
  documentations/
    sources/
    procedures/
    references/
  rag/
    embedding.json
    write.lock/
```

## Entry Rules

- Every entry must be markdown.
- Every entry must start with YAML front matter.
- Every entry must have `id`, `type`, `title`, `status`, `created`, `updated`, `tags`, and `summary`.
- Use ISO dates: `YYYY-MM-DD`.
- Keep one durable idea per file.
- Prefer short, searchable headings.
- Link related entries with relative paths.
- Record source URLs for external documentation.
- Do not store secrets.

## Types

- `decision`: accepted or rejected project choice and rationale.
- `fact`: stable project fact.
- `preference`: user or project preference.
- `source`: documentation source record.
- `procedure`: repeatable workflow.
- `gotcha`: pitfall, failure mode, or workaround.
- `event`: dated thing that happened.

## RAG Locking

`.agents/memory/rag/write.lock/` is an exclusive lock directory.

- Memory writers must wait while it exists.
- Indexers must create it before hashing, chunking, embedding, or replacing indexes.
- Indexers must remove it only after the generated index is consistent with source markdown.
- If the lock is stale because a process crashed, use a deliberate repair command rather than deleting it opportunistically.

## Embedding Configuration

`.agents/memory/rag/embedding.json` records the active embedding provider.

External API mode stores:

- `provider`
- `base_url`
- `model`
- `dimensions`
- `api_key_env`

Repo-local HuggingFace mode additionally stores:

- `service_dir`
- `start_command`
- `cache_dir`

The API key value must stay in the environment and must not be committed.
