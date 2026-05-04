#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${1:-$(pwd)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
agents_template=""
agent_basics_template=""
LOCAL_EMBEDDING_PID=""
LOCAL_EMBEDDING_LOG=""

if [[ ! -d "$TARGET_DIR" ]]; then
  mkdir -p "$TARGET_DIR"
fi

cd "$TARGET_DIR"
TARGET_DIR="$(pwd)"
PROJECT_NAME="${AGENT_BASICS_PROJECT_NAME:-$(basename "$TARGET_DIR")}"
REPO_AGENTS_DIR="$TARGET_DIR/.agents"
REPO_MEMORY_ROOT="$REPO_AGENTS_DIR/memory"
REPO_OPENVIKING_DIR="$REPO_AGENTS_DIR/openviking"
REPO_BACKUPS_DIR="$REPO_AGENTS_DIR/backups"
REPO_MERGE_SESSIONS_DIR="$REPO_AGENTS_DIR/merge-sessions"
RAG_DIR="$REPO_MEMORY_ROOT/rag"
EMBEDDING_API_DIR="$RAG_DIR/embedding-api"

require_interactive() {
  local reason="$1"

  if [[ ! -t 0 ]]; then
    echo "Error: $reason" >&2
    echo "Run agent-basics in an interactive terminal or provide the required environment variables for this step." >&2
    exit 1
  fi
}

cleanup_setup() {
  if [[ -n "${LOCAL_EMBEDDING_PID:-}" ]]; then
    kill "$LOCAL_EMBEDDING_PID" >/dev/null 2>&1 || true
    wait "$LOCAL_EMBEDDING_PID" >/dev/null 2>&1 || true
  fi

  rm -f "${agents_template:-}" "${agent_basics_template:-}"
}

slugify() {
  local input="$1"
  local slug
  slug="$(printf "%s" "$input" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//')"
  if [[ -z "$slug" ]]; then
    slug="project"
  fi
  printf "%s\n" "$slug"
}

read_with_default() {
  local prompt="$1"
  local default_value="$2"
  local value

  require_interactive "$prompt"

  if [[ -n "$default_value" ]]; then
    read -r -p "$prompt [$default_value]: " value
    printf "%s\n" "${value:-$default_value}"
  else
    read -r -p "$prompt: " value
    printf "%s\n" "$value"
  fi
}

create_template_file() {
  local name="$1"
  local template_file

  template_file="$(mktemp "${TMPDIR:-/tmp}/agent-basics-$name.XXXXXX.md")"

  case "$name" in
    agents)
      cat > "$template_file" <<'EOT'
# Agent Base Instructions

## Protected Files

- **DO NOT**, unless explicitly instructed by the user, modify `Agents.md` or `.agents/AGENT-BASICS.md`.
- Follow `.agents/AGENT-BASICS.md` for agent-basics OpenViking, memory, documentation, setup, and repository workflow rules.

## Base Rules

- Be logical.
- For coding tasks, never use placeholders or omit required code in snippets.
- If you hit a character limit, stop abruptly; the user will send `continue`.
- Do not overlook critical context.
- If you have questions or concerns that block safe progress, clarify with the user immediately.

## Context First

- Treat OpenViking as the required target memory, documentation, resource, and skill backend for agent-basics repositories.
- Prefer the repo-aware agent-basics OpenViking gateway over direct OpenViking calls. Use `agent-basics mcp` and `agent-basics ov ...` commands for normal context work.
- Before answering a request that may depend on prior project context, search OpenViking through the agent-basics MCP tool or `agent-basics ov search "<query>"`.
- Anything the user asks you to remember must be recorded in OpenViking through the agent-basics MCP tool or `agent-basics ov record`.
- Add external documentation sources, reusable procedures, and agent skills to OpenViking through the agent-basics gateway when they matter for future work.
- The current `.agents/memory/` mini-RAG is fallback compatibility. Use it only when OpenViking tooling is unavailable and work must continue.
- If you must use the compatibility memory layer, call `.agents/memory/rag/memory-mcp.py` directly or fall back to `agent-basics memory ...` / `.agents/memory/rag/agent-memory.py ...`.
- Do not edit `.agents/memory/**` while `.agents/memory/rag/write.lock/` exists.

## Work Rules

- Before making codebase changes, write the concrete plan in `.agents/TODO.md` and follow it.
- For non-trivial or long-running work, preserve direction in `ROADMAP.md` and current state in `.agents/TODO.md`.
- Read a file fully before editing it.
- Keep comments rare and useful. Explain why or constraints, not obvious mechanics.
- Keep diffs narrow and task-focused.
- Do not guess at attribute names, control flow, or config behavior.
- Prefer fail-fast behavior over silent fallback logic.
- Add tests for new behavior unless the change is strictly docs/metadata cleanup.
- Tick off every completed item in `.agents/TODO.md`.
- After ticking off an item, commit the changes made for that item.
- Only stop working when everything in `.agents/TODO.md` is complete or you are blocked by something that requires user intervention.
- If everything is ticked off in `.agents/TODO.md` and a new work round is needed, clear it and write the new plan.

## Commits

- Set commit author name to `Coding agent supervised by {global git user.name}`, replacing `{global git user.name}` with `git config --global user.name`.
- Use the global git email unless the user explicitly instructs otherwise.
- Write commit messages as `{type}({scope}): {description}`.
- Use one of these commit types: `build`, `chore`, `CI`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test`.

## Answering Rules

Follow in this order:

1. Use the language of the user's message.
2. Search OpenViking or the compatibility memory layer before relying on assumptions about prior work.
3. Combine project context and clear reasoning to answer with concrete details.
4. Keep answers direct and actionable.
EOT
      ;;
    agent-basics)
      cat > "$template_file" <<'EOT'
# agent-basics Operating Manual

This file contains agent-basics-specific operating rules. `Agents.md` contains the base agent contract and must stay at the project root so agents discover it reliably.

## OpenViking Context Backend

- OpenViking is the required target backend for agent-basics memory, documentation, resources, skills, semantic organization, and retrieval.
- Agents should not call OpenViking with ad hoc commands when an agent-basics gateway exists. Use the repo-aware `agent-basics mcp` server or stable `agent-basics ov ...` commands.
- Repository-specific OpenViking metadata and locks should live under `.agents/openviking/`. The OpenViking package and workspace should live in a user-level installation, normally `~/.openviking`, not inside each repository.
- `agent-basics` owns setup, upgrade, validation, repo path resolution, git hooks, migration safety, and agent-facing command/MCP contracts.
- OpenViking owns durable context storage, resource ingestion, summaries, semantic search, and vector indexes.
- Before making context-dependent claims, search OpenViking through the gateway.
- Record durable decisions, facts, preferences, gotchas, events, documentation sources, procedures, and reusable skills through the gateway.
- Do not store secrets in OpenViking entries or agent-basics config. Store secret environment variable names only.

## Gateway Contract

The target agent-facing surfaces are:

- `agent-basics mcp`: repo-aware MCP server for OpenViking-backed tools.
- `agent-basics ov doctor`: check the user-level OpenViking installation, repo config, providers, ingest status, and health.
- `agent-basics ov install-system`: install OpenViking under `~/.openviking` when it is missing.
- `agent-basics ov write-default-config`: write a default `~/.openviking/ov.conf` for LM Studio Gemma 4 E2B plus EmbeddingGemma.
- `agent-basics ov import-repo-memory`: write `.agents/memory/` OV-native memories into OpenViking memory categories and ingest resources/skills.
- `agent-basics ov search <query>`: retrieve prior context for vague or specific project requests.
- `agent-basics ov record`: record durable context in the correct OpenViking category.
- `agent-basics ov add-resource <path-or-url>`: ingest documentation or reference material.
- `agent-basics ov add-skill <path>`: register reusable agent workflows.
- `agent-basics ov ingest-changed`: update OpenViking after source instructions, docs, or memory files change.
- `agent-basics ov install-hooks`: install repo-local hooks that refresh OpenViking after source-store changes.
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
- Environment variables: only provider secret variables named by `.agents/config.toml` or user-level OpenViking config
- Environment variable passthrough: the same provider secret variables, only when needed
- Working directory: absolute path to the repository root

## Transitional Compatibility

The current repository may contain the custom `.agents/memory/` markdown tree and generated mini-RAG for fallback compatibility.

Use this layer only when OpenViking tooling is unavailable:

- Prefer the OpenViking-backed `agent-basics mcp` server for normal work.
- Call `.agents/memory/rag/memory-mcp.py` directly only when the OpenViking gateway is unavailable.
- Let routine `memory_record` calls defer rebuilds.
- Call `memory_rebuild` once after a batch of memory changes, before relying on new entries in search, or before committing memory changes.
- If MCP is unavailable, use `agent-basics memory ...` or `.agents/memory/rag/agent-memory.py ...`.
- Keep `.agents/memory/INDEX.md` updated whenever adding, moving, or removing compatibility entries.
- Do not write `.agents/memory/**` while `.agents/memory/rag/write.lock/` exists.

Compatibility files are not the long-term architecture. When `agent-basics ov` and the OpenViking-backed MCP server are implemented, migrate useful compatibility memory into OpenViking and demote or remove the custom mini-RAG.

## Configuration

- Durable repo configuration belongs in `.agents/config.toml` and `.agents/openviking/` metadata files once those files exist. User-level OpenViking runtime configuration belongs under `~/.openviking`.
- Provider URLs, model names, timeouts, runtime paths, and feature flags should be stored in config files, not scattered through shell environment variables.
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
- Preserve useful handoff context in `.agents/TODO.md` or future `.agents/runs/<run-id>/` files when work may continue in another session.
- Long-horizon work state should route through `agent-basics run start/status/checkpoint/finish/handoff`.

## Skills And Stable Commands

- Skills should capture repeated workflows such as prework, memory update, finish work, documentation lookup, and verification.
- Skills should point to stable `agent-basics` commands so users can approve predictable command prefixes.
- Do not rely on optional client-side skills as the only source of baseline behavior. Root `Agents.md`, this operating manual, MCP tools, CLI checks, and git hooks remain the repo contract.

## Documentation Discipline

- Find up-to-date documentation for any library, framework, API, tool, or programming language used in the project.
- Record source URLs in OpenViking resources through `agent-basics ov add-resource` when the gateway exists.
- While the compatibility layer is still in use, record important sources under `.agents/memory/documentations/sources/`.
- While writing code, refer to recorded documentation sources before relying on memory for external APIs.
- Add a new source record when you consult a new external reference that matters for future work.
EOT
      ;;
    memory-schema)
      cat > "$template_file" <<'EOT'
# Memory Schema

`.agents/memory/` is the repo-owned source store for OpenViking-facing memory, resources, and skills.

OpenViking is the required runtime backend for durable memory, documentation resources, semantic organization, vector indexes, and retrieval. The files in this directory are project-owned source material that agents and setup tooling can inspect, adapt, ingest, and version-control. The OpenViking package, workspace, generated summaries, and vector database remain outside the repository unless the user explicitly configures otherwise.

## Directory Contract

```text
.agents/memory/
  SCHEMA.md
  INDEX.md
  ADAPTATION.md
  inbox/
  imports/
  memories/
    profile/
    preferences/
    entities/
    events/
    cases/
    patterns/
    tools/
    skills/
  resources/
    sources/
    procedures/
    references/
  skills/
  sessions/
```

## OpenViking Source Rules

- Every source entry should be markdown unless it is a resource file that needs to stay in its original format.
- Every entry must start with YAML front matter.
- Every entry must have `id`, `record_kind`, `ov_category`, `title`, `status`, `created`, `updated`, `tags`, and `summary`.
- Use Unix timestamp seconds for `created`, `updated`, and event timestamps.
- Keep one durable idea per file.
- Preserve source paths in `source_paths` when adapting legacy memory.
- Prefer short, searchable headings.
- Link related entries with relative paths.
- Record source URLs for external documentation.
- Do not store secrets.
- Use `requires_human_review: true` when a record is stale, transitional, conflicts with existing knowledge, or changes user intent.

## Record Kinds

- `memory`: durable user, project, system, tool, case, pattern, or skill knowledge for OpenViking memory.
- `resource`: documentation, references, source URLs, and other files that should be ingested as OpenViking resources.
- `skill`: reusable workflows that should be registered with OpenViking as skills.
- `ignore`: preserved migration material that should not be ingested.

## OpenViking Categories

- `profile`: stable user identity or attributes.
- `preferences`: what the user wants, prefers, dislikes, or habitually asks agents to do.
- `entities`: named things and stable attributes, including projects, systems, tools, repositories, people, organizations, and configured technologies.
- `events`: time-bound things that happened, are happening, or are planned.
- `cases`: specific problem, cause, solution, workaround, or outcome.
- `patterns`: reusable process or method for similar situations.
- `tools`: tool usage insights, parameters, success/failure patterns, and optimization.
- `skills`: reusable workflow or skill execution strategy.
- `none`: resources, ignored material, or records that should not become OpenViking memory.

## Adaptation Workflow

Agents adapting an existing project must follow `.agents/memory/ADAPTATION.md`.

High-level rules:

1. Copy existing memory/documentation material into `.agents/memory/imports/<unix-timestamp>-<source>/` or `.agents/openviking/legacy-memory/<unix-timestamp>/` before changing it.
2. Split durable material into one independently updatable idea per file under `memories/<ov_category>/`, `resources/`, or `skills/`.
3. Preserve provenance with `source_paths`.
4. Mark stale compatibility records with `requires_human_review: true` instead of silently importing them.
5. Ingest through `agent-basics ov ...` or the OpenViking-backed MCP gateway.
6. Verify with OpenViking retrieval before demoting legacy material.

Setup must not delete `.agents/memory/`. For fresh repositories, setup creates the OV source-store directories only. For older repositories, setup snapshots legacy compatibility directories such as `templates/`, `memory/`, `documentations/`, and `rag/` under `.agents/openviking/legacy-memory/<unix-timestamp>/` before agents adapt useful content into this schema.

## Transitional Compatibility

The older agent-basics compatibility mini-RAG used these legacy paths:

```text
.agents/memory/
  templates/
  memory/
  documentations/
  rag/
```

Those paths may still exist as compatibility fallback. They are compatibility input, not the target source-store shape. Compatibility writers must still respect `.agents/memory/rag/write.lock/` while the legacy mini-RAG is in use:

- Memory writers must wait while it exists.
- Indexers must create it before hashing, chunking, embedding, or replacing indexes.
- Indexers must remove it only after the generated index is consistent with source markdown.
- If the lock is stale because a process crashed, use a deliberate repair command rather than deleting it opportunistically.
EOT
      ;;
    memory-index)
      cat > "$template_file" <<'EOT'
# Memory Index

This index is maintained by agents and setup tooling. Update it whenever entries are added, moved, or removed.

## OpenViking Source Store

- [Schema](SCHEMA.md)
- [Adaptation guide](ADAPTATION.md)
- `memories/`: OV-native memory source records grouped by OpenViking category.
- `resources/`: documentation and references to ingest as OpenViking resources.
- `skills/`: reusable workflows to register as OpenViking skills.
- `imports/`: copied source material awaiting adaptation.

## Legacy Material

- `.agents/openviking/legacy-memory/`: preserved snapshots of older `.agents/memory/` compatibility trees.
- `imports/`: copied legacy markdown awaiting adaptation.
EOT
      ;;
    memory-adaptation)
      cat > "$template_file" <<'EOT'
# OpenViking Memory Adaptation Guide

Use this guide when converting existing project memory, documentation notes, agent instructions, or compatibility mini-RAG files into the `.agents/memory/` OpenViking source-store shape.

## Goal

The goal is not to preserve the old folder taxonomy. The goal is to preserve useful project knowledge as OpenViking-ready source material with clear provenance and one independently updatable idea per file.

## Required Steps

1. Inventory existing files before changing them.
2. Copy original material into `.agents/memory/imports/<unix-timestamp>-<source>/` or `.agents/openviking/legacy-memory/<unix-timestamp>/`.
3. Decide whether each item is `memory`, `resource`, `skill`, or `ignore`.
4. For memory records, choose one OpenViking category: `profile`, `preferences`, `entities`, `events`, `cases`, `patterns`, `tools`, or `skills`.
5. Split mixed records. Do not combine a user preference, project fact, tool gotcha, and dated event in one file.
6. Preserve `source_paths` and important related links.
7. Mark stale, transitional, or conflicting records with `requires_human_review: true`.
8. Ingest only reviewed or clearly safe records through `agent-basics ov ...` or the OpenViking-backed MCP gateway.
9. Run `ov wait` or the equivalent `agent-basics ov` command after ingest.
10. Verify representative queries with OpenViking retrieval before deleting, demoting, or ignoring legacy material.

Do not delete `.agents/memory/` during migration. That directory is the repo-specific OpenViking source store. Legacy compatibility directories inside it can stay temporarily, but their useful content should be snapshotted, adapted into `memories/`, `resources/`, or `skills/`, ingested into OpenViking, and only then demoted by an explicit cleanup step.

## Mapping Rules

- Legacy `preference` records usually become `record_kind: memory` and `ov_category: preferences`.
- Stable facts about projects, tools, repositories, or configuration usually become `entities`.
- Decisions and dated milestones usually become `events`.
- Gotchas, crashes, caveats, and workaround records usually become `cases`.
- Procedures usually become `patterns`, unless they are packaged as reusable OpenViking skills.
- Documentation source records and URL-only files become `record_kind: resource` and `ov_category: none`.
- Reusable agent workflows can become `record_kind: skill` and may also have an associated `skills` memory record summarizing when to use them.
- Compatibility-only instructions for retired tooling should be preserved as `ignore` or marked `requires_human_review: true`.

## Front Matter

Use this shape for adapted memory records:

```yaml
---
id: ov-memory-UNIXTIMESTAMP-short-name
record_kind: memory
ov_category: preferences
title: Short title
status: active
created: UNIX_TIMESTAMP
updated: UNIX_TIMESTAMP
tags: []
summary: One sentence summary.
source_paths: []
requires_human_review: false
---
```

Use `record_kind: resource` and `ov_category: none` for documentation resources. Use `record_kind: skill` for reusable workflows intended for OpenViking skill registration.

## Quality Bar

- Keep one idea per file.
- Prefer concrete, searchable wording over broad summaries.
- Do not store raw secrets.
- Do not erase user-specific preferences during cleanup.
- Do not treat stale compatibility machinery as active project direction.
- Record uncertainty explicitly instead of guessing.
EOT
      ;;
    template-decision)
      cat > "$template_file" <<'EOT'
---
id: decision-UNIXTIMESTAMP-short-name
type: decision
title: Short decision title
status: accepted
created: UNIX_TIMESTAMP
updated: UNIX_TIMESTAMP
tags: []
summary: One sentence summary.
---

# Short decision title

## Decision

Record the chosen direction.

## Rationale

Explain why this is the right choice.

## Consequences

List important follow-up constraints or tradeoffs.

## Related

- None.
EOT
      ;;
    template-fact)
      cat > "$template_file" <<'EOT'
---
id: fact-UNIXTIMESTAMP-short-name
type: fact
title: Short fact title
status: active
created: UNIX_TIMESTAMP
updated: UNIX_TIMESTAMP
tags: []
summary: One sentence summary.
---

# Short fact title

## Fact

Record the stable project fact.

## Evidence

Record how this is known.

## Related

- None.
EOT
      ;;
    template-preference)
      cat > "$template_file" <<'EOT'
---
id: preference-UNIXTIMESTAMP-short-name
type: preference
title: Short preference title
status: active
created: UNIX_TIMESTAMP
updated: UNIX_TIMESTAMP
tags: []
summary: One sentence summary.
---

# Short preference title

## Preference

Record the user or project preference.

## Scope

Record when this preference applies.

## Related

- None.
EOT
      ;;
    template-source)
      cat > "$template_file" <<'EOT'
---
id: source-UNIXTIMESTAMP-short-name
type: source
title: Documentation source title
status: active
created: UNIX_TIMESTAMP
updated: UNIX_TIMESTAMP
tags: []
summary: One sentence summary.
url: https://example.com
---

# Documentation source title

## Source

- URL: https://example.com
- Project/library/tool:
- Version or date checked:

## Notes

Record the relevant facts from this source in your own words.

## Related

- None.
EOT
      ;;
    template-procedure)
      cat > "$template_file" <<'EOT'
---
id: procedure-UNIXTIMESTAMP-short-name
type: procedure
title: Short procedure title
status: active
created: UNIX_TIMESTAMP
updated: UNIX_TIMESTAMP
tags: []
summary: One sentence summary.
---

# Short procedure title

## When To Use

Describe the trigger for this procedure.

## Steps

1. First concrete step.
2. Second concrete step.

## Verification

Describe how to confirm the procedure worked.

## Related

- None.
EOT
      ;;
    template-gotcha)
      cat > "$template_file" <<'EOT'
---
id: gotcha-UNIXTIMESTAMP-short-name
type: gotcha
title: Short gotcha title
status: active
created: UNIX_TIMESTAMP
updated: UNIX_TIMESTAMP
tags: []
summary: One sentence summary.
---

# Short gotcha title

## Problem

Describe the failure mode.

## Cause

Describe why it happens.

## Workaround

Describe the reliable way around it.

## Related

- None.
EOT
      ;;
    template-event)
      cat > "$template_file" <<'EOT'
---
id: event-UNIXTIMESTAMP-short-name
type: event
title: Short event title
status: recorded
created: UNIX_TIMESTAMP
updated: UNIX_TIMESTAMP
tags: []
summary: One sentence summary.
event_timestamp: UNIX_TIMESTAMP
---

# Short event title

## Event

Record what happened.

## Impact

Record why it matters later.

## Related

- None.
EOT
      ;;
    agent-basics-preference)
      cat > "$template_file" <<'EOT'
---
id: preference-1777507200-markdown-trailing-line
type: preference
title: Keep markdown files ending with an empty trailing line
status: active
created: 1777507200
updated: 1777507200
tags: [markdown, formatting]
summary: Markdown files should end with an empty trailing line.
---

# Keep markdown files ending with an empty trailing line

## Preference

Always keep markdown files ending with an empty trailing line.

## Scope

Applies to agent-basics markdown files and generated markdown templates.

## Related

- `.agents/memory/SCHEMA.md`
EOT
      ;;
    agent-basics-decision)
      cat > "$template_file" <<'EOT'
---
id: decision-1777766400-repo-local-memory-rag
type: decision
title: Use repo-local structured memory with generated RAG support as compatibility
status: superseded
created: 1777766400
updated: 1777827387
tags: [agent-basics, memory, rag, embeddings, compatibility]
summary: agent-basics keeps the custom markdown mini-RAG only as compatibility while OpenViking becomes the required backend.
---

# Use repo-local structured memory with generated RAG support as compatibility

## Decision

agent-basics used `.agents/memory/` as the canonical project-owned memory and documentation source tree.

This decision is now superseded by the OpenViking-backed harness direction. The `.agents/memory/` tree, generated RAG indexes, embedding databases, model caches, and local embedding APIs remain compatibility support until migration is implemented.

## Rationale

Structured markdown gave agents a predictable place to record durable context. A generated RAG layer helped with vague user requests and fuzzy recall without making a separate memory runtime the source of truth.

OpenViking overlaps with this custom layer and should own memory, resources, skills, semantic organization, and retrieval instead.

## Consequences

- Existing compatibility setup may still create the memory schema, templates, and directory layout.
- Compatibility setup may still validate an existing embedding API or install a repo-local HuggingFace embedding API.
- Compatibility RAG provider and runtime settings remain in `.agents/memory/rag/config.json`.
- Agents must wait when `.agents/memory/rag/write.lock/` exists while using the compatibility layer.
- Future OpenViking tooling should cite source records and keep repo-specific config under `.agents/`.

## Related

- `.agents/memory/memory/decisions/1777852800-make-agent-basics-an-openviking-backed-repo-harness.md`
- `.agents/memory/SCHEMA.md`
- `.agents/memory/rag/config.json`
EOT
      ;;
    agent-basics-doc-sources)
      cat > "$template_file" <<'EOT'
---
id: source-1777766400-agent-basics-documentation-sources
type: source
title: agent-basics documentation sources
status: active
created: 1777766400
updated: 1777827387
tags: [agent-basics, bash, git, homebrew, embeddings, mcp, rust, openviking]
summary: Source URLs used by agent-basics setup, packaging, embedding API, Rust binary, MCP, and OpenViking gateway work.
---

# agent-basics documentation sources

## Source Records

- Bash Reference Manual: https://www.gnu.org/software/bash/manual/
- Git `init` documentation: https://git-scm.com/docs/git-init
- Git `.gitignore` documentation: https://git-scm.com/docs/gitignore
- Homebrew Formula Cookbook: https://docs.brew.sh/Formula-Cookbook
- Homebrew Tap documentation: https://docs.brew.sh/How-to-Create-and-Maintain-a-Tap
- Homebrew Formula Ruby API: https://rubydoc.brew.sh/Formula
- Ruby documentation: https://www.ruby-lang.org/en/documentation/
- Rust standard library documentation: https://doc.rust-lang.org/std/
- The Cargo Book: https://doc.rust-lang.org/cargo/
- LM Studio OpenAI-compatible embeddings API: https://lmstudio.ai/docs/developer/openai-compat/embeddings
- LM Studio REST API model management: https://lmstudio.ai/docs/developer/rest
- LM Studio structured output API: https://lmstudio.ai/docs/app/api/structured-output
- LM Studio `lms load` CLI: https://lmstudio.ai/docs/cli/local-models/load
- SentenceTransformers documentation: https://sbert.net/
- FastAPI documentation: https://fastapi.tiangolo.com/
- MCP 2025-11-25 lifecycle specification: https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle
- MCP 2025-11-25 tools specification: https://modelcontextprotocol.io/specification/2025-11-25/server/tools
- MCP 2025-06-18 stdio transport specification: https://modelcontextprotocol.io/specification/2025-06-18/basic/transports
- MCP 2025-06-18 schema reference: https://modelcontextprotocol.io/specification/2025-06-18/schema
- OpenViking GitHub repository: https://github.com/volcengine/OpenViking

## Notes

Record additional source URLs here when setup behavior, local embedding service behavior, or packaging logic changes.

## Related

- `.agents/memory/SCHEMA.md`
- `.agents/memory/documentations/procedures/openviking-gateway.md`
- `.agents/memory/documentations/procedures/agent-memory-mcp.md`
- `.agents/memory/documentations/procedures/local-huggingface-embedding-api.md`
EOT
      ;;
    local-embedding-procedure)
      cat > "$template_file" <<'EOT'
---
id: procedure-1777766400-local-huggingface-embedding-api
type: procedure
title: Run the compatibility repo-local HuggingFace embedding API
status: compatibility
created: 1777766400
updated: 1777827387
tags: [embeddings, huggingface, rag, compatibility]
summary: Start the generated local embedding API when the compatibility mini-RAG was configured with a HuggingFace model.
---

# Run the compatibility repo-local HuggingFace embedding API

## When To Use

Use this when the transitional `.agents/memory/rag/config.json` has embedding provider `huggingface-local`. OpenViking provider setup should use the OpenViking gateway.

## Steps

1. From the repository root, run `.agents/memory/rag/embedding-api/start.sh`.
2. Keep that process running while agents need semantic memory retrieval.
3. Use the configured base URL from `.agents/memory/rag/config.json`, usually `http://127.0.0.1:8765/v1`.

## Verification

Call `/health`, `/v1/models`, or `/v1/embeddings` on the local service.

## Related

- `.agents/memory/documentations/procedures/openviking-gateway.md`
- `.agents/memory/rag/config.json`
- `.agents/memory/rag/embedding-api/README.md`
EOT
      ;;
    openviking-gateway-procedure)
      cat > "$template_file" <<'EOT'
---
id: procedure-1777827387-openviking-gateway
type: procedure
title: Use the agent-basics OpenViking gateway
status: active
created: 1777827387
updated: 1777919266
tags: [agent-basics, openviking, mcp, memory, resources, skills]
summary: Route agent memory, documentation, resource, and skill work through the repo-aware agent-basics OpenViking gateway.
---

# Use the agent-basics OpenViking gateway

## When To Use

Use this whenever an agent needs prior project context, durable memory recording, documentation/resource ingestion, reusable skill registration, or OpenViking health checks in an agent-basics repository.

## Steps

1. Resolve the repository root before calling the gateway.
2. Prefer `agent-basics mcp` when the agent client supports MCP.
3. Configure the MCP server with the repository root as the working directory.
4. Search prior context through the OpenViking-backed MCP search tool or `agent-basics ov search "<query>"` before answering vague or history-dependent requests.
5. Record durable decisions, facts, preferences, gotchas, events, procedures, and useful findings through the OpenViking-backed MCP record tool or `agent-basics ov record`.
6. Add important documentation or reference material with `agent-basics ov add-resource <path-or-url>`.
7. Add reusable workflows with `agent-basics ov add-skill <path>`.
8. After adapting repo memory, resources, or skills under `.agents/memory/`, run `agent-basics ov import-repo-memory --write`. OV-native memory files are written directly into their OpenViking memory categories; resources and skills use OpenViking ingestion.
9. After instruction, documentation, memory, or skill files change, run `agent-basics ov ingest-changed`.
10. Run `agent-basics ov doctor` before relying on OpenViking if setup, provider configuration, or ingest state is uncertain.

## Codex Desktop Configuration

In Settings -> MCP servers -> Connect to a custom MCP, use these fields:

- Name: `agent-basics`
- Transport: `STDIO`
- Command to launch: `agent-basics`
- Arguments: `mcp`
- Environment variables: only provider secret variables named by `.agents/config.toml` or user-level OpenViking config
- Environment variable passthrough: the same provider secret variables, only when needed
- Working directory: absolute path to the repository root

## Verification

Run `agent-basics ov doctor` or call the MCP doctor tool. The result should report user-level OpenViking installation, repo metadata, provider health, and ingest status.

## Related

- `Agents.md`
- `.agents/AGENT-BASICS.md`
- `ROADMAP.md`
EOT
      ;;
    agent-memory-mcp-procedure)
      cat > "$template_file" <<'EOT'
---
id: procedure-1777766400-agent-memory-mcp
type: procedure
title: Use the compatibility agent-basics memory MCP server
status: compatibility
created: 1777766400
updated: 1777827387
tags: [agent-basics, memory, rag, mcp, compatibility]
summary: Use `.agents/memory/rag/memory-mcp.py` only when the OpenViking gateway is unavailable.
---

# Use the compatibility agent-basics memory MCP server

## When To Use

Use this only when the OpenViking-backed `agent-basics mcp` or `agent-basics ov ...` gateway is unavailable and work must continue through the transitional `.agents/memory/` mini-RAG.

## Steps

1. Prefer the OpenViking gateway procedure first.
2. Configure the agent's MCP client to run the absolute repo-local `.agents/memory/rag/memory-mcp.py` path from the repository root.
3. Do not use `agent-basics mcp` for compatibility fallback; that command is the OpenViking-backed gateway.
4. Call `memory_search` before answering requests that depend on prior project context.
5. Call `memory_record` when the user asks to remember something or when a durable decision, fact, preference, gotcha, event, source, or procedure should be preserved before OpenViking migration.
6. Pass structured fields such as `rationale`, `consequences`, `notes`, `steps`, and `related` when they apply, so the recorder can generate polished markdown without manual edits.
7. Leave `no_rebuild` at its default `true` for routine records so writes do not call the embedding API every time.
8. Call `memory_rebuild` once after a batch of memory changes, before relying on new entries in search, or before committing.
9. Call `memory_validate` before committing memory changes.
10. Call `memory_doctor` to inspect layout, config, index freshness, and embedding endpoint health.

## Codex Desktop Configuration

In Settings -> MCP servers -> Connect to a custom MCP, use these fields when the OpenViking gateway is not available:

- Name: `agent-basics-memory`
- Transport: `STDIO`
- Command to launch: the absolute path to `.agents/memory/rag/memory-mcp.py`
- Arguments: none
- Environment variables: leave blank unless `.agents/memory/rag/config.json` names an API key variable in `embedding.api_key_env`
- Environment variable passthrough: same API key variable only when needed
- Working directory: absolute path to the repository root

## Verification

Send `initialize`, `tools/list`, and a `tools/call` request for `memory_doctor`. The compatibility server should return `memory_search`, `memory_record`, `memory_doctor`, `memory_rebuild`, and `memory_validate`.

## Related

- `.agents/memory/documentations/procedures/openviking-gateway.md`
- `.agents/memory/rag/memory-mcp.py`
- `.agents/memory/rag/agent-memory.py`
- `.agents/memory/SCHEMA.md`
EOT
      ;;
    agent-memory-cli-procedure)
      cat > "$template_file" <<'EOT'
---
id: procedure-1777766400-agent-memory-cli
type: procedure
title: Use the compatibility agent-basics memory CLI
status: compatibility
created: 1777766400
updated: 1777827387
tags: [agent-basics, memory, rag, cli, compatibility]
summary: Use `agent-basics memory` or `.agents/memory/rag/agent-memory.py` for fallback memory operations while OpenViking integration is unavailable.
---

# Use the compatibility agent-basics memory CLI

## When To Use

Use this when installing compatibility git hooks, repairing `.agents/memory/` manually, or when the OpenViking gateway and compatibility memory MCP server are unavailable.

## Steps

1. Prefer `agent-basics ov ...` or OpenViking-backed MCP tools when they exist.
2. Run `agent-basics memory validate` before committing compatibility memory changes when the systemwide command is installed, or `.agents/memory/rag/agent-memory.py validate` from a source checkout.
3. Run `agent-basics memory rebuild` after compatibility memory or documentation entries change.
4. Run `agent-basics memory search "<query>"` only as a fallback when OpenViking search and MCP `memory_search` are unavailable.
5. Run `agent-basics memory record <type> <title> --content "<content>" --no-rebuild` only as a fallback when OpenViking recording and MCP `memory_record` are unavailable.
6. Prefer structured fields such as `--rationale`, `--consequences`, `--notes`, `--steps`, and `--related` instead of patching generated memory markdown by hand.
7. Run `agent-basics memory install-hooks` to install compatibility local git hooks in a repo. Hooks validate memory before commit and warn when the generated index is stale; set `AGENT_BASICS_HOOK_AUTO_REBUILD=1` only when hook-triggered embedding calls are acceptable.

## Verification

Run `agent-basics memory doctor` to check compatibility layout, config, manifest, and index status. Add `--online` when the embedding API should be checked too.

## Related

- `.agents/memory/documentations/procedures/openviking-gateway.md`
- `.agents/memory/SCHEMA.md`
- `.agents/memory/rag/agent-memory.py`
- `.agents/memory/rag/memory-mcp.py`
EOT
      ;;
    *)
      echo "Error: unknown template name: $name" >&2
      exit 1
      ;;
  esac

  printf "%s\n" "$template_file"
}

create_memory_layout() {
  mkdir -p \
    "$REPO_OPENVIKING_DIR/legacy-memory" \
    "$REPO_OPENVIKING_DIR/locks" \
    "$REPO_BACKUPS_DIR" \
    "$REPO_MERGE_SESSIONS_DIR" \
    "$REPO_MEMORY_ROOT/inbox" \
    "$REPO_MEMORY_ROOT/imports" \
    "$REPO_MEMORY_ROOT/memories/profile" \
    "$REPO_MEMORY_ROOT/memories/preferences" \
    "$REPO_MEMORY_ROOT/memories/entities" \
    "$REPO_MEMORY_ROOT/memories/events" \
    "$REPO_MEMORY_ROOT/memories/cases" \
    "$REPO_MEMORY_ROOT/memories/patterns" \
    "$REPO_MEMORY_ROOT/memories/tools" \
    "$REPO_MEMORY_ROOT/memories/skills" \
    "$REPO_MEMORY_ROOT/resources/sources" \
    "$REPO_MEMORY_ROOT/resources/procedures" \
    "$REPO_MEMORY_ROOT/resources/references" \
    "$REPO_MEMORY_ROOT/skills" \
    "$REPO_MEMORY_ROOT/sessions"
}

create_compat_memory_layout() {
  mkdir -p \
    "$REPO_MEMORY_ROOT/templates" \
    "$REPO_MEMORY_ROOT/memory/decisions" \
    "$REPO_MEMORY_ROOT/memory/facts" \
    "$REPO_MEMORY_ROOT/memory/preferences" \
    "$REPO_MEMORY_ROOT/memory/gotchas" \
    "$REPO_MEMORY_ROOT/memory/events" \
    "$REPO_MEMORY_ROOT/documentations/sources" \
    "$REPO_MEMORY_ROOT/documentations/procedures" \
    "$REPO_MEMORY_ROOT/documentations/references" \
    "$RAG_DIR"
}

compat_memory_enabled() {
  case "${AGENT_BASICS_INSTALL_COMPAT_MEMORY:-0}" in
    1|true|TRUE|yes|YES|on|ON)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

snapshot_existing_legacy_memory() {
  local timestamp
  local snapshot_root
  local legacy_path
  local found=0
  local existing_snapshot_count=0
  local -a legacy_dirs
  local -a rag_files

  if [[ ! -d "$REPO_MEMORY_ROOT" ]]; then
    return
  fi

  legacy_dirs=("templates" "memory" "documentations")
  for legacy_path in "${legacy_dirs[@]}"; do
    if [[ -e "$REPO_MEMORY_ROOT/$legacy_path" ]]; then
      found=1
    fi
  done
  if [[ -d "$RAG_DIR" ]]; then
    found=1
  fi

  if [[ "$found" -ne 1 ]]; then
    return
  fi

  if [[ -d "$REPO_OPENVIKING_DIR/legacy-memory" ]]; then
    existing_snapshot_count="$(find "$REPO_OPENVIKING_DIR/legacy-memory" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')"
  fi
  if [[ "$existing_snapshot_count" -gt 0 && "${AGENT_BASICS_FORCE_LEGACY_MEMORY_SNAPSHOT:-0}" != "1" ]]; then
    echo "Legacy memory snapshot already exists under .agents/openviking/legacy-memory/"
    return
  fi

  timestamp="$(date -u +%s)"
  snapshot_root="$REPO_OPENVIKING_DIR/legacy-memory/$timestamp"
  mkdir -p "$snapshot_root"

  for legacy_path in "${legacy_dirs[@]}"; do
    if [[ -e "$REPO_MEMORY_ROOT/$legacy_path" ]]; then
      cp -R "$REPO_MEMORY_ROOT/$legacy_path" "$snapshot_root/$legacy_path"
    fi
  done

  if [[ -d "$RAG_DIR" ]]; then
    mkdir -p "$snapshot_root/rag"
    rag_files=("agent-memory.py" "memory-mcp.py" "config.json" "config.example.json" "embedding.json" "README.md")
    for legacy_path in "${rag_files[@]}"; do
      if [[ -f "$RAG_DIR/$legacy_path" ]]; then
        cp "$RAG_DIR/$legacy_path" "$snapshot_root/rag/$legacy_path"
      fi
    done
  fi

  cat > "$snapshot_root/manifest.json" <<EOT
{
  "created": $timestamp,
  "source": ".agents/memory",
  "reason": "Preserve legacy agent-basics memory material before adapting the repo to the OpenViking source-store layout.",
  "excluded_generated_files": [
    ".agents/memory/rag/index.sqlite",
    ".agents/memory/rag/manifest.json",
    ".agents/memory/rag/write.lock",
    ".agents/memory/rag/embedding-api/venv",
    ".agents/memory/rag/embedding-api/models"
  ]
}
EOT

  echo "Snapshotted legacy memory material: .agents/openviking/legacy-memory/$timestamp"
}

backup_existing_file() {
  local file_path="$1"
  local timestamp
  local backup_name
  timestamp="$(date +%s)"
  backup_name="${file_path//\//__}.$timestamp.bak"

  mkdir -p "$REPO_BACKUPS_DIR"
  cp "$file_path" "$REPO_BACKUPS_DIR/$backup_name"
  echo "Backed up existing file: .agents/backups/$backup_name"
}

create_empty_file_if_missing() {
  local file_path="$1"

  if [[ -e "$file_path" ]]; then
    echo "Exists: $file_path"
    return
  fi

  : > "$file_path"
  echo "Created: $file_path"
}

ensure_trailing_blank_line() {
  local file_path="$1"

  if [[ ! -f "$file_path" ]]; then
    return
  fi

  if [[ ! -s "$file_path" ]]; then
    printf "\n" > "$file_path"
    return
  fi

  if [[ -n "$(tail -c 1 "$file_path" 2>/dev/null)" ]]; then
    printf "\n" >> "$file_path"
  fi

  if [[ -n "$(tail -n 1 "$file_path")" ]]; then
    printf "\n" >> "$file_path"
  fi
}

markdown_files_equivalent() {
  local left_path="$1"
  local right_path="$2"

  python3 - "$left_path" "$right_path" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path


def normalize(path: str) -> str:
    text = Path(path).read_text(encoding="utf-8")
    return text.rstrip("\n") + "\n\n"


sys.exit(0 if normalize(sys.argv[1]) == normalize(sys.argv[2]) else 1)
PY
}

print_conflict_options() {
  local file_path="$1"

  cat <<EOT
$file_path already exists and differs from the agent-basics template.
Choose how to handle it:
  k  keep the existing file unchanged
  r  replace it with the agent-basics template after creating a backup
  a  append the agent-basics template after creating a backup
  m  manually merge both versions in \$EDITOR after creating a backup
  w  use the local web merge UI after creating a backup
  s  save the agent-basics template beside the existing file as $file_path.agent-basics.new
EOT
}

prompt_conflict_action() {
  local file_path="$1"
  local choice

  require_interactive "$file_path conflicts with the agent-basics template, and stdin is not interactive."

  while true; do
    print_conflict_options "$file_path" >&2
    read -r -p "Selection [k/r/a/m/w/s]: " choice
    case "$choice" in
      k|K) printf "k\n"; return ;;
      r|R) printf "r\n"; return ;;
      a|A) printf "a\n"; return ;;
      m|M) printf "m\n"; return ;;
      w|W) printf "w\n"; return ;;
      s|S) printf "s\n"; return ;;
      *) echo "Invalid choice: $choice" >&2 ;;
    esac
  done
}

manual_merge_file() {
  local source_path="$1"
  local destination_path="$2"
  local merge_file
  local editor
  local apply_choice

  merge_file="$REPO_MERGE_SESSIONS_DIR/$(basename "$destination_path").$(date +%s).md"
  editor="${EDITOR:-vi}"
  mkdir -p "$(dirname "$merge_file")"

  {
    printf "<<<<<<< existing: %s\n" "$destination_path"
    cat "$destination_path"
    printf "\n======= agent-basics template: %s\n" "$source_path"
    cat "$source_path"
    printf "\n>>>>>>> agent-basics template\n"
  } > "$merge_file"

  echo "Opening merge draft in $editor: $merge_file"
  "$editor" "$merge_file"

  while true; do
    read -r -p "Apply merged content to $destination_path? [y/n]: " apply_choice
    case "$apply_choice" in
      y|Y)
        backup_existing_file "$destination_path"
        cp "$merge_file" "$destination_path"
        echo "Applied manual merge: $destination_path"
        return
        ;;
      n|N)
        echo "Kept existing file unchanged. Merge draft remains at: $merge_file"
        return
        ;;
      *)
        echo "Invalid choice: $apply_choice"
        ;;
    esac
  done
}

web_merge_file() {
  local source_path="$1"
  local destination_path="$2"
  local merge_file
  local server_script
  local apply_choice

  require_interactive "$destination_path needs an interactive terminal for the web merge UI."

  merge_file="$REPO_MERGE_SESSIONS_DIR/$(basename "$destination_path").$(date +%s).web.md"
  server_script="$(mktemp "${TMPDIR:-/tmp}/agent-basics-web-merge.XXXXXX.py")"
  mkdir -p "$(dirname "$merge_file")"

  cat > "$server_script" <<'PY'
from __future__ import annotations

import html
import json
import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


source_path = Path(sys.argv[1])
destination_path = Path(sys.argv[2])
merge_path = Path(sys.argv[3])

existing_text = destination_path.read_text(encoding="utf-8") if destination_path.exists() else ""
proposed_text = source_path.read_text(encoding="utf-8")


def page() -> bytes:
    payload = {
        "file": str(destination_path),
        "existing": existing_text.splitlines(),
        "proposed": proposed_text.splitlines(),
    }
    data = json.dumps(payload)
    title = html.escape(str(destination_path))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>agent-basics markdown merge</title>
<style>
:root {{
  color-scheme: light;
  --border: #c9ced6;
  --text: #172033;
  --muted: #5e6a7d;
  --same: #dff5e6;
  --diff: #ffe0e0;
  --picked: #e5edff;
  --panel: #f8fafc;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: var(--text);
  background: white;
}}
header {{
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}}
h1 {{ margin: 0; font-size: 18px; }}
header span {{ color: var(--muted); font-size: 13px; }}
button {{
  border: 1px solid var(--border);
  background: white;
  border-radius: 6px;
  padding: 7px 10px;
  cursor: pointer;
}}
button.primary {{ background: #1f5eff; color: white; border-color: #1f5eff; }}
.toolbar {{ display: flex; gap: 8px; flex-wrap: wrap; }}
.grid {{
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr) minmax(0, 1fr);
  gap: 12px;
  padding: 12px;
}}
.panel {{
  min-height: 70vh;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--panel);
  overflow: hidden;
}}
.panel h2 {{
  margin: 0;
  padding: 10px 12px;
  font-size: 14px;
  border-bottom: 1px solid var(--border);
  background: white;
}}
.list {{ padding: 8px; max-height: 68vh; overflow: auto; }}
.row {{
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 8px;
  align-items: start;
  margin-bottom: 6px;
  padding: 7px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: white;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  white-space: pre-wrap;
}}
.row.same {{ background: var(--same); }}
.row.diff {{ background: var(--diff); }}
.row.picked {{ background: var(--picked); }}
.line-no {{ color: var(--muted); user-select: none; }}
.row-actions {{ display: flex; gap: 4px; }}
.row-actions button {{ padding: 2px 6px; }}
textarea {{
  width: 100%;
  min-height: 300px;
  padding: 10px;
  resize: vertical;
  border: 0;
  border-top: 1px solid var(--border);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
}}
.status {{ padding: 0 20px 14px; color: var(--muted); font-size: 13px; }}
@media (max-width: 980px) {{
  .grid {{ grid-template-columns: 1fr; }}
  .panel {{ min-height: auto; }}
}}
</style>
</head>
<body>
<header>
  <div>
    <h1>agent-basics markdown merge</h1>
    <span>{title}</span>
  </div>
  <div class="toolbar">
    <button id="use-existing">Use existing</button>
    <button id="use-proposed">Use agent-basics</button>
    <button id="clear">Clear</button>
    <button class="primary" id="save">Save merge draft</button>
  </div>
</header>
<main class="grid">
  <section class="panel">
    <h2>Existing project</h2>
    <div class="list" id="existing"></div>
  </section>
  <section class="panel">
    <h2>Final ordered file</h2>
    <div class="list" id="final"></div>
    <textarea id="preview" spellcheck="false"></textarea>
  </section>
  <section class="panel">
    <h2>agent-basics proposed</h2>
    <div class="list" id="proposed"></div>
  </section>
</main>
<div class="status" id="status">Pick lines from either side, reorder with arrows, edit the preview if needed, then save.</div>
<script>
const data = {data};
const same = new Set(data.existing.filter((line) => data.proposed.includes(line)));
let selected = data.proposed.map((text, index) => ({{ text, source: 'proposed', id: `${{index}}-proposed-${{Math.random()}}` }}));

function rowClass(text, picked = false) {{
  if (picked) return 'row picked';
  return same.has(text) ? 'row same' : 'row diff';
}}

function makeRow(text, index, source) {{
  const row = document.createElement('div');
  row.className = rowClass(text);
  const number = document.createElement('span');
  number.className = 'line-no';
  number.textContent = String(index + 1).padStart(3, ' ');
  const body = document.createElement('span');
  body.textContent = text || ' ';
  const actions = document.createElement('span');
  actions.className = 'row-actions';
  const add = document.createElement('button');
  add.type = 'button';
  add.textContent = '+';
  add.title = 'Add line to final file';
  add.addEventListener('click', () => {{
    selected.push({{ text, source, id: `${{Date.now()}}-${{Math.random()}}` }});
    render();
  }});
  actions.append(add);
  row.append(number, body, actions);
  return row;
}}

function makeFinalRow(item, index) {{
  const row = document.createElement('div');
  row.className = rowClass(item.text, true);
  const number = document.createElement('span');
  number.className = 'line-no';
  number.textContent = String(index + 1).padStart(3, ' ');
  const body = document.createElement('span');
  body.textContent = item.text || ' ';
  const actions = document.createElement('span');
  actions.className = 'row-actions';
  const up = document.createElement('button');
  up.type = 'button';
  up.textContent = 'up';
  up.disabled = index === 0;
  up.addEventListener('click', () => {{
    [selected[index - 1], selected[index]] = [selected[index], selected[index - 1]];
    render();
  }});
  const down = document.createElement('button');
  down.type = 'button';
  down.textContent = 'down';
  down.disabled = index === selected.length - 1;
  down.addEventListener('click', () => {{
    [selected[index + 1], selected[index]] = [selected[index], selected[index + 1]];
    render();
  }});
  const remove = document.createElement('button');
  remove.type = 'button';
  remove.textContent = 'x';
  remove.addEventListener('click', () => {{
    selected.splice(index, 1);
    render();
  }});
  actions.append(up, down, remove);
  row.append(number, body, actions);
  return row;
}}

function render() {{
  const existing = document.querySelector('#existing');
  const proposed = document.querySelector('#proposed');
  const final = document.querySelector('#final');
  existing.replaceChildren(...data.existing.map((line, index) => makeRow(line, index, 'existing')));
  proposed.replaceChildren(...data.proposed.map((line, index) => makeRow(line, index, 'proposed')));
  final.replaceChildren(...selected.map(makeFinalRow));
  document.querySelector('#preview').value = selected.map((item) => item.text).join('\\n') + '\\n';
}}

document.querySelector('#use-existing').addEventListener('click', () => {{
  selected = data.existing.map((text, index) => ({{ text, source: 'existing', id: `${{index}}-existing-${{Math.random()}}` }}));
  render();
}});
document.querySelector('#use-proposed').addEventListener('click', () => {{
  selected = data.proposed.map((text, index) => ({{ text, source: 'proposed', id: `${{index}}-proposed-${{Math.random()}}` }}));
  render();
}});
document.querySelector('#clear').addEventListener('click', () => {{
  selected = [];
  render();
}});
document.querySelector('#preview').addEventListener('input', (event) => {{
  selected = event.target.value.replace(/\\n$/, '').split('\\n').map((text, index) => ({{ text, source: 'preview', id: `${{index}}-preview-${{Math.random()}}` }}));
  document.querySelector('#final').replaceChildren(...selected.map(makeFinalRow));
}});
document.querySelector('#save').addEventListener('click', async () => {{
  const response = await fetch('/save', {{ method: 'POST', body: document.querySelector('#preview').value }});
  const text = await response.text();
  document.querySelector('#status').textContent = text;
}});
render();
</script>
</body>
</html>
""".encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        if self.path != "/":
            self.send_response(404)
            self.end_headers()
            return
        content = page()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        if self.path != "/save":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        content = self.rfile.read(length).decode("utf-8")
        merge_path.parent.mkdir(parents=True, exist_ok=True)
        if content and not content.endswith("\n\n"):
            content = content.rstrip("\n") + "\n\n"
        merge_path.write_text(content, encoding="utf-8")
        body = f"Saved merge draft to {merge_path}. You can return to the terminal.".encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        threading.Thread(target=self.server.shutdown, daemon=True).start()


server = HTTPServer(("127.0.0.1", 0), Handler)
url = f"http://127.0.0.1:{server.server_address[1]}/"
print(f"Open the merge UI: {url}", flush=True)
if os.environ.get("AGENT_BASICS_OPEN_MERGE_UI", "1") != "0":
    webbrowser.open(url)
server.serve_forever()
PY

  python3 "$server_script" "$source_path" "$destination_path" "$merge_file"
  rm -f "$server_script"

  if [[ ! -s "$merge_file" ]]; then
    echo "No merge draft was saved. Existing file remains unchanged."
    return
  fi

  while true; do
    read -r -p "Apply web merge draft to $destination_path? [y/n]: " apply_choice
    case "$apply_choice" in
      y|Y)
        backup_existing_file "$destination_path"
        cp "$merge_file" "$destination_path"
        echo "Applied web merge: $destination_path"
        return
        ;;
      n|N)
        echo "Kept existing file unchanged. Merge draft remains at: $merge_file"
        return
        ;;
      *)
        echo "Invalid choice: $apply_choice"
        ;;
    esac
  done
}

copy_or_merge_markdown_file() {
  local source_path="$1"
  local destination_path="$2"
  local action

  mkdir -p "$(dirname "$destination_path")"

  if [[ ! -e "$destination_path" ]]; then
    cp "$source_path" "$destination_path"
    echo "Created: $destination_path"
    return
  fi

  if [[ ! -s "$destination_path" ]]; then
    cp "$source_path" "$destination_path"
    echo "Updated empty file: $destination_path"
    return
  fi

  if cmp -s "$source_path" "$destination_path" || markdown_files_equivalent "$source_path" "$destination_path"; then
    ensure_trailing_blank_line "$destination_path"
    echo "No changes: $destination_path already matches the template"
    return
  fi

  action="$(prompt_conflict_action "$destination_path")"
  case "$action" in
    k)
      echo "Kept existing file: $destination_path"
      ;;
    r)
      backup_existing_file "$destination_path"
      cp "$source_path" "$destination_path"
      echo "Replaced with template: $destination_path"
      ;;
    a)
      backup_existing_file "$destination_path"
      ensure_trailing_blank_line "$destination_path"
      {
        printf "<!-- agent-basics template appended at Unix timestamp %s -->\n\n" "$(date -u +%s)"
        cat "$source_path"
      } >> "$destination_path"
      echo "Appended template: $destination_path"
      ;;
    m)
      manual_merge_file "$source_path" "$destination_path"
      ;;
    w)
      web_merge_file "$source_path" "$destination_path"
      ;;
    s)
      cp "$source_path" "$destination_path.agent-basics.new"
      echo "Saved incoming template: $destination_path.agent-basics.new"
      ;;
  esac
}

seed_agent_basics_from_legacy_instructions() {
  if [[ -f ".agents/INSTRUCTIONS.md" && ! -e ".agents/AGENT-BASICS.md" ]]; then
    cp ".agents/INSTRUCTIONS.md" ".agents/AGENT-BASICS.md"
    echo "Seeded .agents/AGENT-BASICS.md from legacy .agents/INSTRUCTIONS.md"
  fi
}

copy_memory_template_if_missing() {
  local template_name="$1"
  local destination_path="$2"
  local source_path

  source_path="$(create_template_file "$template_name")"
  copy_or_merge_markdown_file "$source_path" "$destination_path"
  rm -f "$source_path"
}

migrate_legacy_markdown_if_missing() {
  local source_path="$1"
  local destination_path="$2"
  local entry_type="$3"
  local title="$4"
  local summary="$5"
  local tags="$6"
  local timestamp

  if [[ ! -f "$source_path" || -f "$destination_path" ]]; then
    return
  fi

  timestamp="$(date -u +%s)"
  mkdir -p "$(dirname "$destination_path")"

  {
    printf -- "---\n"
    printf "id: ov-import-%s-%s-legacy\n" "$timestamp" "$(slugify "$PROJECT_NAME")"
    printf "record_kind: ignore\n"
    printf "ov_category: none\n"
    printf "title: %s\n" "$title"
    printf "status: imported\n"
    printf "created: %s\n" "$timestamp"
    printf "updated: %s\n" "$timestamp"
    printf "tags: %s\n" "$tags"
    printf "summary: %s\n" "$summary"
    printf "source_paths: [\"%s\"]\n" "$source_path"
    printf "requires_human_review: true\n"
    printf -- "---\n\n"
    printf "# %s\n\n" "$title"
    printf "## Legacy Content\n\n"
    cat "$source_path"
    printf "\n"
  } > "$destination_path"

  echo "Migrated legacy markdown: $source_path -> $destination_path"
}

write_repo_openviking_metadata_if_missing() {
  local repo_metadata="$REPO_OPENVIKING_DIR/repo.json"
  local timestamp

  if [[ -f "$repo_metadata" ]]; then
    echo "Exists: .agents/openviking/repo.json"
    return
  fi

  timestamp="$(date -u +%s)"
  mkdir -p "$REPO_OPENVIKING_DIR"
  python3 - "$repo_metadata" "$timestamp" "$PROJECT_NAME" <<'PY'
from __future__ import annotations

import json
import sys

path, timestamp, project_name = sys.argv[1:]
payload = {
    "version": 1,
    "created": int(timestamp),
    "updated": int(timestamp),
    "project_name": project_name,
    "memory_source": ".agents/memory",
    "legacy_snapshots": ".agents/openviking/legacy-memory",
    "runtime_home": "~/.openviking",
    "notes": (
        "Repository-specific source material stays here; OpenViking runtime data and indexes stay in "
        "the user-level OpenViking home unless explicitly configured otherwise."
    ),
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY
  echo "Created: .agents/openviking/repo.json"
}

write_repo_config_if_missing() {
  local repo_config="$REPO_AGENTS_DIR/config.toml"
  local timestamp
  local repo_slug

  if [[ -f "$repo_config" ]]; then
    echo "Exists: .agents/config.toml"
    return
  fi

  timestamp="$(date -u +%s)"
  repo_slug="$(slugify "$PROJECT_NAME")"
  mkdir -p "$REPO_AGENTS_DIR"
  python3 - "$repo_config" "$timestamp" "$repo_slug" "$TARGET_DIR" <<'PY'
from __future__ import annotations

import json
import sys


path, timestamp, repo_slug, target_dir = sys.argv[1:]


def quote(value: str) -> str:
    return json.dumps(value)


with open(path, "w", encoding="utf-8") as handle:
    handle.write("version = 1\n")
    handle.write(f"generated_at = {int(timestamp)}\n")
    handle.write(f"repo_slug = {quote(repo_slug)}\n\n")
    handle.write("[openviking]\n")
    handle.write("enabled = true\n")
    handle.write("required = true\n")
    handle.write('source_store_path = ".agents/memory"\n\n')
    handle.write("[openviking.mcp]\n")
    handle.write('command = "agent-basics"\n')
    handle.write('args = ["mcp"]\n')
    handle.write(f"cwd = {quote(target_dir)}\n")
PY
  echo "Created: .agents/config.toml"
}

write_repo_mcp_config_snippets() {
  local codex_snippet="$REPO_OPENVIKING_DIR/codex-mcp.json"

  mkdir -p "$REPO_OPENVIKING_DIR"
  python3 - "$codex_snippet" "$TARGET_DIR" <<'PY'
from __future__ import annotations

import json
import sys

path, target_dir = sys.argv[1:]
payload = {
    "mcpServers": {
        "agent-basics": {
            "command": "agent-basics",
            "args": ["mcp"],
            "cwd": target_dir,
        }
    }
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY
  echo "Wrote MCP config snippet: .agents/openviking/codex-mcp.json"
}

openviking_cli_is_valid() {
  local ov_bin="$1"

  [[ -x "$ov_bin" ]] && "$ov_bin" --help >/dev/null 2>&1
}

find_agent_basics_dispatcher() {
  local candidate

  # Tests use a fake dispatcher so setup does not perform network installs.
  if [[ -n "${AGENT_BASICS_TEST_OPENVIKING_INSTALL_DISPATCHER:-}" ]]; then
    if [[ -x "$AGENT_BASICS_TEST_OPENVIKING_INSTALL_DISPATCHER" ]]; then
      printf "%s\n" "$AGENT_BASICS_TEST_OPENVIKING_INSTALL_DISPATCHER"
      return 0
    fi
    return 1
  fi

  for candidate in "$SCRIPT_DIR/agent-basics"; do
    if [[ -x "$candidate" ]]; then
      printf "%s\n" "$candidate"
      return 0
    fi
  done

  candidate="$(command -v agent-basics 2>/dev/null || true)"
  if [[ -n "$candidate" && -x "$candidate" ]]; then
    printf "%s\n" "$candidate"
    return 0
  fi

  return 1
}

install_or_repair_user_openviking() {
  local ov_bin="$1"
  local ov_home="$2"
  local mode="$3"
  local dispatcher
  local choice
  local -a install_args

  if ! dispatcher="$(find_agent_basics_dispatcher)"; then
    echo "Error: user-level OpenViking $mode is required, but no executable agent-basics dispatcher was found." >&2
    echo "Expected an executable dispatcher next to setup-macos.sh or on PATH as: agent-basics" >&2
    echo "Install or repair agent-basics, then run: agent-basics ov install-system --home \"$ov_home\"" >&2
    exit 1
  fi

  install_args=(ov install-system --home "$ov_home")
  if [[ "$mode" == "repair" ]]; then
    install_args+=(--force)
  fi

  if [[ "${AGENT_BASICS_TEST_OPENVIKING_AUTO_INSTALL:-0}" == "1" && -n "${AGENT_BASICS_TEST_OPENVIKING_INSTALL_DISPATCHER:-}" ]]; then
    echo "Running test-only OpenViking $mode via fake dispatcher: $dispatcher"
  else
    if [[ ! -t 0 ]]; then
      echo "Error: user-level OpenViking $mode is required, but setup is not running interactively." >&2
      echo "Expected executable: $ov_bin" >&2
      echo "Run setup in an interactive terminal, or run this first:" >&2
      echo "  $dispatcher ov install-system --home \"$ov_home\"" >&2
      exit 1
    fi

    printf "User-level OpenViking %s is required at %s. Run '%s ov install-system --home \"%s\"' now? [y/N]: " \
      "$mode" "$ov_bin" "$dispatcher" "$ov_home" >&2
    read -r choice
    case "$choice" in
      y|Y|yes|YES)
        ;;
      *)
        echo "Error: user-level OpenViking $mode was declined." >&2
        echo "Install or repair OpenViking with: $dispatcher ov install-system --home \"$ov_home\"" >&2
        exit 1
        ;;
    esac
  fi

  if ! "$dispatcher" "${install_args[@]}"; then
    echo "Error: OpenViking $mode command failed: $dispatcher ${install_args[*]}" >&2
    exit 1
  fi

  if ! openviking_cli_is_valid "$ov_bin"; then
    echo "Error: OpenViking $mode completed, but the CLI still failed verification." >&2
    echo "Expected executable: $ov_bin" >&2
    exit 1
  fi
}

verify_user_openviking_installation() {
  local ov_bin
  local ov_home

  # Test-only escapes keep unit tests independent of the developer machine.
  case "${AGENT_BASICS_TEST_SKIP_OPENVIKING_CHECK:-0}" in
    1)
      echo "Skipped user-level OpenViking verification via AGENT_BASICS_TEST_SKIP_OPENVIKING_CHECK (tests only)."
      return
      ;;
  esac

  if [[ -n "${AGENT_BASICS_TEST_OPENVIKING_BIN:-}" ]]; then
    ov_bin="$AGENT_BASICS_TEST_OPENVIKING_BIN"
  else
    if [[ -z "${HOME:-}" ]]; then
      echo "Error: HOME is required to locate the user-level OpenViking installation." >&2
      exit 1
    fi
    ov_home="$HOME/.openviking"
    ov_bin="$ov_home/venv/bin/ov"
  fi

  if openviking_cli_is_valid "$ov_bin"; then
    echo "Verified user-level OpenViking CLI: $ov_bin"
    return
  fi

  if [[ -n "${AGENT_BASICS_TEST_OPENVIKING_BIN:-}" ]]; then
    echo "Error: user-level OpenViking installation was not found." >&2
    echo "Expected executable: $ov_bin" >&2
    echo "Install or repair OpenViking with: agent-basics ov install-system" >&2
    exit 1
  fi

  if [[ ! -x "$ov_bin" ]]; then
    install_or_repair_user_openviking "$ov_bin" "$ov_home" "installation"
  else
    install_or_repair_user_openviking "$ov_bin" "$ov_home" "repair"
  fi

  echo "Verified user-level OpenViking CLI: $ov_bin"
}

append_gitignore_entry_if_missing() {
  local entry="$1"

  if [[ ! -e ".gitignore" ]]; then
    printf "%s\n" "$entry" > .gitignore
    echo "Created: .gitignore"
    return
  fi

  if grep -Fxq "$entry" .gitignore; then
    echo "No changes: .gitignore already contains $entry"
  else
    printf "\n%s\n" "$entry" >> .gitignore
    echo "Appended entry to .gitignore: $entry"
  fi
}

find_memory_tool_source() {
  local candidate
  local -a candidates

  candidates=(
    "$SCRIPT_DIR/agent-memory.py"
    "$SCRIPT_DIR/.agents/memory/rag/agent-memory.py"
  )

  for candidate in "${candidates[@]}"; do
    if [[ -f "$candidate" ]]; then
      printf "%s\n" "$candidate"
      return 0
    fi
  done

  return 1
}

find_memory_mcp_source() {
  local candidate
  local -a candidates

  candidates=(
    "$SCRIPT_DIR/memory-mcp.py"
    "$SCRIPT_DIR/.agents/memory/rag/memory-mcp.py"
  )

  for candidate in "${candidates[@]}"; do
    if [[ -f "$candidate" ]]; then
      printf "%s\n" "$candidate"
      return 0
    fi
  done

  return 1
}

write_memory_tool_files() {
  local source_path
  local mcp_source_path
  local source_abs
  local mcp_source_abs
  local target_path
  local mcp_target_path
  local target_abs
  local mcp_target_abs

  if ! source_path="$(find_memory_tool_source)"; then
    echo "Error: bundled agent-memory.py was not found next to setup-macos.sh." >&2
    echo "Run setup from the full agent-basics checkout or install through the Homebrew formula." >&2
    exit 1
  fi
  if ! mcp_source_path="$(find_memory_mcp_source)"; then
    echo "Error: bundled memory-mcp.py was not found next to setup-macos.sh." >&2
    echo "Run setup from the full agent-basics checkout or install through the Homebrew formula." >&2
    exit 1
  fi

  mkdir -p "$RAG_DIR"
  target_path="$RAG_DIR/agent-memory.py"
  source_abs="$(cd "$(dirname "$source_path")" && pwd -P)/$(basename "$source_path")"
  target_abs="$(cd "$(dirname "$target_path")" && pwd -P)/$(basename "$target_path")"
  if [[ "$source_abs" != "$target_abs" ]]; then
    cp "$source_path" "$target_path"
  fi
  chmod 0755 "$target_path"
  echo "Installed memory CLI: .agents/memory/rag/agent-memory.py"

  mcp_target_path="$RAG_DIR/memory-mcp.py"
  mcp_source_abs="$(cd "$(dirname "$mcp_source_path")" && pwd -P)/$(basename "$mcp_source_path")"
  mcp_target_abs="$(cd "$(dirname "$mcp_target_path")" && pwd -P)/$(basename "$mcp_target_path")"
  if [[ "$mcp_source_abs" != "$mcp_target_abs" ]]; then
    cp "$mcp_source_path" "$mcp_target_path"
  fi
  chmod 0755 "$mcp_target_path"
  echo "Installed memory MCP server: .agents/memory/rag/memory-mcp.py"
}

write_embedding_api_files() {
  local model_id="$1"

  mkdir -p "$EMBEDDING_API_DIR/models"

  cat > "$EMBEDDING_API_DIR/requirements.txt" <<'EOT'
fastapi>=0.115
sentence-transformers>=3.0
uvicorn[standard]>=0.30
EOT

  cat > "$EMBEDDING_API_DIR/server.py" <<'EOT'
from __future__ import annotations

import os
import time
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer


MODEL_ID = os.environ.get("AGENT_BASICS_EMBEDDING_MODEL", "").strip()
CACHE_DIR = os.environ.get("AGENT_BASICS_HF_CACHE_DIR", "").strip() or None
NORMALIZE = os.environ.get("AGENT_BASICS_EMBEDDING_NORMALIZE", "1") != "0"

if not MODEL_ID:
    raise RuntimeError("AGENT_BASICS_EMBEDDING_MODEL is required")

MODEL = SentenceTransformer(MODEL_ID, cache_folder=CACHE_DIR)
STARTED_AT = time.time()

app = FastAPI(title="agent-basics embedding API")


class EmbeddingRequest(BaseModel):
    input: str | list[str]
    model: str | None = None
    dimensions: int | None = None


def _as_inputs(value: str | list[str]) -> list[str]:
    if isinstance(value, str):
        return [value]
    if not value:
        raise HTTPException(status_code=400, detail="input must not be empty")
    if not all(isinstance(item, str) for item in value):
        raise HTTPException(status_code=400, detail="input must be a string or list of strings")
    return value


def _resize(vector: np.ndarray, dimensions: int | None) -> list[float]:
    if dimensions is not None:
        if dimensions <= 0:
            raise HTTPException(status_code=400, detail="dimensions must be positive")
        if dimensions > vector.shape[0]:
            raise HTTPException(status_code=400, detail="dimensions exceeds model embedding dimension")
        vector = vector[:dimensions]
        if NORMALIZE:
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
    return [float(item) for item in vector.tolist()]


def _model_dimensions() -> int:
    vector = MODEL.encode(["agent-basics dimension check"], normalize_embeddings=NORMALIZE, convert_to_numpy=True)
    if vector.ndim != 2 or vector.shape[0] != 1:
        raise RuntimeError("embedding model returned an unexpected shape")
    return int(vector.shape[1])


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "model": MODEL_ID,
        "dimensions": _model_dimensions(),
        "uptime_seconds": time.time() - STARTED_AT,
    }


@app.get("/v1/models")
def models() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_ID,
                "object": "model",
                "owned_by": "agent-basics",
            }
        ],
    }


@app.post("/v1/embeddings")
def embeddings(request: EmbeddingRequest) -> dict[str, Any]:
    inputs = _as_inputs(request.input)
    vectors = MODEL.encode(inputs, normalize_embeddings=NORMALIZE, convert_to_numpy=True)
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)
    if vectors.ndim != 2 or vectors.shape[0] != len(inputs):
        raise HTTPException(status_code=500, detail="embedding model returned an unexpected shape")

    data = [
        {
            "object": "embedding",
            "embedding": _resize(vectors[index], request.dimensions),
            "index": index,
        }
        for index in range(len(inputs))
    ]

    return {
        "object": "list",
        "data": data,
        "model": request.model or MODEL_ID,
        "usage": {
            "prompt_tokens": 0,
            "total_tokens": 0,
        },
    }
EOT

  cat > "$EMBEDDING_API_DIR/verify_model.py" <<'EOT'
from __future__ import annotations

import math
import os
import sys

from sentence_transformers import SentenceTransformer


model_id = os.environ.get("AGENT_BASICS_EMBEDDING_MODEL", "").strip()
cache_dir = os.environ.get("AGENT_BASICS_HF_CACHE_DIR", "").strip() or None
minimum_dimensions = int(os.environ.get("AGENT_BASICS_EMBEDDING_MIN_DIMENSIONS", "64"))

if not model_id:
    print("AGENT_BASICS_EMBEDDING_MODEL is required", file=sys.stderr)
    sys.exit(1)

model = SentenceTransformer(model_id, cache_folder=cache_dir)
vectors = model.encode(
    [
        "agent-basics embedding health check",
        "project memory retrieval should work for vague requests",
    ],
    normalize_embeddings=True,
    convert_to_numpy=True,
)

if vectors.ndim != 2 or vectors.shape[0] != 2:
    print(f"unexpected embedding shape: {vectors.shape}", file=sys.stderr)
    sys.exit(1)

dimensions = int(vectors.shape[1])
if dimensions < minimum_dimensions:
    print(f"embedding dimension {dimensions} is below required minimum {minimum_dimensions}", file=sys.stderr)
    sys.exit(1)

if not all(math.isfinite(float(item)) for item in vectors[0]):
    print("embedding contains non-finite values", file=sys.stderr)
    sys.exit(1)

print(dimensions)
EOT

  cat > "$EMBEDDING_API_DIR/start.sh" <<'EOT'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SCRIPT_DIR/config.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/config.env"
  set +a
fi

export AGENT_BASICS_EMBEDDING_MODEL="${AGENT_BASICS_EMBEDDING_MODEL:?AGENT_BASICS_EMBEDDING_MODEL is required}"
export AGENT_BASICS_HF_CACHE_DIR="${AGENT_BASICS_HF_CACHE_DIR:-$SCRIPT_DIR/models}"
export AGENT_BASICS_EMBEDDING_HOST="${AGENT_BASICS_EMBEDDING_HOST:-127.0.0.1}"
export AGENT_BASICS_EMBEDDING_PORT="${AGENT_BASICS_EMBEDDING_PORT:-8765}"

exec "$SCRIPT_DIR/venv/bin/python" -m uvicorn server:app \
  --app-dir "$SCRIPT_DIR" \
  --host "$AGENT_BASICS_EMBEDDING_HOST" \
  --port "$AGENT_BASICS_EMBEDDING_PORT"
EOT
  chmod 0755 "$EMBEDDING_API_DIR/start.sh"

  cat > "$EMBEDDING_API_DIR/config.env" <<EOT
AGENT_BASICS_EMBEDDING_MODEL="$model_id"
AGENT_BASICS_HF_CACHE_DIR="$EMBEDDING_API_DIR/models"
AGENT_BASICS_EMBEDDING_HOST="127.0.0.1"
AGENT_BASICS_EMBEDDING_PORT="8765"
AGENT_BASICS_EMBEDDING_NORMALIZE="1"
EOT

  cat > "$EMBEDDING_API_DIR/README.md" <<'EOT'
# agent-basics Embedding API

This directory contains a small OpenAI-compatible embedding API generated by `setup-macos.sh` when the project is configured with a HuggingFace embedding model.

Start it from the repository root:

```bash
.agents/memory/rag/embedding-api/start.sh
```

The service exposes:

- `GET /health`
- `GET /v1/models`
- `POST /v1/embeddings`

Model weights are cached under `models/`. The virtualenv is under `venv/`. Both are generated runtime state and should not be committed.
EOT
}

normalize_hf_model_id() {
  local input="$1"
  input="${input#https://huggingface.co/}"
  input="${input#http://huggingface.co/}"
  input="${input%%\?*}"
  input="${input%%#*}"
  input="${input%%/tree/*}"
  input="${input%%/blob/*}"
  input="${input%%/resolve/*}"
  input="${input%/}"
  printf "%s\n" "$input"
}

write_rag_config() {
  local provider="$1"
  local base_url="$2"
  local model="$3"
  local dimensions="$4"
  local api_key_env="$5"
  local service_dir="$6"
  local cache_dir="$7"
  local start_command="$8"
  local timeout_seconds="${AGENT_BASICS_EMBEDDING_TIMEOUT:-0}"
  local batch_size="${AGENT_BASICS_EMBEDDING_BATCH_SIZE:-16}"
  local minimum_dimensions="${AGENT_BASICS_EMBEDDING_MIN_DIMENSIONS:-64}"

  mkdir -p "$RAG_DIR"
  python3 - "$RAG_DIR/config.json" "$provider" "$base_url" "$model" "$dimensions" "$api_key_env" "$service_dir" "$cache_dir" "$start_command" "$timeout_seconds" "$batch_size" "$minimum_dimensions" <<'PY'
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

(
    path,
    provider,
    base_url,
    model,
    dimensions,
    api_key_env,
    service_dir,
    cache_dir,
    start_command,
    timeout_seconds,
    batch_size,
    minimum_dimensions,
) = sys.argv[1:]
payload = {
    "version": 1,
    "embedding": {
        "provider": provider,
        "base_url": base_url,
        "model": model,
        "dimensions": int(dimensions),
        "api_key_env": api_key_env,
    },
    "runtime": {
        "embedding_timeout_seconds": 0 if timeout_seconds in {"", "0", "none", "None"} else float(timeout_seconds),
        "embedding_batch_size": int(batch_size),
        "embedding_minimum_dimensions": int(minimum_dimensions),
        "hook_auto_rebuild": False,
    },
    "updated": int(datetime.now(timezone.utc).timestamp()),
}

if service_dir:
    payload["embedding"]["service_dir"] = service_dir
if cache_dir:
    payload["embedding"]["cache_dir"] = cache_dir
if start_command:
    payload["embedding"]["start_command"] = start_command

with open(path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY
  echo "Wrote RAG configuration: .agents/memory/rag/config.json"
}

validate_embedding_api() {
  local base_url="$1"
  local model="$2"
  local api_key="$3"
  local timeout_seconds="${AGENT_BASICS_EMBEDDING_TIMEOUT:-0}"
  local minimum_dimensions="${AGENT_BASICS_EMBEDDING_MIN_DIMENSIONS:-64}"

  python3 - "$base_url" "$model" "$api_key" "$timeout_seconds" "$minimum_dimensions" <<'PY'
from __future__ import annotations

import json
import math
import sys
import urllib.error
import urllib.request

base_url, model, api_key, timeout_seconds, minimum_dimensions = sys.argv[1:]
base_url = base_url.rstrip("/")
timeout = None if timeout_seconds in {"", "0", "none", "None"} else float(timeout_seconds)
request_payload = {
    "model": model,
    "input": ["agent-basics embedding health check"],
}
request = urllib.request.Request(
    f"{base_url}/embeddings",
    data=json.dumps(request_payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
if api_key:
    request.add_header("Authorization", f"Bearer {api_key}")

try:
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
except urllib.error.HTTPError as exc:
    body = exc.read().decode("utf-8", errors="replace")
    print(f"embedding API returned HTTP {exc.code}: {body}", file=sys.stderr)
    sys.exit(1)
except Exception as exc:
    print(f"embedding API validation failed: {exc}", file=sys.stderr)
    sys.exit(1)

try:
    embedding = payload["data"][0]["embedding"]
except Exception as exc:
    print(f"embedding API response did not match OpenAI-compatible shape: {exc}", file=sys.stderr)
    sys.exit(1)

if not isinstance(embedding, list) or not embedding:
    print("embedding API returned an empty or invalid embedding vector", file=sys.stderr)
    sys.exit(1)

if not all(isinstance(item, (int, float)) and math.isfinite(float(item)) for item in embedding):
    print("embedding API returned non-numeric or non-finite values", file=sys.stderr)
    sys.exit(1)

if len(embedding) < int(minimum_dimensions):
    print(
        f"embedding API returned {len(embedding)} dimensions, below required minimum {minimum_dimensions}",
        file=sys.stderr,
    )
    sys.exit(1)

print(len(embedding))
PY
}

configure_existing_embedding_api() {
  local base_url="${AGENT_BASICS_EMBEDDING_BASE_URL:-}"
  local model="${AGENT_BASICS_EMBEDDING_MODEL:-}"
  local api_key_env="${AGENT_BASICS_EMBEDDING_API_KEY_ENV-AGENT_BASICS_EMBEDDING_API_KEY}"
  local api_key=""
  local dimensions

  if [[ -z "$base_url" ]]; then
    base_url="$(read_with_default "Embedding API base URL" "http://127.0.0.1:1234/v1")"
  fi

  if [[ -z "$model" ]]; then
    model="$(read_with_default "Embedding model name" "")"
  fi

  if [[ -z "$model" ]]; then
    echo "Error: embedding model name is required." >&2
    exit 1
  fi

  if [[ -t 0 && -z "${AGENT_BASICS_EMBEDDING_API_KEY_ENV+x}" ]]; then
    api_key_env="$(read_with_default "API key environment variable name, leave blank for none" "$api_key_env")"
  fi

  if [[ -n "$api_key_env" ]]; then
    api_key="${!api_key_env-}"
  fi

  echo "Validating embedding API: $base_url model=$model"
  dimensions="$(validate_embedding_api "$base_url" "$model" "$api_key")"
  write_rag_config "openai-compatible-api" "$base_url" "$model" "$dimensions" "$api_key_env" "" "" ""
  echo "Embedding API is valid. Dimension: $dimensions"
}

configure_huggingface_embedding_api() {
  local raw_model="${AGENT_BASICS_EMBEDDING_HF_MODEL:-}"
  local model_id
  local python_version="${AGENT_BASICS_PYTHON_VERSION:-3.12}"
  local dimensions

  if [[ -z "$raw_model" ]]; then
    raw_model="$(read_with_default "HuggingFace embedding model id or URL" "")"
  fi

  model_id="$(normalize_hf_model_id "$raw_model")"
  if [[ -z "$model_id" || "$model_id" != */* ]]; then
    echo "Error: HuggingFace model must look like owner/model or https://huggingface.co/owner/model." >&2
    exit 1
  fi

  if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv is required to install the repo-local HuggingFace embedding API." >&2
    exit 1
  fi

  write_embedding_api_files "$model_id"

  if [[ ! -d "$EMBEDDING_API_DIR/venv" ]]; then
    uv venv --python "$python_version" "$EMBEDDING_API_DIR/venv"
  fi

  uv pip install --python "$EMBEDDING_API_DIR/venv/bin/python" -r "$EMBEDDING_API_DIR/requirements.txt"

  echo "Pulling and validating HuggingFace embedding model: $model_id"
  dimensions="$(
    AGENT_BASICS_EMBEDDING_MODEL="$model_id" \
    AGENT_BASICS_HF_CACHE_DIR="$EMBEDDING_API_DIR/models" \
    "$EMBEDDING_API_DIR/venv/bin/python" "$EMBEDDING_API_DIR/verify_model.py"
  )"

  write_rag_config \
    "huggingface-local" \
    "http://127.0.0.1:8765/v1" \
    "$model_id" \
    "$dimensions" \
    "" \
    ".agents/memory/rag/embedding-api" \
    ".agents/memory/rag/embedding-api/models" \
    ".agents/memory/rag/embedding-api/start.sh"

  echo "Local HuggingFace embedding API is ready."
  echo "Start it with: .agents/memory/rag/embedding-api/start.sh"
}

configure_embedding() {
  local mode="${AGENT_BASICS_EMBEDDING_MODE:-}"
  local choice

  case "$mode" in
    api)
      configure_existing_embedding_api
      return
      ;;
    huggingface|hf)
      configure_huggingface_embedding_api
      return
      ;;
    "")
      ;;
    *)
      echo "Error: AGENT_BASICS_EMBEDDING_MODE must be api or huggingface." >&2
      exit 1
      ;;
  esac

  if [[ -n "${AGENT_BASICS_EMBEDDING_BASE_URL:-}" || -n "${AGENT_BASICS_EMBEDDING_MODEL:-}" ]]; then
    configure_existing_embedding_api
    return
  fi

  if [[ -n "${AGENT_BASICS_EMBEDDING_HF_MODEL:-}" ]]; then
    configure_huggingface_embedding_api
    return
  fi

  require_interactive "Embedding setup is required."

  cat <<'EOT'
agent-basics requires an embedding provider for compatibility memory RAG support.
Choose one:
  a  use an existing OpenAI-compatible embedding API
  h  install a HuggingFace embedding model and create a repo-local API
EOT

  while true; do
    read -r -p "Selection [a/h]: " choice
    case "$choice" in
      a|A)
        configure_existing_embedding_api
        return
        ;;
      h|H)
        configure_huggingface_embedding_api
        return
        ;;
      *)
        echo "Invalid choice: $choice" >&2
        ;;
    esac
  done
}

read_rag_config_field() {
  local field="$1"

  python3 - "$RAG_DIR/config.json" "$RAG_DIR/embedding.json" "$field" <<'PY'
from __future__ import annotations

import json
import sys

config_path, legacy_path, field = sys.argv[1:]
try:
    with open(config_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
except FileNotFoundError:
    with open(legacy_path, "r", encoding="utf-8") as handle:
        payload = {"embedding": json.load(handle), "runtime": {}}

value = payload
for part in field.split("."):
    if not isinstance(value, dict):
        value = ""
        break
    value = value.get(part, "")
print(value)
PY
}

start_repo_local_embedding_api_for_setup() {
  local provider
  local base_url
  local model
  local api_key_env
  local api_key=""
  local start_command
  local dimensions
  local timeout_seconds
  local start_time="$SECONDS"
  local elapsed
  local timeout_limit

  if [[ ! -f "$RAG_DIR/config.json" && ! -f "$RAG_DIR/embedding.json" ]]; then
    return
  fi

  provider="$(read_rag_config_field "embedding.provider")"
  if [[ "$provider" != "huggingface-local" ]]; then
    return
  fi

  base_url="$(read_rag_config_field "embedding.base_url")"
  model="$(read_rag_config_field "embedding.model")"
  api_key_env="$(read_rag_config_field "embedding.api_key_env")"
  start_command="$(read_rag_config_field "embedding.start_command")"
  timeout_seconds="${AGENT_BASICS_EMBEDDING_TIMEOUT:-$(read_rag_config_field "runtime.embedding_timeout_seconds")}"
  timeout_seconds="${timeout_seconds:-0}"

  if [[ -z "$start_command" ]]; then
    echo "Error: local embedding config is missing start_command." >&2
    exit 1
  fi

  if [[ -n "$api_key_env" ]]; then
    api_key="${!api_key_env-}"
  fi

  LOCAL_EMBEDDING_LOG="$(mktemp "${TMPDIR:-/tmp}/agent-basics-embedding-api.XXXXXX")"
  echo "Starting repo-local embedding API for setup rebuild: $start_command"
  echo "Embedding API log: $LOCAL_EMBEDDING_LOG"

  "$start_command" > "$LOCAL_EMBEDDING_LOG" 2>&1 &
  LOCAL_EMBEDDING_PID="$!"

  while true; do
    if ! kill -0 "$LOCAL_EMBEDDING_PID" >/dev/null 2>&1; then
      echo "Error: repo-local embedding API exited before it became ready." >&2
      cat "$LOCAL_EMBEDDING_LOG" >&2
      exit 1
    fi

    if dimensions="$(validate_embedding_api "$base_url" "$model" "$api_key" 2>/dev/null)"; then
      echo "Repo-local embedding API is ready. Dimension: $dimensions"
      return
    fi

    case "$timeout_seconds" in
      ""|0|none|None)
        ;;
      *)
        elapsed=$((SECONDS - start_time))
        timeout_limit="${timeout_seconds%.*}"
        if (( elapsed >= timeout_limit )); then
          echo "Error: timed out waiting for repo-local embedding API after ${timeout_seconds}s." >&2
          cat "$LOCAL_EMBEDDING_LOG" >&2
          exit 1
        fi
        ;;
    esac

    sleep 1
  done
}

verify_user_openviking_installation
snapshot_existing_legacy_memory
create_memory_layout

agents_template="$(create_template_file "agents")"
agent_basics_template="$(create_template_file "agent-basics")"
trap cleanup_setup EXIT

copy_or_merge_markdown_file "$agents_template" "Agents.md"
seed_agent_basics_from_legacy_instructions
copy_or_merge_markdown_file "$agent_basics_template" ".agents/AGENT-BASICS.md"
create_empty_file_if_missing ".agents/TODO.md"

copy_memory_template_if_missing "memory-schema" ".agents/memory/SCHEMA.md"
copy_memory_template_if_missing "memory-index" ".agents/memory/INDEX.md"
copy_memory_template_if_missing "memory-adaptation" ".agents/memory/ADAPTATION.md"
write_repo_openviking_metadata_if_missing
write_repo_config_if_missing
write_repo_mcp_config_snippets
create_empty_file_if_missing ".agents/memory/memories/profile/.gitkeep"
create_empty_file_if_missing ".agents/memory/memories/preferences/.gitkeep"
create_empty_file_if_missing ".agents/memory/memories/entities/.gitkeep"
create_empty_file_if_missing ".agents/memory/memories/events/.gitkeep"
create_empty_file_if_missing ".agents/memory/memories/cases/.gitkeep"
create_empty_file_if_missing ".agents/memory/memories/patterns/.gitkeep"
create_empty_file_if_missing ".agents/memory/memories/tools/.gitkeep"
create_empty_file_if_missing ".agents/memory/memories/skills/.gitkeep"
create_empty_file_if_missing ".agents/memory/resources/sources/.gitkeep"
create_empty_file_if_missing ".agents/memory/resources/procedures/.gitkeep"
create_empty_file_if_missing ".agents/memory/resources/references/.gitkeep"
create_empty_file_if_missing ".agents/memory/skills/.gitkeep"
create_empty_file_if_missing ".agents/memory/inbox/.gitkeep"
create_empty_file_if_missing ".agents/memory/imports/.gitkeep"
create_empty_file_if_missing ".agents/memory/sessions/.gitkeep"

if compat_memory_enabled; then
  create_compat_memory_layout
  copy_memory_template_if_missing "template-decision" ".agents/memory/templates/decision.md"
  copy_memory_template_if_missing "template-fact" ".agents/memory/templates/fact.md"
  copy_memory_template_if_missing "template-preference" ".agents/memory/templates/preference.md"
  copy_memory_template_if_missing "template-source" ".agents/memory/templates/source.md"
  copy_memory_template_if_missing "template-procedure" ".agents/memory/templates/procedure.md"
  copy_memory_template_if_missing "template-gotcha" ".agents/memory/templates/gotcha.md"
  copy_memory_template_if_missing "template-event" ".agents/memory/templates/event.md"
  copy_memory_template_if_missing "agent-basics-preference" ".agents/memory/memory/preferences/agent-basics.md"
  copy_memory_template_if_missing "agent-basics-decision" ".agents/memory/memory/decisions/repo-local-memory-rag.md"
  copy_memory_template_if_missing "agent-basics-doc-sources" ".agents/memory/documentations/sources/agent-basics.md"
  copy_memory_template_if_missing "openviking-gateway-procedure" ".agents/memory/documentations/procedures/openviking-gateway.md"
  copy_memory_template_if_missing "agent-memory-mcp-procedure" ".agents/memory/documentations/procedures/agent-memory-mcp.md"
  copy_memory_template_if_missing "agent-memory-cli-procedure" ".agents/memory/documentations/procedures/agent-memory-cli.md"
  copy_memory_template_if_missing "local-embedding-procedure" ".agents/memory/documentations/procedures/local-huggingface-embedding-api.md"
  create_empty_file_if_missing ".agents/memory/memory/facts/.gitkeep"
  create_empty_file_if_missing ".agents/memory/memory/gotchas/.gitkeep"
  create_empty_file_if_missing ".agents/memory/memory/events/.gitkeep"
  create_empty_file_if_missing ".agents/memory/documentations/references/.gitkeep"
fi

migrate_legacy_markdown_if_missing \
  ".agents/DOCUMENTATIONS.md" \
  ".agents/memory/imports/legacy-documentations.md" \
  "source" \
  "Legacy DOCUMENTATIONS.md" \
  "Legacy documentation records migrated from .agents/DOCUMENTATIONS.md." \
  "[legacy, documentation]"
migrate_legacy_markdown_if_missing \
  ".agents/MEMORY.md" \
  ".agents/memory/imports/legacy-memory.md" \
  "fact" \
  "Legacy MEMORY.md" \
  "Legacy memory records migrated from .agents/MEMORY.md." \
  "[legacy, memory]"

append_gitignore_entry_if_missing ".agents/TODO.md"
append_gitignore_entry_if_missing ".agents/backups/"
append_gitignore_entry_if_missing ".agents/merge-sessions/"
append_gitignore_entry_if_missing ".agents/openviking/locks/"

if compat_memory_enabled; then
  configure_embedding
  write_memory_tool_files
  append_gitignore_entry_if_missing ".agents/memory/rag/write.lock/"
  append_gitignore_entry_if_missing ".agents/memory/rag/manifest.json"
  append_gitignore_entry_if_missing ".agents/memory/rag/*.sqlite"
  append_gitignore_entry_if_missing ".agents/memory/rag/*.sqlite-*"
  append_gitignore_entry_if_missing ".agents/memory/rag/embedding-api/venv/"
  append_gitignore_entry_if_missing ".agents/memory/rag/embedding-api/models/"
fi

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Git repository already initialized"
else
  git init >/dev/null
  echo "Initialized empty Git repository"
fi

if compat_memory_enabled; then
  ".agents/memory/rag/agent-memory.py" install-hooks
fi

while IFS= read -r markdown_file; do
  ensure_trailing_blank_line "$markdown_file"
done < <(find "Agents.md" ".agents" -type f -name "*.md" 2>/dev/null | sort)

if compat_memory_enabled; then
  start_repo_local_embedding_api_for_setup
  ".agents/memory/rag/agent-memory.py" rebuild
fi

cat <<EOT
agent-basics setup complete.

OpenViking source store:
  .agents/memory/

OpenViking repo metadata:
  .agents/openviking/

OpenViking repo config:
  .agents/config.toml

MCP config snippets:
  .agents/openviking/codex-mcp.json

Legacy memory snapshots:
  .agents/openviking/legacy-memory/

Conflict backups and merge sessions:
  .agents/backups/
  .agents/merge-sessions/

Codex Desktop custom MCP fields for the target gateway:
  Name: agent-basics
  Transport: STDIO
  Command to launch: agent-basics
  Arguments: mcp
  Working directory: $TARGET_DIR

Compatibility mini-RAG:
  Not installed by default. Re-run with AGENT_BASICS_INSTALL_COMPAT_MEMORY=1 only if you need the old fallback memory CLI/MCP when OpenViking is unavailable.

If legacy material was snapshotted, adapt it with:
  .agents/memory/ADAPTATION.md
EOT
