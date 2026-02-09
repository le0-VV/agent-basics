#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${1:-$(pwd)}"

if [[ ! -d "$TARGET_DIR" ]]; then
  echo "Error: target directory does not exist: $TARGET_DIR" >&2
  exit 1
fi

cd "$TARGET_DIR"

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

prompt_existing_file_action() {
  local file_path="$1"
  local choice

  while true; do
    read -r -p "$file_path exists and is not empty. Append new content (a) or overwrite (o)? [a/o]: " choice
    case "${choice}" in
      a|A)
        echo "append"
        return
        ;;
      o|O)
        echo "overwrite"
        return
        ;;
      *)
        echo "Invalid choice: $choice"
        ;;
    esac
  done
}

write_or_merge_instruction_file() {
  local file_path="$1"
  local content="$2"
  local action

  if [[ ! -e "$file_path" ]]; then
    printf "%s" "$content" > "$file_path"
    echo "Created: $file_path"
    return
  fi

  if [[ ! -s "$file_path" ]]; then
    printf "%s" "$content" > "$file_path"
    echo "Updated empty file: $file_path"
    return
  fi

  action=$(prompt_existing_file_action "$file_path")
  if [[ "$action" == "append" ]]; then
    printf "\n%s" "$content" >> "$file_path"
    echo "Appended content: $file_path"
    return
  fi

  printf "%s" "$content" > "$file_path"
  echo "Overwrote content: $file_path"
}

mkdir -p .agents

agents_md_content=$(cat <<'EOT'
# **YOU MUST:**

- **DO NOT, UNDER ANY CIRCUMSTANCES, UNLESS EXPLICITLY INSTRUCTED BY THE USER**, modify this file or ./.agents/INSTRUCTIONS.md
- Follow the instructions of ./.agents/INSTRUCTIONS.md
- Find up-to-date documentations for any library, framework and programming languages used in this project, and record their source URLs in ./.agents/DOCUMENTATIONS.md
- While you write code, **CONSTANTLY** refer to sources you recorded in ./.agents/DOCUMENTATIONS.md to make sure you're writing accurate, working and standard-complying code.
- Anything the user asks you to remember, record it in ./.agents/MEMORY.md
- If the user's message referred to anything that may have been part of a past conversation, but is not present in your context, check ./.agents/MEMORY.md
- When .agents/DOCUMENTATIONS.md is updated, commit ONLY .agents/DOCUMENTATIONS.md with commit message: "docs(agent docs): agent added more doc sources"
- When .agents/MEMORY.md is updated, commit ONLY .agents/MEMORY.md with commit message: "docs(agent memory): update memory"
- If you have **ANY** questions or concerns, **IMMEDIATELY** clarify with the user.
- Before making any changes to the codebase, THOROUGHLY plan out your work, write down every step you're going to take in ./.agents/TODO.md, and follow it during your work.
- Tick off every item you completed in ./.agents/TODO.md.
- **Only** stop working when you finished everything listed in /.agents/TODO.md **OR** you encountered an interruption to your work that **REQUIRES** user intervention.
- If everything is ticked off in ./.agents/TODO.md and you need to plan for a new round of work, clear out ./.agents/TODO.md and write down your new list of steps
EOT
)

instructions_md_content=$(cat <<'EOT'
# INSTRUCTIONS

You **MUST** ALWAYS:

- **BE LOGICAL**
- **ONLY IF** you working with coding tasks: I have no fingers and the placeholders trauma: **NEVER** use placeholders or omit the code (in any code snippets)
- If you encounter a character limit, **DO** an **ABRUPT** stop; I will send a "continue" as a new message
- You will be **PENALISED** for wrong answers
- You **DENIED** to overlook the critical context
- ALWAYS follow Answering rules

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
)

write_or_merge_instruction_file "Agents.md" "$agents_md_content"
write_or_merge_instruction_file ".agents/INSTRUCTIONS.md" "$instructions_md_content"
create_empty_file_if_missing ".agents/DOCUMENTATIONS.md"
create_empty_file_if_missing ".agents/MEMORY.md"
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

for markdown_file in "Agents.md" ".agents/INSTRUCTIONS.md" ".agents/DOCUMENTATIONS.md" ".agents/MEMORY.md" ".agents/TODO.md"; do
  ensure_trailing_blank_line "$markdown_file"
done
