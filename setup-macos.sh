#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${1:-$(pwd)}"

if [[ ! -d "$TARGET_DIR" ]]; then
  echo "Error: target directory does not exist: $TARGET_DIR" >&2
  exit 1
fi

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
- OpenViking is mandatory for this project. Do not use agent-basics workflows until OpenViking is installed, initialized, and healthy.
- Before running OpenViking commands for this repo, export `PATH="$PWD/.agents/openviking/venv/bin:$PATH"`, `OPENVIKING_CONFIG_FILE="$PWD/.agents/openviking/ov.conf"`, and `OPENVIKING_CLI_CONFIG_FILE="$PWD/.agents/openviking/ovcli.conf"`.
- Find up-to-date documentations for any library, framework and programming languages used in this project, and record their source URLs in OpenViking under `viking://resources/`.
- While you write code, **CONSTANTLY** refer to documentation sources recorded in OpenViking to make sure you're writing accurate, working and standard-complying code.
- Store user-specific memories in OpenViking under `viking://user/memories/`, using the documented categories such as `profile.md`, `preferences/`, `entities/`, and `events/`.
- Store agent-learned memories in OpenViking under `viking://agent/memories/`, using the documented categories such as `cases/`, `patterns/`, `tools/`, and `skills/`.
- Store static project knowledge, documents, and other reference resources in OpenViking under `viking://resources/`.
- Store reusable agent capabilities and workflows in OpenViking under `viking://agent/skills/`.
- If the user's message refers to anything that may have been part of a past conversation but is not present in your context, search OpenViking memory before answering.
- Anything the user asks you to remember must be recorded in OpenViking memory.
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
- Use OpenViking for persistent memory and project context
- ALWAYS follow Answering rules

## OpenViking Memory Rules

- OpenViking is mandatory for this project. Do not continue agent-basics workflows until OpenViking is installed, initialized, and healthy.
- Use the project-local OpenViking virtualenv at `.agents/openviking/venv` when it exists.
- Export `OPENVIKING_CONFIG_FILE="$PWD/.agents/openviking/ov.conf"` before running OpenViking server, SDK, or CLI commands for this repo.
- Export `OPENVIKING_CLI_CONFIG_FILE="$PWD/.agents/openviking/ovcli.conf"` before running `ov` CLI commands for this repo.
- Add `.agents/openviking/venv/bin` to the front of `PATH` when invoking `openviking-server`, `openviking`, or `ov` for this repo.
- `setup-macos.sh` uses `EDITOR` for manual markdown conflict merges. If provider credentials are referenced through environment variables in `ov.conf`, document the exact variable names here before use and never commit raw secret values.
- Keep OpenViking storage, setup state, exports, backups, and merge sessions under `.agents/openviking/`.
- Validate OpenViking with `openviking-server doctor` before migrating project content. If doctor reports missing embedding or VLM configuration, fix the OpenViking config or install the required extras before continuing.
- Migrate legacy `.agents/DOCUMENTATIONS.md` content into OpenViking resources under `viking://resources/agent-basics/documentations/` before deleting the file.
- Migrate legacy `.agents/MEMORY.md` content into OpenViking memory/resource paths before deleting the file. Use `viking://user/memories/` for user preferences and `viking://agent/memories/` for agent-learned project patterns.
- Store user-specific memories under `viking://user/memories/`.
- Store agent-learned memories under `viking://agent/memories/`.
- Store static project references and documents under `viking://resources/`.
- Store reusable agent skills and workflows under `viking://agent/skills/`.
- Use concise markdown entries with clear titles, dates when relevant, and enough source context to make the memory useful later.
- Search OpenViking memory when the user refers to previous work, preferences, prior conversations, or project context that is not in the visible chat.

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
mkdir -p .agents

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
      y|Y)
        return 0
        ;;
      n|N)
        return 1
        ;;
      *)
        echo "Invalid choice: $choice" >&2
        ;;
    esac
  done
}

create_openviking_layout() {
  mkdir -p \
    .agents/openviking/backups \
    .agents/openviking/data \
    .agents/openviking/exports \
    .agents/openviking/merge-sessions \
    .agents/openviking/setup-state

  if [[ ! -f ".agents/openviking/README.md" ]]; then
    cat > ".agents/openviking/README.md" <<'EOT'
# OpenViking

This directory contains project-local OpenViking integration files for agent-basics.

Keep OpenViking configuration, setup state, backups, exports, and merge sessions under this directory when OpenViking's documented configuration model allows project-local placement.

Use these environment variables before running OpenViking commands for this repo:

```bash
export PATH="$PWD/.agents/openviking/venv/bin:$PATH"
export OPENVIKING_CONFIG_FILE="$PWD/.agents/openviking/ov.conf"
export OPENVIKING_CLI_CONFIG_FILE="$PWD/.agents/openviking/ovcli.conf"
```
EOT
    echo "Created: .agents/openviking/README.md"
  fi
}

create_default_openviking_config() {
  local ov_config="$1"
  local ov_cli_config="$2"

  if [[ ! -f "$ov_config" ]]; then
    cat > "$ov_config" <<'EOT'
{
  "storage": {
    "workspace": ".agents/openviking/data"
  },
  "embedding": {
    "dense": {
      "provider": "litellm",
      "model": "text-embedding-3-small",
      "api_key": "no-key",
      "api_base": "http://127.0.0.1:9",
      "dimension": 1536
    }
  },
  "vlm": {
    "provider": "litellm",
    "model": "gpt-4o-mini",
    "api_key": "no-key",
    "api_base": "http://127.0.0.1:9"
  },
  "server": {
    "host": "127.0.0.1",
    "port": 1933
  }
}
EOT
    echo "Created: .agents/openviking/ov.conf"
  fi

  if [[ ! -f "$ov_cli_config" ]]; then
    cat > "$ov_cli_config" <<'EOT'
{
  "url": "http://127.0.0.1:1933",
  "timeout": 60,
  "output": "table"
}
EOT
    echo "Created: .agents/openviking/ovcli.conf"
  fi
}

ensure_openviking_command() {
  if [[ -x ".agents/openviking/venv/bin/openviking-server" ]]; then
    export PATH="$TARGET_DIR/.agents/openviking/venv/bin:$PATH"
    return
  fi

  echo "OpenViking is required by agent-basics, but .agents/openviking/venv is not ready."
  if ! confirm_action "Install OpenViking into .agents/openviking/venv with uv?"; then
    echo "OpenViking installation declined. agent-basics cannot continue." >&2
    exit 1
  fi

  if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv is required to create the project-local OpenViking virtualenv." >&2
    echo "Install uv, then rerun agent-basics." >&2
    exit 1
  fi

  uv venv --python 3.12 .agents/openviking/venv
  uv pip install --python .agents/openviking/venv/bin/python openviking --upgrade --force-reinstall
  export PATH="$TARGET_DIR/.agents/openviking/venv/bin:$PATH"

  if ! command -v openviking-server >/dev/null 2>&1; then
    echo "Error: OpenViking install completed, but openviking-server is still not available." >&2
    exit 1
  fi
}

ensure_openviking_ready() {
  local ov_config
  local ov_cli_config
  ov_config="$TARGET_DIR/.agents/openviking/ov.conf"
  ov_cli_config="$TARGET_DIR/.agents/openviking/ovcli.conf"

  create_openviking_layout
  ensure_openviking_command

  export OPENVIKING_CONFIG_FILE="$ov_config"
  export OPENVIKING_CLI_CONFIG_FILE="$ov_cli_config"

  if [[ ! -f "$ov_config" || ! -f "$ov_cli_config" ]]; then
    create_default_openviking_config "$ov_config" "$ov_cli_config"
  fi

  openviking-server doctor
}

ensure_openviking_ready

migrate_legacy_context_to_openviking() {
  local migration_needed=0
  local archive_dir

  if [[ -f ".agents/DOCUMENTATIONS.md" ]]; then
    migration_needed=1
  fi
  if [[ -f ".agents/MEMORY.md" ]]; then
    migration_needed=1
  fi

  if [[ "$migration_needed" -eq 0 ]]; then
    return
  fi

  echo "Migrating legacy .agents markdown context into OpenViking."
  OPENVIKING_CONFIG_FILE="$OPENVIKING_CONFIG_FILE" \
  OPENVIKING_CLI_CONFIG_FILE="$OPENVIKING_CLI_CONFIG_FILE" \
  "$TARGET_DIR/.agents/openviking/venv/bin/python" <<'PY'
from pathlib import Path

from openviking.client.local import LocalClient
from openviking_cli.utils import run_async


ROOT = Path.cwd()


async def mkdir_p(client, parts):
    current = ""
    for part in parts:
        current = f"{current}/{part}" if current else part
        try:
            await client.mkdir(f"viking://{current}")
        except Exception:
            pass


async def write_if_file(client, source, target_uri):
    path = ROOT / source
    if not path.exists():
        return False
    await write_uri(client, target_uri, path.read_text(encoding="utf-8"))
    return True


async def write_uri(client, target_uri, content):
    mode = "replace"
    try:
        await client.stat(target_uri)
    except Exception:
        mode = "create"
    await client.write(target_uri, content, mode=mode, wait=False)
    actual = await client.read(target_uri)
    if actual.rstrip("\n") != content.rstrip("\n"):
        raise RuntimeError(f"OpenViking verification failed for {target_uri}")


async def main():
    client = LocalClient(path=str(ROOT / ".agents/openviking/data"))
    await client.initialize()
    await mkdir_p(client, ["resources", "agent-basics", "documentations"])
    await mkdir_p(client, ["user", "memories", "preferences"])
    await mkdir_p(client, ["agent", "memories", "patterns"])

    migrated = []
    if await write_if_file(
        client,
        ".agents/DOCUMENTATIONS.md",
        "viking://resources/agent-basics/documentations/legacy-documentations.md",
    ):
        migrated.append(".agents/DOCUMENTATIONS.md -> viking://resources/agent-basics/documentations/legacy-documentations.md")

    memory_path = ROOT / ".agents/MEMORY.md"
    if memory_path.exists():
        memory_text = memory_path.read_text(encoding="utf-8")
        await write_uri(
            client,
            "viking://user/memories/preferences/agent-basics.md",
            memory_text,
        )
        await write_uri(
            client,
            "viking://agent/memories/patterns/agent-basics.md",
            memory_text,
        )
        migrated.append(".agents/MEMORY.md -> viking://user/memories/preferences/agent-basics.md")
        migrated.append(".agents/MEMORY.md -> viking://agent/memories/patterns/agent-basics.md")

    report = "\n".join(migrated) + "\n"
    report_path = ROOT / ".agents/openviking/setup-state/legacy-markdown-migration.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    for line in migrated:
        print(f"Migrated: {line}")

    await client.close()


run_async(main())
PY

  archive_dir=".agents/openviking/backups/legacy-context-$(date +%Y%m%d%H%M%S)"
  mkdir -p "$archive_dir"
  for legacy_file in ".agents/DOCUMENTATIONS.md" ".agents/MEMORY.md"; do
    if [[ -f "$legacy_file" ]]; then
      mv "$legacy_file" "$archive_dir/$(basename "$legacy_file")"
      echo "Archived migrated legacy file: $archive_dir/$(basename "$legacy_file")"
    fi
  done
}

migrate_legacy_context_to_openviking

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

  # Ensure newline at EOF.
  if [[ -n "$(tail -c 1 "$file_path" 2>/dev/null)" ]]; then
    printf "\n" >> "$file_path"
  fi

  # Ensure one additional empty trailing line.
  if [[ -n "$(tail -n 1 "$file_path")" ]]; then
    printf "\n" >> "$file_path"
  fi
}

backup_existing_file() {
  local file_path="$1"
  local timestamp
  local backup_name
  timestamp="$(date +%Y%m%d%H%M%S)"
  backup_name="${file_path//\//__}.$timestamp.bak"

  mkdir -p .agents/openviking/backups
  cp "$file_path" ".agents/openviking/backups/$backup_name"
  echo "Backed up existing file: .agents/openviking/backups/$backup_name"
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
      k|K)
        printf "k\n"
        return
        ;;
      r|R)
        printf "r\n"
        return
        ;;
      a|A)
        printf "a\n"
        return
        ;;
      m|M)
        printf "m\n"
        return
        ;;
      s|S)
        printf "s\n"
        return
        ;;
      *)
        echo "Invalid choice: $choice" >&2
        ;;
    esac
  done
}

manual_merge_file() {
  local source_path="$1"
  local destination_path="$2"
  local merge_file
  local editor
  local apply_choice

  merge_file="$(mktemp "${TMPDIR:-/tmp}/agent-basics-merge.XXXXXX.md")"
  editor="${EDITOR:-vi}"

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

agents_template="$(create_template_file "agents")"
instructions_template="$(create_template_file "instructions")"
trap 'rm -f "$agents_template" "$instructions_template"' EXIT

copy_or_merge_markdown_file "$agents_template" "Agents.md"
copy_or_merge_markdown_file "$instructions_template" ".agents/INSTRUCTIONS.md"
create_empty_file_if_missing ".agents/TODO.md"

gitignore_entry=".agents/TODO.md"
if [[ ! -e ".gitignore" ]]; then
  printf "%s\n" "$gitignore_entry" > .gitignore
  echo "Created: .gitignore"
else
  if grep -Fxq "$gitignore_entry" .gitignore; then
    echo "No changes: .gitignore already contains $gitignore_entry"
  else
    printf "\n%s\n" "$gitignore_entry" >> .gitignore
    echo "Appended entry to .gitignore: $gitignore_entry"
  fi
fi

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Git repository already initialized"
else
  git init >/dev/null
  echo "Initialized empty Git repository"
fi

for markdown_file in "Agents.md" ".agents/INSTRUCTIONS.md" ".agents/TODO.md" ".agents/openviking/README.md"; do
  ensure_trailing_blank_line "$markdown_file"
done
