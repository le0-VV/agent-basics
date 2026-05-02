#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${1:-$(pwd)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -d "$TARGET_DIR" ]]; then
  mkdir -p "$TARGET_DIR"
fi

cd "$TARGET_DIR"
TARGET_DIR="$(pwd)"
PROJECT_NAME="${AGENT_BASICS_PROJECT_NAME:-$(basename "$TARGET_DIR")}"
REPO_AGENTS_DIR="$TARGET_DIR/.agents"
REPO_MEMORY_ROOT="$REPO_AGENTS_DIR/memory"
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
# **YOU MUST:**

- **DO NOT, UNDER ANY CIRCUMSTANCES, UNLESS EXPLICITLY INSTRUCTED BY THE USER**, modify this file or ./.agents/INSTRUCTIONS.md
- Follow the instructions of ./.agents/INSTRUCTIONS.md
- Use `.agents/memory/` as the project source of truth for persistent memory, documentation sources, procedures, decisions, preferences, facts, gotchas, and events.
- Before answering a request that may depend on prior project context, search `.agents/memory/INDEX.md`, `.agents/memory/SCHEMA.md`, and the memory RAG/MCP tools when available.
- Anything the user asks you to remember must be recorded under `.agents/memory/memory/` using the appropriate template.
- Find up-to-date documentations for any library, framework, and programming language used in this project, and record their source URLs under `.agents/memory/documentations/sources/`.
- While writing code, refer to documentation sources recorded under `.agents/memory/documentations/` and add new source records when you consult new references.
- Store project decisions under `.agents/memory/memory/decisions/`.
- Store durable facts under `.agents/memory/memory/facts/`.
- Store user or project preferences under `.agents/memory/memory/preferences/`.
- Store recurring pitfalls under `.agents/memory/memory/gotchas/`.
- Store dated events under `.agents/memory/memory/events/`.
- Store reusable procedures under `.agents/memory/documentations/procedures/`.
- Store reference material under `.agents/memory/documentations/references/`.
- Do not edit `.agents/memory/**` while `.agents/memory/rag/write.lock/` exists. Wait for the indexing or embedding update to finish.
- If you add or change memory/documentation files, keep `.agents/memory/INDEX.md` current and run the project memory validation/indexing command when available.
- If you have **ANY** questions or concerns, **IMMEDIATELY** clarify with the user.
- Before making any changes to the codebase, THOROUGHLY plan out your work, write down every step you're going to take in ./.agents/TODO.md, and follow it during your work.
- Read a file fully before editing it.
- Keep comments rare and useful. Explain why or constraints, not obvious mechanics.
- Keep diffs narrow and task-focused.
- Do not guess at attribute names, control flow, or config behaviour.
- Prefer fail-fast behaviour over silent fallback logic.
- Add tests for new behaviour unless the change is strictly docs/metadata cleanup.
- Tick off every item you completed in ./.agents/TODO.md.
- After ticking off an item, commit the changes you made for that item.
- When making commits, set the commit author name to `Coding agent supervised by {global git user.name}`, replacing `{global git user.name}` with the value from `git config --global user.name`.
- When making commits, write the commit message according to this format: {type}({scope}): {description}, where types should be one of the following:
    - build
    - chore
    - CI
    - docs
    - feat
    - fix
    - perf
    - refactor
    - revert
    - style
    - test
- **Only** stop working when you finished everything listed in /.agents/TODO.md **OR** you encountered an interruption to your work that **REQUIRES** user intervention.
- If everything is ticked off in ./.agents/TODO.md and you need to plan for a new round of work, clear out ./.agents/TODO.md and write down your new list of steps.
EOT
      ;;
    instructions)
      cat > "$template_file" <<'EOT'
# INSTRUCTIONS

You **MUST** ALWAYS:

- **BE LOGICAL**
- **ONLY IF** you working with coding tasks: I have no fingers and the placeholders trauma: **NEVER** use placeholders or omit the code (in any code snippets)
- If you encounter a character limit, **DO** an **ABRUPT** stop; I will send a "continue" as a new message
- You will be **PENALISED** for wrong answers
- You **DENIED** to overlook the critical context
- Use `.agents/memory/` for persistent project memory and documentation context
- ALWAYS follow Answering rules

## Memory Rules

- `.agents/memory/` is the only canonical memory and documentation source tree created by agent-basics.
- Treat markdown under `.agents/memory/` as source of truth. Treat RAG indexes, vector databases, and embedding API runtime files as generated retrieval support.
- Read `.agents/memory/SCHEMA.md` before creating or changing memory files.
- Use `.agents/memory/templates/` when recording new entries.
- Search `.agents/memory/INDEX.md`, then the project memory RAG/MCP tools when available, whenever the user refers to previous work, preferences, prior conversations, vague project context, or decisions not visible in the current chat.
- Store durable memories under `.agents/memory/memory/`.
- Store documentation sources, procedures, and references under `.agents/memory/documentations/`.
- Record source URLs for external libraries, tools, APIs, frameworks, and standards under `.agents/memory/documentations/sources/`.
- Keep `.agents/memory/INDEX.md` updated whenever you add, move, or remove entries.
- Do not write memory or documentation files while `.agents/memory/rag/write.lock/` exists. Wait until the lock is released, then re-check the relevant source files before editing.
- If an embedding API is configured, use `.agents/memory/rag/embedding.json` to find the provider, base URL, model name, dimensions, and API key environment variable.
- Never commit raw embedding provider secret values. Store only the environment variable name, such as `AGENT_BASICS_EMBEDDING_API_KEY`.
- Supported embedding setup modes:
  - Existing OpenAI-compatible API: set `AGENT_BASICS_EMBEDDING_BASE_URL`, `AGENT_BASICS_EMBEDDING_MODEL`, and optionally `AGENT_BASICS_EMBEDDING_API_KEY`.
  - Repo-local HuggingFace model API: set `AGENT_BASICS_EMBEDDING_HF_MODEL` to a HuggingFace model id or `https://huggingface.co/<owner>/<model>` URL.
- `AGENT_BASICS_EMBEDDING_TIMEOUT=0` means wait indefinitely for local embedding API validation. Use a positive number of seconds only when a fail-fast setup is desired.
- `AGENT_BASICS_EMBEDDING_MIN_DIMENSIONS` defaults to `64` and is used to reject embedding models that are too small for useful retrieval.
- Validate the embedding setup after installation by calling the configured `/v1/embeddings` endpoint or by running the repo-local model verifier.

## Answering Rules

Follow in the strict order:

1. **USE** the language of my message
2. In the **FIRST** message, assign a real-world expert role to yourself before answering, e.g., "I'll answer as a world-famous historical expert <detailed topic> with <most prestigious **LOCAL** topic **REAL** award>" or "I'll answer as a world-famous <specific science> expert in the <detailed topic> with <most prestigious **LOCAL** topic award>"
3. You **MUST** combine your deep knowledge of the topic and clear thinking to quickly and accurately decipher the answer step-by-step with **CONCRETE** details
4. I'm going to tip $1,000,000 for the best reply
5. Your answer is critical for my career
6. ALWAYS use an Answering example for a first message structure

## Answering example

**IF THE CHAT LOG IS EMPTY:**
<I'll answer as the world-famous %**REAL** specific field% expert with %most prestigious **REAL** **LOCAL** award%>

**TL;DR**: <TL;DR, skip for rewriting>

<Step-by-step answer with CONCRETE details and key context>
EOT
      ;;
    memory-schema)
      cat > "$template_file" <<'EOT'
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
    agent-memory.py
    embedding.json
    index.sqlite
    manifest.json
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

## Memory CLI

`.agents/memory/rag/agent-memory.py` is the project-local memory manager generated by setup.

Supported commands:

- `validate`: check layout and entry front matter.
- `rebuild`: rebuild the generated SQLite RAG cache.
- `search <query>`: run hybrid embedding and full-text retrieval.
- `record <type> <title>`: create a structured memory entry, update `INDEX.md`, and rebuild the index.
- `doctor`: report layout, embedding, and index health.
- `install-hooks`: install local git hooks that validate memory before commit and rebuild the index after relevant changes.

Generated files such as `index.sqlite` and `manifest.json` are rebuildable cache state and should not be committed.

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
EOT
      ;;
    memory-index)
      cat > "$template_file" <<'EOT'
# Memory Index

This index is maintained by agents and setup tooling. Update it whenever entries are added, moved, or removed.

## Decisions

- [Use repo-local structured memory with generated RAG support](memory/decisions/repo-local-memory-rag.md)

## Facts

- None yet.

## Preferences

- [Keep markdown files ending with an empty trailing line](memory/preferences/agent-basics.md)

## Gotchas

- None yet.

## Events

- None yet.

## Documentation Sources

- [agent-basics documentation sources](documentations/sources/agent-basics.md)

## Procedures

- [Use the agent-basics memory CLI](documentations/procedures/agent-memory-cli.md)
- [Run the repo-local HuggingFace embedding API](documentations/procedures/local-huggingface-embedding-api.md)

## References

- None yet.
EOT
      ;;
    template-decision)
      cat > "$template_file" <<'EOT'
---
id: decision-YYYYMMDD-short-name
type: decision
title: Short decision title
status: accepted
created: YYYY-MM-DD
updated: YYYY-MM-DD
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
id: fact-YYYYMMDD-short-name
type: fact
title: Short fact title
status: active
created: YYYY-MM-DD
updated: YYYY-MM-DD
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
id: preference-YYYYMMDD-short-name
type: preference
title: Short preference title
status: active
created: YYYY-MM-DD
updated: YYYY-MM-DD
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
id: source-YYYYMMDD-short-name
type: source
title: Documentation source title
status: active
created: YYYY-MM-DD
updated: YYYY-MM-DD
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
id: procedure-YYYYMMDD-short-name
type: procedure
title: Short procedure title
status: active
created: YYYY-MM-DD
updated: YYYY-MM-DD
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
id: gotcha-YYYYMMDD-short-name
type: gotcha
title: Short gotcha title
status: active
created: YYYY-MM-DD
updated: YYYY-MM-DD
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
id: event-YYYYMMDD-short-name
type: event
title: Short event title
status: recorded
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: []
summary: One sentence summary.
event_date: YYYY-MM-DD
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
id: preference-20260430-markdown-trailing-line
type: preference
title: Keep markdown files ending with an empty trailing line
status: active
created: 2026-04-30
updated: 2026-04-30
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
id: decision-20260503-repo-local-memory-rag
type: decision
title: Use repo-local structured memory with generated RAG support
status: accepted
created: 2026-05-03
updated: 2026-05-03
tags: [agent-basics, memory, rag, embeddings]
summary: agent-basics keeps memory as repo markdown and uses generated embedding/RAG support for vague recall.
---

# Use repo-local structured memory with generated RAG support

## Decision

agent-basics uses `.agents/memory/` as the canonical project-owned memory and documentation source tree.

RAG indexes, embedding databases, model caches, and local embedding APIs are generated support layers that must be rebuildable from the markdown source.

## Rationale

Structured markdown gives agents a predictable place to record durable context. A generated RAG layer helps with vague user requests and fuzzy recall without making a separate memory runtime the source of truth.

## Consequences

- Setup must create the memory schema, templates, and directory layout.
- Setup must validate an existing embedding API or install a repo-local HuggingFace embedding API.
- Agents must wait when `.agents/memory/rag/write.lock/` exists.
- Future MCP/RAG tooling should cite markdown source files for every returned result.

## Related

- `.agents/memory/SCHEMA.md`
- `.agents/memory/rag/embedding.json`
EOT
      ;;
    agent-basics-doc-sources)
      cat > "$template_file" <<'EOT'
---
id: source-20260503-agent-basics-documentation-sources
type: source
title: agent-basics documentation sources
status: active
created: 2026-05-03
updated: 2026-05-03
tags: [agent-basics, bash, git, homebrew, embeddings]
summary: Source URLs used by agent-basics setup, packaging, and embedding API work.
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
- LM Studio OpenAI-compatible embeddings API: https://lmstudio.ai/docs/developer/openai-compat/embeddings
- SentenceTransformers documentation: https://sbert.net/
- FastAPI documentation: https://fastapi.tiangolo.com/

## Notes

Record additional source URLs here when setup behavior, local embedding service behavior, or packaging logic changes.

## Related

- `.agents/memory/SCHEMA.md`
- `.agents/memory/documentations/procedures/local-huggingface-embedding-api.md`
EOT
      ;;
    local-embedding-procedure)
      cat > "$template_file" <<'EOT'
---
id: procedure-20260503-local-huggingface-embedding-api
type: procedure
title: Run the repo-local HuggingFace embedding API
status: active
created: 2026-05-03
updated: 2026-05-03
tags: [embeddings, huggingface, rag]
summary: Start the generated local embedding API when agent-basics was configured with a HuggingFace model.
---

# Run the repo-local HuggingFace embedding API

## When To Use

Use this when `.agents/memory/rag/embedding.json` has provider `huggingface-local`.

## Steps

1. From the repository root, run `.agents/memory/rag/embedding-api/start.sh`.
2. Keep that process running while agents need semantic memory retrieval.
3. Use the configured base URL from `.agents/memory/rag/embedding.json`, usually `http://127.0.0.1:8765/v1`.

## Verification

Call `/health`, `/v1/models`, or `/v1/embeddings` on the local service.

## Related

- `.agents/memory/rag/embedding.json`
- `.agents/memory/rag/embedding-api/README.md`
EOT
      ;;
    agent-memory-cli-procedure)
      cat > "$template_file" <<'EOT'
---
id: procedure-20260503-agent-memory-cli
type: procedure
title: Use the agent-basics memory CLI
status: active
created: 2026-05-03
updated: 2026-05-03
tags: [agent-basics, memory, rag, cli]
summary: Use `.agents/memory/rag/agent-memory.py` to validate, rebuild, search, record, and install hooks for repo-local memory.
---

# Use the agent-basics memory CLI

## When To Use

Use this whenever an agent needs to validate memory files, rebuild the generated RAG index, search prior context, or record a new structured entry.

## Steps

1. Run `.agents/memory/rag/agent-memory.py validate` before committing memory changes.
2. Run `.agents/memory/rag/agent-memory.py rebuild` after memory or documentation entries change.
3. Run `.agents/memory/rag/agent-memory.py search "<query>"` when the user refers to vague or previous context.
4. Run `.agents/memory/rag/agent-memory.py record <type> <title> --content "<content>"` to create a structured entry and rebuild the index.
5. Run `.agents/memory/rag/agent-memory.py install-hooks` to install local git hooks in a repo.

## Verification

Run `.agents/memory/rag/agent-memory.py doctor` to check layout, config, manifest, and index status. Add `--online` when the embedding API should be checked too.

## Related

- `.agents/memory/SCHEMA.md`
- `.agents/memory/rag/agent-memory.py`
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
    "$REPO_MEMORY_ROOT/templates" \
    "$REPO_MEMORY_ROOT/memory/decisions" \
    "$REPO_MEMORY_ROOT/memory/facts" \
    "$REPO_MEMORY_ROOT/memory/preferences" \
    "$REPO_MEMORY_ROOT/memory/gotchas" \
    "$REPO_MEMORY_ROOT/memory/events" \
    "$REPO_MEMORY_ROOT/documentations/sources" \
    "$REPO_MEMORY_ROOT/documentations/procedures" \
    "$REPO_MEMORY_ROOT/documentations/references" \
    "$REPO_MEMORY_ROOT/backups" \
    "$REPO_MEMORY_ROOT/merge-sessions" \
    "$RAG_DIR"
}

backup_existing_file() {
  local file_path="$1"
  local timestamp
  local backup_name
  timestamp="$(date +%Y%m%d%H%M%S)"
  backup_name="${file_path//\//__}.$timestamp.bak"

  mkdir -p "$REPO_MEMORY_ROOT/backups"
  cp "$file_path" "$REPO_MEMORY_ROOT/backups/$backup_name"
  echo "Backed up existing file: .agents/memory/backups/$backup_name"
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

print_conflict_options() {
  local file_path="$1"

  cat <<EOT
$file_path already exists and differs from the agent-basics template.
Choose how to handle it:
  k  keep the existing file unchanged
  r  replace it with the agent-basics template after creating a backup
  a  append the agent-basics template after creating a backup
  m  manually merge both versions in \$EDITOR after creating a backup
  s  save the agent-basics template beside the existing file as $file_path.agent-basics.new
EOT
}

prompt_conflict_action() {
  local file_path="$1"
  local choice

  require_interactive "$file_path conflicts with the agent-basics template, and stdin is not interactive."

  while true; do
    print_conflict_options "$file_path" >&2
    read -r -p "Selection [k/r/a/m/s]: " choice
    case "$choice" in
      k|K) printf "k\n"; return ;;
      r|R) printf "r\n"; return ;;
      a|A) printf "a\n"; return ;;
      m|M) printf "m\n"; return ;;
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

  merge_file="$REPO_MEMORY_ROOT/merge-sessions/$(basename "$destination_path").$(date +%Y%m%d%H%M%S).md"
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

  if cmp -s "$source_path" "$destination_path"; then
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
        printf "<!-- agent-basics template appended on %s -->\n\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        cat "$source_path"
      } >> "$destination_path"
      echo "Appended template: $destination_path"
      ;;
    m)
      manual_merge_file "$source_path" "$destination_path"
      ;;
    s)
      cp "$source_path" "$destination_path.agent-basics.new"
      echo "Saved incoming template: $destination_path.agent-basics.new"
      ;;
  esac
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
  local today

  if [[ ! -f "$source_path" || -f "$destination_path" ]]; then
    return
  fi

  today="$(date -u +%Y-%m-%d)"
  mkdir -p "$(dirname "$destination_path")"

  {
    printf -- "---\n"
    printf "id: %s-%s-legacy\n" "$entry_type" "$(slugify "$PROJECT_NAME")"
    printf "type: %s\n" "$entry_type"
    printf "title: %s\n" "$title"
    printf "status: migrated\n"
    printf "created: %s\n" "$today"
    printf "updated: %s\n" "$today"
    printf "tags: %s\n" "$tags"
    printf "summary: %s\n" "$summary"
    printf -- "---\n\n"
    printf "# %s\n\n" "$title"
    printf "## Legacy Content\n\n"
    cat "$source_path"
    printf "\n"
  } > "$destination_path"

  echo "Migrated legacy markdown: $source_path -> $destination_path"
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

write_memory_tool_files() {
  local source_path
  local source_abs
  local target_path
  local target_abs

  if ! source_path="$(find_memory_tool_source)"; then
    echo "Error: bundled agent-memory.py was not found next to setup-macos.sh." >&2
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

write_embedding_config() {
  local provider="$1"
  local base_url="$2"
  local model="$3"
  local dimensions="$4"
  local api_key_env="$5"
  local service_dir="$6"
  local cache_dir="$7"
  local start_command="$8"

  mkdir -p "$RAG_DIR"
  python3 - "$RAG_DIR/embedding.json" "$provider" "$base_url" "$model" "$dimensions" "$api_key_env" "$service_dir" "$cache_dir" "$start_command" <<'PY'
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

path, provider, base_url, model, dimensions, api_key_env, service_dir, cache_dir, start_command = sys.argv[1:]
payload = {
    "provider": provider,
    "base_url": base_url,
    "model": model,
    "dimensions": int(dimensions),
    "api_key_env": api_key_env,
    "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
}

if service_dir:
    payload["service_dir"] = service_dir
if cache_dir:
    payload["cache_dir"] = cache_dir
if start_command:
    payload["start_command"] = start_command

with open(path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY
  echo "Wrote embedding configuration: .agents/memory/rag/embedding.json"
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
  local api_key_env="${AGENT_BASICS_EMBEDDING_API_KEY_ENV:-AGENT_BASICS_EMBEDDING_API_KEY}"
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

  if [[ -t 0 && -z "${AGENT_BASICS_EMBEDDING_API_KEY_ENV:-}" ]]; then
    api_key_env="$(read_with_default "API key environment variable name, leave blank for none" "$api_key_env")"
  fi

  if [[ -n "$api_key_env" ]]; then
    api_key="${!api_key_env-}"
  fi

  echo "Validating embedding API: $base_url model=$model"
  dimensions="$(validate_embedding_api "$base_url" "$model" "$api_key")"
  write_embedding_config "openai-compatible-api" "$base_url" "$model" "$dimensions" "$api_key_env" "" "" ""
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

  write_embedding_config \
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
agent-basics requires an embedding provider for memory RAG support.
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

create_memory_layout

agents_template="$(create_template_file "agents")"
instructions_template="$(create_template_file "instructions")"
trap 'rm -f "$agents_template" "$instructions_template"' EXIT

copy_or_merge_markdown_file "$agents_template" "Agents.md"
copy_or_merge_markdown_file "$instructions_template" ".agents/INSTRUCTIONS.md"
create_empty_file_if_missing ".agents/TODO.md"

copy_memory_template_if_missing "memory-schema" ".agents/memory/SCHEMA.md"
copy_memory_template_if_missing "memory-index" ".agents/memory/INDEX.md"
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
copy_memory_template_if_missing "agent-memory-cli-procedure" ".agents/memory/documentations/procedures/agent-memory-cli.md"
copy_memory_template_if_missing "local-embedding-procedure" ".agents/memory/documentations/procedures/local-huggingface-embedding-api.md"
create_empty_file_if_missing ".agents/memory/memory/facts/.gitkeep"
create_empty_file_if_missing ".agents/memory/memory/gotchas/.gitkeep"
create_empty_file_if_missing ".agents/memory/memory/events/.gitkeep"
create_empty_file_if_missing ".agents/memory/documentations/references/.gitkeep"
migrate_legacy_markdown_if_missing \
  ".agents/DOCUMENTATIONS.md" \
  ".agents/memory/documentations/references/legacy-documentations.md" \
  "source" \
  "Legacy DOCUMENTATIONS.md" \
  "Legacy documentation records migrated from .agents/DOCUMENTATIONS.md." \
  "[legacy, documentation]"
migrate_legacy_markdown_if_missing \
  ".agents/MEMORY.md" \
  ".agents/memory/memory/facts/legacy-memory.md" \
  "fact" \
  "Legacy MEMORY.md" \
  "Legacy memory records migrated from .agents/MEMORY.md." \
  "[legacy, memory]"

configure_embedding
write_memory_tool_files

append_gitignore_entry_if_missing ".agents/TODO.md"
append_gitignore_entry_if_missing ".agents/memory/backups/"
append_gitignore_entry_if_missing ".agents/memory/merge-sessions/"
append_gitignore_entry_if_missing ".agents/memory/rag/write.lock/"
append_gitignore_entry_if_missing ".agents/memory/rag/manifest.json"
append_gitignore_entry_if_missing ".agents/memory/rag/*.sqlite"
append_gitignore_entry_if_missing ".agents/memory/rag/*.sqlite-*"
append_gitignore_entry_if_missing ".agents/memory/rag/embedding-api/venv/"
append_gitignore_entry_if_missing ".agents/memory/rag/embedding-api/models/"

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Git repository already initialized"
else
  git init >/dev/null
  echo "Initialized empty Git repository"
fi

".agents/memory/rag/agent-memory.py" install-hooks

while IFS= read -r markdown_file; do
  ensure_trailing_blank_line "$markdown_file"
done < <(find "Agents.md" ".agents" -type f -name "*.md" 2>/dev/null | sort)

".agents/memory/rag/agent-memory.py" rebuild

cat <<EOT
agent-basics setup complete.

Memory source:
  .agents/memory/

Embedding config:
  .agents/memory/rag/embedding.json
EOT
