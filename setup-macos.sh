#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${1:-$(pwd)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MEMORYHUB_CONFIG_DIR="${MEMORYHUB_CONFIG_DIR:-$HOME/.memoryhub}"
MEMORYHUB_VENV_DIR="$MEMORYHUB_CONFIG_DIR/venv"
MEMORYHUB_PROJECTS_DIR="$MEMORYHUB_CONFIG_DIR/projects"
MEMORYHUB_BIN=""

if [[ ! -d "$TARGET_DIR" ]]; then
  echo "Error: target directory does not exist: $TARGET_DIR" >&2
  exit 1
fi

confirm_action() {
  local prompt="$1"
  local choice

  if [[ ! -t 0 ]]; then
    echo "Error: $prompt" >&2
    echo "Run agent-basics in an interactive terminal to approve this required step." >&2
    exit 1
  fi

  while true; do
    read -r -p "$prompt [y/n]: " choice
    case "$choice" in
      y|Y) return 0 ;;
      n|N) return 1 ;;
      *) echo "Invalid choice: $choice" >&2 ;;
    esac
  done
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

absolute_path() {
  local path="$1"
  local directory
  local basename_part

  directory="$(dirname "$path")"
  basename_part="$(basename "$path")"
  if [[ ! -d "$directory" ]]; then
    return 1
  fi

  printf "%s/%s\n" "$(cd "$directory" && pwd -P)" "$basename_part"
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
- MemoryHub is mandatory for this project. Do not use agent-basics workflows until the central MemoryHub installation is installed, initialized, and healthy.
- MemoryHub is the central OpenViking-backed memory hub for agent-basics projects. Use one hub installation and one embedding/runtime stack instead of per-repo OpenViking installs.
- Before running MemoryHub commands for this repo, export `MEMORYHUB_CONFIG_DIR="${MEMORYHUB_CONFIG_DIR:-$HOME/.memoryhub}"` and add `${MEMORYHUB_CONFIG_DIR}/venv/bin` to `PATH` when that virtualenv exists.
- Keep this repo's MemoryHub markdown source under `.agents/memoryhub/`. The central hub should reference it through a symlink under `$MEMORYHUB_CONFIG_DIR/projects/`.
- Find up-to-date documentations for any library, framework and programming languages used in this project, and record their source URLs in MemoryHub resources.
- While you write code, **CONSTANTLY** refer to documentation sources recorded in MemoryHub to make sure you're writing accurate, working and standard-complying code.
- Store user-specific memories in MemoryHub under `.agents/memoryhub/user/memories/`, using categories such as `profile.md`, `preferences/`, `entities/`, and `events/`.
- Store agent-learned memories in MemoryHub under `.agents/memoryhub/agent/memories/`, using categories such as `cases/`, `patterns/`, `tools/`, and `skills/`.
- Store static project knowledge, documents, and other reference resources in MemoryHub under `.agents/memoryhub/resources/`.
- Store reusable agent capabilities and workflows in MemoryHub under `.agents/memoryhub/agent/skills/`.
- If the user's message refers to anything that may have been part of a past conversation but is not present in your context, search MemoryHub before answering.
- Anything the user asks you to remember must be recorded in MemoryHub memory.
- If you have **ANY** questions or concerns, **IMMEDIATELY** clarify with the user.
- Before making any changes to the codebase, THOROUGHLY plan out your work, write down every step you're going to take in ./.agents/TODO.md, and follow it during your work.
- Read a file fully before editing it.
- Keep comments rare and useful. Explain why or constraints, not obvious mechanics.
- Keep diffs narrow and task-focused.
- Do not guess at attribute names, control flow, or config behaviour.
- Prefer fail-fast behaviour over silent fallback logic.
- Add tests for new behaviour unless the change is strictly docs/metadata cleanup.
- Tick off every item you completed in ./.agents/TODO.md.
- After ticking off an item, commit the changes you made for that item
- When making commits, set the commit author name to `Coding agent supervised by {global git user.name}`, replacing `{global git user.name}` with the value from `git config --global user.name`
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
- If everything is ticked off in ./.agents/TODO.md and you need to plan for a new round of work, clear out ./.agents/TODO.md and write down your new list of steps
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
- Use MemoryHub for persistent memory and project context
- ALWAYS follow Answering rules

## MemoryHub Rules

- MemoryHub is mandatory for this project. Do not continue agent-basics workflows until the central MemoryHub installation is installed, initialized, and healthy.
- MemoryHub is the central OpenViking-backed memory hub for agent-basics projects. Do not install a separate OpenViking runtime, embedding model, or vector stack per repository.
- Use `MEMORYHUB_CONFIG_DIR="${MEMORYHUB_CONFIG_DIR:-$HOME/.memoryhub}"` for the central hub configuration and database.
- Add `$MEMORYHUB_CONFIG_DIR/venv/bin` to the front of `PATH` when invoking the central `memoryhub` executable installed by `setup-macos.sh`.
- This repo's MemoryHub markdown source belongs under `.agents/memoryhub/`.
- The central hub should expose this repo through a symlink at `$MEMORYHUB_CONFIG_DIR/projects/<project-name>` pointing back to `.agents/memoryhub/`.
- `setup-macos.sh` uses `EDITOR` for manual markdown conflict merges. If provider credentials or model endpoints are referenced through MemoryHub environment variables, document the exact variable names here before use and never commit raw secret values.
- Required MemoryHub environment variables:
  - `MEMORYHUB_CONFIG_DIR`: central MemoryHub config, database, venv, project symlink, and runtime state directory.
  - `MEMORYHUB_MCP_PROJECT`: optional project constraint when an agent or MCP server must be pinned to one project.
  - `MEMORYHUB_SEMANTIC_EMBEDDING_PROVIDER`, `MEMORYHUB_SEMANTIC_EMBEDDING_MODEL`, `MEMORYHUB_SEMANTIC_EMBEDDING_DIMENSIONS`, and `MEMORYHUB_SEMANTIC_EMBEDDING_BATCH_SIZE`: optional semantic search overrides. Do not set these unless the selected MemoryHub provider requires them.
- Validate MemoryHub with `memoryhub doctor` and `memoryhub project list --json` before migrating project content.
- Migrate legacy `.agents/DOCUMENTATIONS.md` content into `.agents/memoryhub/resources/legacy-documentations.md` before deleting the file.
- Migrate legacy `.agents/MEMORY.md` content into `.agents/memoryhub/user/memories/preferences/<project-name>.md` and `.agents/memoryhub/agent/memories/patterns/<project-name>.md` before deleting the file.
- Store user-specific memories under `.agents/memoryhub/user/memories/`.
- Store agent-learned memories under `.agents/memoryhub/agent/memories/`.
- Store static project references and documents under `.agents/memoryhub/resources/`.
- Store reusable agent skills and workflows under `.agents/memoryhub/agent/skills/`.
- Use concise markdown entries with clear titles, dates when relevant, and enough source context to make the memory useful later.
- Search MemoryHub when the user refers to previous work, preferences, prior conversations, or project context that is not in the visible chat.

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
    *)
      echo "Error: unknown template name: $name" >&2
      exit 1
      ;;
  esac

  printf "%s\n" "$template_file"
}

cd "$TARGET_DIR"
TARGET_DIR="$(pwd)"
PROJECT_NAME="${AGENT_BASICS_PROJECT_NAME:-$(slugify "$(basename "$TARGET_DIR")")}"
REPO_MEMORY_DIR="$TARGET_DIR/.agents/memoryhub"
HUB_PROJECT_LINK="$MEMORYHUB_PROJECTS_DIR/$PROJECT_NAME"
mkdir -p .agents

find_memoryhub_source_dir() {
  local candidate
  local -a candidates

  candidates=(
    "${MEMORYHUB_SOURCE_DIR:-}"
    "$SCRIPT_DIR/../MemoryHub"
    "$SCRIPT_DIR/../../MemoryHub"
    "/Users/leonardw/Projects/MemoryHub"
  )

  for candidate in "${candidates[@]}"; do
    if [[ -n "$candidate" && -f "$candidate/pyproject.toml" && -d "$candidate/src/memoryhub" ]]; then
      printf "%s\n" "$candidate"
      return 0
    fi
  done

  return 1
}

ensure_memoryhub_command() {
  local source_dir

  mkdir -p "$MEMORYHUB_CONFIG_DIR" "$MEMORYHUB_PROJECTS_DIR"

  if [[ -x "$MEMORYHUB_VENV_DIR/bin/memoryhub" ]]; then
    export PATH="$MEMORYHUB_VENV_DIR/bin:$PATH"
    MEMORYHUB_BIN="$MEMORYHUB_VENV_DIR/bin/memoryhub"
    return
  fi

  if command -v memoryhub >/dev/null 2>&1; then
    MEMORYHUB_BIN="$(command -v memoryhub)"
    return
  fi

  echo "MemoryHub is required by agent-basics, but no central memoryhub executable was found."
  if ! confirm_action "Install MemoryHub into $MEMORYHUB_VENV_DIR with uv?"; then
    echo "MemoryHub installation declined. agent-basics cannot continue." >&2
    exit 1
  fi

  if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv is required to create the central MemoryHub virtualenv." >&2
    exit 1
  fi

  if ! source_dir="$(find_memoryhub_source_dir)"; then
    echo "Error: MemoryHub source checkout was not found." >&2
    echo "Set MEMORYHUB_SOURCE_DIR to the local MemoryHub checkout, then rerun setup." >&2
    exit 1
  fi

  uv venv --python 3.12 "$MEMORYHUB_VENV_DIR"
  uv pip install --python "$MEMORYHUB_VENV_DIR/bin/python" -e "$source_dir"
  export PATH="$MEMORYHUB_VENV_DIR/bin:$PATH"
  MEMORYHUB_BIN="$MEMORYHUB_VENV_DIR/bin/memoryhub"

  if [[ ! -x "$MEMORYHUB_BIN" ]]; then
    echo "Error: MemoryHub install completed, but $MEMORYHUB_BIN is not executable." >&2
    exit 1
  fi
}

create_memoryhub_layout() {
  mkdir -p \
    "$REPO_MEMORY_DIR/agent/memories/cases" \
    "$REPO_MEMORY_DIR/agent/memories/patterns" \
    "$REPO_MEMORY_DIR/agent/memories/tools" \
    "$REPO_MEMORY_DIR/agent/memories/skills" \
    "$REPO_MEMORY_DIR/agent/skills" \
    "$REPO_MEMORY_DIR/backups" \
    "$REPO_MEMORY_DIR/merge-sessions" \
    "$REPO_MEMORY_DIR/resources/agent-basics/setup" \
    "$REPO_MEMORY_DIR/setup-state" \
    "$REPO_MEMORY_DIR/user/memories/entities" \
    "$REPO_MEMORY_DIR/user/memories/events" \
    "$REPO_MEMORY_DIR/user/memories/preferences"

  if [[ ! -f "$REPO_MEMORY_DIR/README.md" ]]; then
    cat > "$REPO_MEMORY_DIR/README.md" <<'EOT'
# MemoryHub

This directory contains repo-local markdown source for the central MemoryHub installation used by agent-basics.

The central hub should be configured with `MEMORYHUB_CONFIG_DIR`, usually `$HOME/.memoryhub`. Its `projects/` directory links back to this directory so the project owns its memory files while the hub owns the runtime, database, embeddings, and MCP/API surface.

Suggested categories:

- `user/memories/`: user profile, preferences, entities, and events
- `agent/memories/`: agent-learned cases, patterns, tools, and skills
- `agent/skills/`: reusable workflows and capabilities
- `resources/`: static project documents and documentation source records
EOT
    echo "Created: .agents/memoryhub/README.md"
  fi
}

backup_existing_file() {
  local file_path="$1"
  local timestamp
  local backup_name
  timestamp="$(date +%Y%m%d%H%M%S)"
  backup_name="${file_path//\//__}.$timestamp.bak"

  mkdir -p "$REPO_MEMORY_DIR/backups"
  cp "$file_path" "$REPO_MEMORY_DIR/backups/$backup_name"
  echo "Backed up existing file: .agents/memoryhub/backups/$backup_name"
}

ensure_hub_symlink() {
  mkdir -p "$MEMORYHUB_PROJECTS_DIR"

  if [[ -L "$HUB_PROJECT_LINK" ]]; then
    local current_target
    local resolved_target
    current_target="$(readlink "$HUB_PROJECT_LINK")"
    if [[ "$current_target" != /* ]]; then
      current_target="$(dirname "$HUB_PROJECT_LINK")/$current_target"
    fi
    resolved_target="$(absolute_path "$current_target" 2>/dev/null || true)"
    if [[ "$resolved_target" == "$REPO_MEMORY_DIR" ]]; then
      echo "Exists: $HUB_PROJECT_LINK -> $REPO_MEMORY_DIR"
      return
    fi
  fi

  if [[ ! -e "$HUB_PROJECT_LINK" && ! -L "$HUB_PROJECT_LINK" ]]; then
    ln -s "$REPO_MEMORY_DIR" "$HUB_PROJECT_LINK"
    echo "Created hub symlink: $HUB_PROJECT_LINK -> $REPO_MEMORY_DIR"
    return
  fi

  echo "MemoryHub project path already exists and does not point at this repo: $HUB_PROJECT_LINK"
  if ! confirm_action "Move the existing path aside and create the agent-basics symlink?"; then
    echo "Keeping existing MemoryHub project path. Registering repo-local path directly instead." >&2
    HUB_PROJECT_LINK="$REPO_MEMORY_DIR"
    return
  fi

  local backup_path
  backup_path="$MEMORYHUB_PROJECTS_DIR/$PROJECT_NAME.backup.$(date +%Y%m%d%H%M%S)"
  mv "$HUB_PROJECT_LINK" "$backup_path"
  ln -s "$REPO_MEMORY_DIR" "$HUB_PROJECT_LINK"
  echo "Moved existing hub path to: $backup_path"
  echo "Created hub symlink: $HUB_PROJECT_LINK -> $REPO_MEMORY_DIR"
}

memoryhub_project_exists() {
  local list_file
  list_file="$(mktemp "${TMPDIR:-/tmp}/agent-basics-memoryhub-projects.XXXXXX.json")"

  if ! MEMORYHUB_CONFIG_DIR="$MEMORYHUB_CONFIG_DIR" "$MEMORYHUB_BIN" project list --json > "$list_file"; then
    rm -f "$list_file"
    return 1
  fi

  if python3 - "$PROJECT_NAME" "$list_file" <<'PY'
import json
import sys

project_name = sys.argv[1]
list_file = sys.argv[2]
payload = json.loads(open(list_file, encoding="utf-8").read())
projects = payload.get("projects", [])
sys.exit(0 if any(project.get("name") == project_name for project in projects) else 1)
PY
  then
    rm -f "$list_file"
    return 0
  fi

  rm -f "$list_file"
  return 1
}

register_memoryhub_project() {
  if memoryhub_project_exists; then
    echo "MemoryHub project already registered: $PROJECT_NAME"
    return
  fi

  MEMORYHUB_CONFIG_DIR="$MEMORYHUB_CONFIG_DIR" "$MEMORYHUB_BIN" project add "$PROJECT_NAME" "$HUB_PROJECT_LINK"
}

ensure_memoryhub_ready() {
  ensure_memoryhub_command
  create_memoryhub_layout
  ensure_hub_symlink

  MEMORYHUB_CONFIG_DIR="$MEMORYHUB_CONFIG_DIR" "$MEMORYHUB_BIN" doctor
  MEMORYHUB_CONFIG_DIR="$MEMORYHUB_CONFIG_DIR" "$MEMORYHUB_BIN" project list --json >/dev/null
  register_memoryhub_project
}

migrate_file_if_missing() {
  local source_path="$1"
  local destination_path="$2"

  if [[ ! -f "$source_path" || -f "$destination_path" ]]; then
    return
  fi

  mkdir -p "$(dirname "$destination_path")"
  cp "$source_path" "$destination_path"
  echo "Migrated: $source_path -> ${destination_path#$TARGET_DIR/}"
}

migrate_legacy_context_to_memoryhub() {
  migrate_file_if_missing \
    ".agents/DOCUMENTATIONS.md" \
    "$REPO_MEMORY_DIR/resources/legacy-documentations.md"
  migrate_file_if_missing \
    ".agents/MEMORY.md" \
    "$REPO_MEMORY_DIR/user/memories/preferences/$PROJECT_NAME.md"
  migrate_file_if_missing \
    ".agents/MEMORY.md" \
    "$REPO_MEMORY_DIR/agent/memories/patterns/$PROJECT_NAME.md"
  migrate_file_if_missing \
    ".agents/openviking/data/viking/default/resources/agent-basics/documentations/legacy-documentations.md" \
    "$REPO_MEMORY_DIR/resources/legacy-documentations.md"
  migrate_file_if_missing \
    ".agents/openviking/data/viking/default/user/default/memories/preferences/agent-basics.md" \
    "$REPO_MEMORY_DIR/user/memories/preferences/agent-basics.md"
  migrate_file_if_missing \
    ".agents/openviking/data/viking/default/agent/default/memories/patterns/agent-basics.md" \
    "$REPO_MEMORY_DIR/agent/memories/patterns/agent-basics.md"

  cat > "$REPO_MEMORY_DIR/resources/agent-basics/setup/last-setup.md" <<EOT
# agent-basics setup

- Project: $PROJECT_NAME
- Repository: $TARGET_DIR
- MemoryHub config: $MEMORYHUB_CONFIG_DIR
- Hub project path: $HUB_PROJECT_LINK
- Repo memory source: $REPO_MEMORY_DIR
- Updated: $(date -u +%Y-%m-%dT%H:%M:%SZ)
EOT
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

  if [[ ! -t 0 ]]; then
    echo "Error: $file_path conflicts with the agent-basics template, and stdin is not interactive." >&2
    echo "Run the command in a terminal to choose keep, replace, append, manual merge, or save-beside." >&2
    exit 1
  fi

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

  merge_file="$REPO_MEMORY_DIR/merge-sessions/$(basename "$destination_path").$(date +%Y%m%d%H%M%S).md"
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

ensure_memoryhub_ready
migrate_legacy_context_to_memoryhub

agents_template="$(create_template_file "agents")"
instructions_template="$(create_template_file "instructions")"
trap 'rm -f "$agents_template" "$instructions_template"' EXIT

copy_or_merge_markdown_file "$agents_template" "Agents.md"
copy_or_merge_markdown_file "$instructions_template" ".agents/INSTRUCTIONS.md"
create_empty_file_if_missing ".agents/TODO.md"

append_gitignore_entry_if_missing ".agents/TODO.md"
append_gitignore_entry_if_missing ".agents/memoryhub/backups/"
append_gitignore_entry_if_missing ".agents/memoryhub/merge-sessions/"
append_gitignore_entry_if_missing ".agents/memoryhub/setup-state/"

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Git repository already initialized"
else
  git init >/dev/null
  echo "Initialized empty Git repository"
fi

for markdown_file in "Agents.md" ".agents/INSTRUCTIONS.md" ".agents/TODO.md" ".agents/memoryhub/README.md"; do
  ensure_trailing_blank_line "$markdown_file"
done
