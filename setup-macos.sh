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
REPO_SKILLS_DIR="$REPO_AGENTS_DIR/skills"
RAG_DIR="$REPO_MEMORY_ROOT/rag"
EMBEDDING_API_DIR="$RAG_DIR/embedding-api"
AGENT_BASICS_CONFIG_HOME="${AGENT_BASICS_CONFIG_HOME:-${AGENT_BASICS_HOME:-$HOME/.agent-basics}}"
AGENT_BASICS_CONFIG_FILE="${AGENT_BASICS_CONFIG_FILE:-$AGENT_BASICS_CONFIG_HOME/config.toml}"
RAW_AGENT_BASICS_LANGUAGE="${AGENT_BASICS_LANGUAGE:-}"
AGENT_BASICS_LANGUAGE_EXPLICIT="${AGENT_BASICS_LANGUAGE_EXPLICIT:-0}"

if [[ -n "$RAW_AGENT_BASICS_LANGUAGE" && "$AGENT_BASICS_LANGUAGE_EXPLICIT" == "0" ]]; then
  AGENT_BASICS_LANGUAGE_EXPLICIT=1
fi

detect_agent_basics_language() {
  case "${LANG:-}${LC_ALL:-}${LC_MESSAGES:-}" in
    zh*|*zh_CN*|*zh-CN*|*zh_Hans*|*Chinese*)
      printf "zh-CN\n"
      ;;
    *)
      printf "en\n"
      ;;
  esac
}

normalize_agent_basics_language() {
  local value="$1"
  local lowered

  lowered="$(printf "%s" "$value" | tr '[:upper:]' '[:lower:]' | tr '_' '-')"
  case "$lowered" in
    ""|en|en-us|en-gb)
      printf "en\n"
      ;;
    auto)
      detect_agent_basics_language
      ;;
    zh|zh-cn|zh-hans|cn|chinese|simplified-chinese)
      printf "zh-CN\n"
      ;;
    *)
      echo "Error: unsupported agent-basics language: $value" >&2
      echo "Supported values: en, zh-CN, auto" >&2
      exit 2
      ;;
  esac
}

read_agent_basics_install_language() {
  local config_file="$AGENT_BASICS_CONFIG_FILE"

  [[ -f "$config_file" ]] || return 1
  python3 - "$config_file" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path


path = Path(sys.argv[1])
current_section = ""

for raw_line in path.read_text(encoding="utf-8").splitlines():
    line = raw_line.split("#", 1)[0].strip()
    if not line:
        continue
    if line.startswith("[") and line.endswith("]"):
        current_section = line.strip("[]").strip()
        continue
    if current_section != "agent_basics" or "=" not in line:
        continue
    key, value = line.split("=", 1)
    if key.strip() != "language":
        continue
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    print(value)
    raise SystemExit(0)

raise SystemExit(1)
PY
}

resolve_agent_basics_language() {
  local configured_language

  if [[ -n "$RAW_AGENT_BASICS_LANGUAGE" ]]; then
    normalize_agent_basics_language "$RAW_AGENT_BASICS_LANGUAGE"
    return
  fi

  if configured_language="$(read_agent_basics_install_language 2>/dev/null)"; then
    normalize_agent_basics_language "$configured_language"
    return
  fi

  normalize_agent_basics_language "en"
}

AGENT_BASICS_LANGUAGE="$(resolve_agent_basics_language)"
export AGENT_BASICS_LANGUAGE

agent_basics_language_is_zh() {
  [[ "$AGENT_BASICS_LANGUAGE" == "zh-CN" ]]
}

write_agent_basics_install_language() {
  local config_file="$AGENT_BASICS_CONFIG_FILE"
  local existed="0"

  if [[ -f "$config_file" ]]; then
    existed="1"
  fi

  mkdir -p "$(dirname "$config_file")"
  python3 - "$config_file" "$AGENT_BASICS_LANGUAGE" <<'PY'
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


path = Path(sys.argv[1])
language = sys.argv[2]
line = f"language = {json.dumps(language)}"

if path.exists():
    text = path.read_text(encoding="utf-8")
else:
    text = "version = 1\n"

section_re = re.compile(r"(?ms)^\[agent_basics\]\n(?P<body>.*?)(?=^\[|\Z)")
match = section_re.search(text)

if match:
    body = match.group("body")
    if re.search(r"(?m)^language\s*=", body):
        body = re.sub(r"(?m)^language\s*=.*$", line, body)
    else:
        if body and not body.endswith("\n"):
            body += "\n"
        body += line + "\n"
    text = text[: match.start("body")] + body + text[match.end("body") :]
else:
    if text and not text.endswith("\n"):
        text += "\n"
    text += f"\n[agent_basics]\n{line}\n"

path.write_text(text, encoding="utf-8")
PY

  if [[ "$existed" == "1" ]]; then
    echo "Updated: $config_file language = $AGENT_BASICS_LANGUAGE"
  else
    echo "Created: $config_file"
  fi
}

ensure_agent_basics_install_config() {
  if [[ "$AGENT_BASICS_LANGUAGE_EXPLICIT" == "1" ]]; then
    write_agent_basics_install_language
    return
  fi

  if read_agent_basics_install_language >/dev/null 2>&1; then
    echo "Exists: $AGENT_BASICS_CONFIG_FILE"
    return
  fi

  write_agent_basics_install_language
}

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
- Use `Skills.md` and `.agents/skills/` for repeatable workflows before inventing new process.
- The `.agents/memory/` mini-RAG is legacy fallback compatibility only. Use it only when OpenViking tooling is unavailable and work must continue.
- If you must use the compatibility memory layer, prefer the compatibility MCP tools `memory_search` and `memory_record` when that server is configured. Otherwise fall back to `agent-basics memory ...` or `.agents/memory/rag/agent-memory.py ...`.
- Do not edit `.agents/memory/**` while `.agents/memory/rag/write.lock/` exists.

## Work Rules

- When delegation is available and useful, prefer subagents working in their own branch or worktree with clear ownership.
- Subagents must not spawn their own subagents unless the user explicitly asks for nested delegation.
- The main agent owns supervision: review, integrate, resolve conflicts, and merge subagent work after they finish.
- Before making codebase changes, write the concrete plan in `.agents/TODO.md` and follow it.
- For non-trivial or long-running work, preserve direction in `ROADMAP.md` and current state in `.agents/TODO.md`.
- Read a file fully before editing it.
- Keep comments rare and useful. Explain why or constraints, not obvious mechanics.
- Keep diffs narrow and task-focused.
- Do not guess at attribute names, control flow, or config behavior.
- Prefer fail-fast behavior over silent fallback logic.
- Add tests for new behavior unless the change is strictly docs/metadata cleanup.
- Tick off every completed item in `.agents/TODO.md`.
- Commit each completed logical unit when the repo is verified and the staged changes are coherent.
- Only stop working when everything in `.agents/TODO.md` is complete or you are blocked by something that requires user intervention.
- If everything is ticked off in `.agents/TODO.md` and a new work round is needed, clear it and write the new plan.

## Commits

- Set commit author name to `Coding agent supervised by {global git user.name}`, replacing `{global git user.name}` with `git config --global user.name`.
- Use the global git email unless the user explicitly instructs otherwise.
- Write commit messages as `{type}({scope}): {description}`.
- Use one of these commit types: `build`, `chore`, `CI`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test`.

## Answering Rules

Follow in this order:

1. Use the language of the user's message when it is clear.
2. If the user's language is ambiguous, use the installation language in `~/.agent-basics/config.toml` under `[agent_basics].language`.
3. If `[agent_basics].language` is `zh-CN`, use Simplified Chinese for user-facing explanations unless the user asks otherwise.
4. Search OpenViking or the compatibility memory layer before relying on assumptions about prior work.
5. Combine project context and clear reasoning to answer with concrete details.
6. Keep answers direct and actionable.
EOT
      ;;
    agent-basics)
      cat > "$template_file" <<'EOT'
# agent-basics Operating Manual

This file contains agent-basics-specific operating rules. `Agents.md` contains the base agent contract and must stay at the project root so agents discover it reliably.

## OpenViking Context Backend

- OpenViking is the required target backend for agent-basics memory, documentation, resources, skills, semantic organization, and retrieval.
- Agents should not call OpenViking with ad hoc commands when an agent-basics gateway exists. Use the repo-aware `agent-basics mcp` server or stable `agent-basics ov ...` commands.
- Repository-specific OpenViking config, workspace, import state, metadata, and locks should live under `.agents/openviking/`. Only the OpenViking package/runtime should live in the user-level installation, normally `~/.openviking`.
- `agent-basics` owns setup, upgrade, validation, repo path resolution, git hooks, migration safety, and agent-facing command/MCP contracts.
- OpenViking owns durable context storage, resource ingestion, summaries, semantic search, and vector indexes.
- Before making context-dependent claims, search OpenViking through the gateway.
- Record durable decisions, facts, preferences, gotchas, events, documentation sources, procedures, and reusable skills through the gateway.
- Do not store secrets in OpenViking entries or agent-basics config. Store secret environment variable names only.

## Gateway Contract

The target agent-facing surfaces are:

- `agent-basics mcp`: repo-aware MCP server for OpenViking-backed tools.
- `agent-basics ov doctor`: check the user-level OpenViking installation, repo config, providers, ingest status, and health.
- `agent-basics ov bootstrap-system`: install OpenViking under `~/.openviking` when missing, package the server as `~/.openviking/openviking`, and prepare default runtime/provider config. Repo setup owns repo-local OpenViking config and service setup.
- `agent-basics ov package-server`: build the OpenViking server entrypoint into a one-file `openviking` executable so macOS process listings do not show the long-running service as `python3.12`.
- `agent-basics mlx bootstrap`: on Apple Silicon Macs with at least 16 GB unified memory, install the lightweight MLX runtime, pull the configured Hugging Face chat/embedding models when needed, and check the local OpenAI-compatible API.
- `agent-basics ov write-default-config --provider custom`: point OpenViking at a user-supplied OpenAI-compatible API provider.
- `agent-basics ov install-system`: low-level repair command for only the OpenViking package installation.
- `agent-basics ov write-default-config`: low-level repair command for OpenViking `ov.conf` and `ovcli.conf` for the configured local provider.
- `agent-basics ov service install --repo-local`: install and load the repo-local OpenViking HTTP server as a macOS LaunchAgent, using the shared `~/.openviking/openviking` executable and repo-local `.agents/openviking/ov.conf`.
- `agent-basics ov server`: start the repo-local OpenViking HTTP server in the foreground for debugging.
- `agent-basics ov import-repo-memory`: write `.agents/memory/` OV-native memories into OpenViking memory categories and ingest resources/skills.
- `agent-basics ov search <query>`: retrieve prior context for vague or specific project requests.
- `agent-basics ov record`: record durable context in the correct OpenViking category.
- `agent-basics ov add-resource <path-or-url>`: ingest documentation or reference material.
- `agent-basics ov add-skill <path>`: register reusable agent workflows.
- `agent-basics ov ingest-changed`: update OpenViking after source instructions, docs, or memory files change.
- `agent-basics ov install-hooks`: install repo-local hooks that refresh OpenViking after source-store changes.
- `agent-basics ov status`: report repo-specific OpenViking state.

When configuring an MCP-capable agent, prefer a systemwide `agent-basics` command without a fixed working directory. Agents should pass their current working directory through the `cwd` tool argument on each repo-scoped call:

```json
{
  "mcpServers": {
    "agent-basics": {
      "command": "agent-basics",
      "args": ["mcp"]
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
- Working directory: leave unset/default
- Tool calls: pass `cwd` as the repository root or any directory inside it

## Legacy Compatibility

This repository may contain the older `.agents/memory/` markdown mini-RAG source files if it is an agent-basics development checkout or was explicitly configured for fallback compatibility. Fresh setup does not install that legacy mini-RAG unless `AGENT_BASICS_INSTALL_COMPAT_MEMORY=1` is set.

Use this layer only as fallback compatibility when OpenViking tooling is unavailable and work must continue:

- Prefer the OpenViking-backed `agent-basics mcp` server for normal work.
- Use the compatibility memory MCP server only if it is explicitly configured.
- Call compatibility `memory_search` for prior context only when OpenViking search is unavailable.
- Call compatibility `memory_record` for durable records only when OpenViking recording is unavailable.
- Let routine `memory_record` calls defer rebuilds.
- Call `memory_rebuild` once after a batch of memory changes, before relying on new entries in search, or before committing memory changes.
- If MCP is unavailable, use `agent-basics memory ...` or `.agents/memory/rag/agent-memory.py ...`.
- Keep `.agents/memory/INDEX.md` updated whenever adding, moving, or removing compatibility entries.
- Do not write `.agents/memory/**` while `.agents/memory/rag/write.lock/` exists.

Compatibility files are not the long-term architecture. Useful compatibility memory should be adapted into `.agents/memory/memories/`, `.agents/memory/resources/`, or `.agents/memory/skills/`, ingested through OpenViking, and then treated as legacy source-checkout fallback.

## Configuration

- Durable repo configuration belongs in `.agents/config.toml` and `.agents/openviking/` metadata/config files once those files exist. User-level OpenViking runtime installation files belong under `~/.openviking`.
- Provider URLs, model names, timeouts, runtime paths, and feature flags should be stored in config files, not scattered through shell environment variables.
- Environment variables are allowed for secrets, compatibility inputs, and one-off overrides.
- Never commit raw provider API keys or local-only secrets.
- Local provider defaults currently being tested are:
  - MLX base URL: `http://127.0.0.1:18080`
  - Chat/VLM model: `mlx-community/gemma-4-e2b-it-4bit`
  - Embedding model: `mlx-community/embeddinggemma-300m-4bit`
- The MLX LaunchAgent should preload both configured models after startup, run the OpenViking router structured-output warmup check, keep model weights warm, and clear transient MLX runtime cache after each request.
- For the first release, the bundled local MLX runtime requires an Apple Silicon Mac with at least 16 GB unified memory. Unsupported hosts should use `agent-basics ov write-default-config --provider custom` with a user-supplied OpenAI-compatible API.
- MLX is the default local runtime on supported Apple Silicon hosts. Non-MLX inference should be configured as a custom OpenAI-compatible API provider through OpenViking config, not through provider-specific agent-basics commands.

## Long-Horizon Work

- `ROADMAP.md` records project direction, design choices, milestones, non-goals, and open questions.
- `.agents/TODO.md` records the current work plan and cross-session state.
- For substantial work, update `.agents/TODO.md` before editing files and tick items off as they are completed.
- Preserve useful handoff context in `.agents/TODO.md`, OpenViking records, commits, pull requests, or chat handoff notes when work may continue in another session.
- Pre-work and finish-work routines are instruction-driven. agent-basics does not try to enforce them with a local run-state command.

## Skills And Stable Commands

- Skills should capture repeated workflows such as prework, memory update, finish work, documentation lookup, and verification.
- Skills should point to stable `agent-basics` commands so users can approve predictable command prefixes.
- Do not rely on optional client-side skills as the only source of baseline behavior. Root `Agents.md`, this operating manual, MCP tools, CLI checks, and git hooks remain the repo contract.

## Documentation Discipline

- Find up-to-date documentation for any library, framework, API, tool, or programming language used in the project.
- Record source URLs in OpenViking resources through `agent-basics ov add-resource` when the gateway exists.
- Record important sources under `.agents/memory/resources/` when maintaining repo-owned source-store files. Use legacy `.agents/memory/documentations/sources/` only while explicitly operating the compatibility layer.
- While writing code, refer to recorded documentation sources before relying on memory for external APIs.
- Add a new source record when you consult a new external reference that matters for future work.
EOT
      ;;
    skills-index)
      cat > "$template_file" <<'EOT'
# Skills

This file indexes repo-local agent workflows. Skills reduce repeated prompt overhead; baseline behavior still depends on root instructions and MCP tools.

## Available Skills

- [Prework](.agents/skills/prework.md): establish context and plan before editing.
- [Memory Update](.agents/skills/memory-update.md): record durable decisions, preferences, facts, cases, resources, and skills through OpenViking.
- [Finish Work](.agents/skills/finish-work.md): verify, ingest, summarize, and commit completed work.

## Command Surface

Prefer these stable command prefixes:

```bash
agent-basics ov
agent-basics verify
agent-basics commit
```

Agents should use the OpenViking-backed MCP server when available and fall back to the same `agent-basics ov ...` commands when MCP is unavailable.
EOT
      ;;
    skill-prework)
      cat > "$template_file" <<'EOT'
---
name: agent-basics-prework
description: Establish context and a concrete plan before editing an agent-basics repository.
---

# Prework Skill

Use this before non-trivial repository work.

## Steps

1. Read `Agents.md`, `.agents/AGENT-BASICS.md`, `ROADMAP.md`, `.agents/TODO.md`, and `Skills.md` when they exist.
2. Verify or start the user-level OpenViking service with `agent-basics ov status --offline`, `agent-basics ov doctor`, or `agent-basics ov service install` when live retrieval is needed. Use `agent-basics ov server` only for foreground debugging.
3. Search prior context through the OpenViking MCP server or `agent-basics ov search "<query>"`.
4. Inspect the git state before editing.
5. Write or update the concrete checklist in `.agents/TODO.md`.

## Commands

```bash
agent-basics ov status --offline
agent-basics ov search "<query>"
```

## Output

Proceed only when the current task, prior context, and planned file scope are clear.
EOT
      ;;
    skill-memory-update)
      cat > "$template_file" <<'EOT'
---
name: agent-basics-memory-update
description: Record durable project context through the OpenViking-backed agent-basics gateway.
---

# Memory Update Skill

Use this whenever durable project context should survive the current session.

## Record

Record through the OpenViking MCP server when available. Otherwise use `agent-basics ov record`.

Use OpenViking memory categories:

- `profile`
- `preferences`
- `entities`
- `events`
- `cases`
- `patterns`
- `tools`
- `skills`

Use resources for external documentation, URLs, references, and larger source material.

## Steps

1. Decide whether the information is durable enough to keep.
2. Split mixed information into one independently updatable idea per record.
3. Avoid secrets and local-only credentials.
4. Record memory with `agent-basics ov record` or ingest resources with `agent-basics ov add-resource`.
5. Run `agent-basics ov ingest-changed` after editing `.agents/memory/` source-store files.
6. Verify retrieval with `agent-basics ov search "<query>"` when the record matters for future work.

## Commands

```bash
agent-basics ov record <category> "<title>" --content "<content>"
agent-basics ov add-resource <path-or-url>
agent-basics ov add-skill <path>
agent-basics ov ingest-changed
agent-basics ov search "<query>"
```
EOT
      ;;
    skill-finish-work)
      cat > "$template_file" <<'EOT'
---
name: agent-basics-finish-work
description: Verify, ingest, summarize, and commit completed agent-basics repository work.
---

# Finish Work Skill

Use this before handing work back to the user or another agent.

## Steps

1. Run `agent-basics verify` or the narrowest reliable validation for the changed surface.
2. Record durable decisions, gotchas, and follow-up context through the memory update workflow.
3. Run `agent-basics ov ingest-changed` after source-store, instruction, documentation, or skill changes.
4. Update `.agents/TODO.md` by ticking completed items and recording blockers.
5. Check `git status --short`.
6. Stage intentional changes.
7. Commit with `agent-basics commit "type(scope): description"` when a commit is expected.

## Commands

```bash
agent-basics verify
agent-basics ov ingest-changed
agent-basics commit "feat(scope): description"
```

## Output

Report changed files, validation results, memory/ingest status, commit hash when created, and any residual risk.
EOT
      ;;
    memory-schema)
      cat > "$template_file" <<'EOT'
# Memory Schema

`.agents/memory/` is the repo-owned source store for OpenViking-facing memory, resources, and skills.

OpenViking is the required runtime backend for durable memory, documentation resources, semantic organization, vector indexes, and retrieval. The files in this directory are project-owned source material that agents and setup tooling can inspect, adapt, ingest, and version-control. The OpenViking package/runtime stays user-level; the repo-local OpenViking workspace, generated summaries, queues, and vector database live under `.agents/openviking/workspace/` as ignored generated state.

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

Those paths may still exist in target repositories as compatibility fallback. They are compatibility input, not the target source-store shape. The agent-basics development checkout keeps fallback implementation source under `compat/memory-rag/`; setup copies it to `.agents/memory/rag/` only when `AGENT_BASICS_INSTALL_COMPAT_MEMORY=1` is used. Compatibility writers must still respect `.agents/memory/rag/write.lock/` while the legacy mini-RAG is in use:

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
- MLX: https://github.com/ml-explore/mlx
- mlx-vlm: https://github.com/Blaizzy/mlx-vlm
- mlx-community Gemma 4 E2B MLX model: https://huggingface.co/mlx-community/gemma-4-e2b-it-4bit
- mlx-community EmbeddingGemma MLX model: https://huggingface.co/mlx-community/embeddinggemma-300m-4bit
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
3. Configure the MCP server without a fixed working directory and pass `cwd` on each repo-scoped tool call.
4. Verify the user-level OpenViking service with `agent-basics ov doctor` or install it with `agent-basics ov service install` when live retrieval is needed. Use `agent-basics ov server` only for foreground debugging.
5. Search prior context through the OpenViking-backed MCP search tool or `agent-basics ov search "<query>"` before answering vague or history-dependent requests.
6. Record durable decisions, facts, preferences, gotchas, events, procedures, and useful findings through the OpenViking-backed MCP record tool or `agent-basics ov record`.
7. Add important documentation or reference material with `agent-basics ov add-resource <path-or-url>`.
8. Add reusable workflows with `agent-basics ov add-skill <path>`.
9. After adapting repo memory, resources, or skills under `.agents/memory/`, run `agent-basics ov import-repo-memory --write --wait-memory --wait-resources`. OV-native memory files are written directly into their OpenViking memory categories; resources and skills use OpenViking ingestion.
10. After instruction, documentation, memory, or skill files change, run `agent-basics ov ingest-changed`.
11. Run `agent-basics ov doctor` before relying on OpenViking if setup, provider configuration, or ingest state is uncertain.

## Codex Desktop Configuration

In Settings -> MCP servers -> Connect to a custom MCP, use these fields:

- Name: `agent-basics`
- Transport: `STDIO`
- Command to launch: `agent-basics`
- Arguments: `mcp`
- Environment variables: only provider secret variables named by `.agents/config.toml` or user-level OpenViking config
- Environment variable passthrough: the same provider secret variables, only when needed
- Working directory: leave unset/default
- Tool calls: pass `cwd` as the repository root or any directory inside it

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
    "$REPO_SKILLS_DIR" \
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

  choice="${AGENT_BASICS_CONFLICT_ACTION:-}"
  case "$choice" in
    k|K|keep) printf "k\n"; return ;;
    r|R|replace) printf "r\n"; return ;;
    a|A|append) printf "a\n"; return ;;
    m|M|manual) printf "m\n"; return ;;
    w|W|web|web-merge) printf "w\n"; return ;;
    s|S|save) printf "s\n"; return ;;
    "")
      ;;
    *)
      echo "Error: AGENT_BASICS_CONFLICT_ACTION must be one of keep, replace, append, manual, web, or save." >&2
      exit 2
      ;;
  esac

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

copy_bundled_merge_ui() {
  local session_dir="$1"
  local source_ui="$SCRIPT_DIR/demos/markdown-merge-ui.html"
  local target_ui="$session_dir/markdown-merge-ui.html"

  if [[ -f "$source_ui" ]]; then
    cp "$source_ui" "$target_ui"
  else
    cat > "$target_ui" <<'EOT'
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>agent-basics markdown merge</title></head>
<body>
<h1>agent-basics markdown merge</h1>
<p>The bundled merge UI was not found. Edit <code>final.md</code> in this session directory, then copy it over the target file when ready.</p>
</body>
</html>
EOT
  fi
}

create_web_merge_session() {
  local source_path="$1"
  local destination_path="$2"
  local timestamp
  local safe_name
  local session_dir

  timestamp="$(date -u +%s)"
  safe_name="$(slugify "$(basename "$destination_path")")"
  session_dir="$REPO_MERGE_SESSIONS_DIR/$timestamp-$safe_name"
  mkdir -p "$session_dir"

  cp "$destination_path" "$session_dir/existing.md"
  cp "$source_path" "$session_dir/proposed.md"
  cp "$source_path" "$session_dir/final.md"
  copy_bundled_merge_ui "$session_dir"

  python3 - "$session_dir/session.json" "$timestamp" "$destination_path" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
timestamp = int(sys.argv[2])
destination = sys.argv[3]
session_dir = path.parent
payload = {
    "created": timestamp,
    "updated": timestamp,
    "status": "unresolved",
    "destination_path": destination,
    "existing_path": str(session_dir / "existing.md"),
    "proposed_path": str(session_dir / "proposed.md"),
    "final_path": str(session_dir / "final.md"),
    "ui_path": str(session_dir / "markdown-merge-ui.html"),
    "instructions": [
        "Open markdown-merge-ui.html for visual review or edit final.md directly.",
        "Apply final.md to destination_path only after reviewing the merge.",
    ],
}
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

  printf "%s\n" "$session_dir"
}

web_merge_file() {
  local source_path="$1"
  local destination_path="$2"
  local merge_file
  local session_dir
  local session_ui
  local server_script=""
  local apply_choice

  backup_existing_file "$destination_path"
  session_dir="$(create_web_merge_session "$source_path" "$destination_path")"
  merge_file="$session_dir/final.md"
  session_ui="$session_dir/markdown-merge-ui.html"
  echo "Created web merge session: $session_dir"
  echo "Bundled merge UI copy: $session_ui"
  echo "Merge draft: $merge_file"

  if [[ "${AGENT_BASICS_OPEN_MERGE_UI:-1}" != "1" || ! -t 0 ]]; then
    echo "Web merge UI was not launched. Open the UI file above or edit final.md directly, then apply it manually when ready."
    return
  fi

  server_script="$(mktemp "${TMPDIR:-/tmp}/agent-basics-web-merge.XXXXXX.py")"

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

  timestamp="$(date -u +%s)"
  mkdir -p "$REPO_OPENVIKING_DIR"
  python3 - "$repo_metadata" "$timestamp" "$PROJECT_NAME" <<'PY'
from __future__ import annotations

import json
import sys

path, timestamp, project_name = sys.argv[1:]
existed = True
try:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
except FileNotFoundError:
    existed = False
    payload = {}
except json.JSONDecodeError:
    payload = {}

created = int(payload.get("created") or timestamp)
desired = dict(payload)
desired.update({
    "version": 1,
    "created": created,
    "project_name": project_name,
    "memory_source": ".agents/memory",
    "legacy_snapshots": ".agents/openviking/legacy-memory",
    "shared_runtime_home": "~/.openviking",
    "ov_config": ".agents/openviking/ov.conf",
    "ov_cli_config": ".agents/openviking/ovcli.conf",
    "workspace": ".agents/openviking/workspace",
    "data_plane": "repo-local",
    "notes": (
        "The OpenViking executable/runtime is shared at user level. Repository-specific OpenViking "
        "config, workspace, generated data, queues, vector indexes, import state, and locks stay under "
        ".agents/openviking/."
    ),
})
changed = (not existed) or any(payload.get(key) != value for key, value in desired.items())
if changed:
    desired["updated"] = int(timestamp)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(desired, handle, indent=2, sort_keys=True)
        handle.write("\n")
PY
  echo "Wrote: .agents/openviking/repo.json"
}

repo_openviking_service_port() {
  python3 - "$TARGET_DIR" <<'PY'
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
digest = hashlib.sha256(str(repo).encode("utf-8")).hexdigest()
print(20000 + int(digest[:4], 16) % 20000)
PY
}

repo_openviking_service_label() {
  local repo_slug
  repo_slug="$(slugify "$PROJECT_NAME")"
  python3 - "$TARGET_DIR" "$repo_slug" <<'PY'
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
repo_slug = sys.argv[2]
digest = hashlib.sha256(str(repo).encode("utf-8")).hexdigest()[:8]
print(f"com.agent-basics.openviking.{repo_slug}.{digest}")
PY
}

write_repo_openviking_config_files_if_missing() {
  local ov_home="$REPO_OPENVIKING_DIR"
  local ov_config="$REPO_OPENVIKING_DIR/ov.conf"
  local ovcli_config="$REPO_OPENVIKING_DIR/ovcli.conf"
  local meta_config="$REPO_OPENVIKING_DIR/config.toml"
  local namespaces_config="$REPO_OPENVIKING_DIR/namespaces.toml"
  local server_port
  local server_url
  local service_label
  local dispatcher
  local helper_path
  local timestamp
  local repo_slug
  local workspace_path

  server_port="$(repo_openviking_service_port)"
  server_url="http://127.0.0.1:$server_port"
  service_label="$(repo_openviking_service_label)"
  timestamp="$(date -u +%s)"
  repo_slug="$(slugify "$PROJECT_NAME")"

  mkdir -p "$REPO_OPENVIKING_DIR" "$REPO_OPENVIKING_DIR/workspace"
  workspace_path="$(cd "$REPO_OPENVIKING_DIR" && pwd -P)/workspace"

  if [[ -f "$ov_config" && -f "$ovcli_config" ]]; then
    python3 - "$ov_config" "$ovcli_config" "$workspace_path" "$server_url" "$server_port" <<'PY'
import json
import sys
from pathlib import Path

ov_config = Path(sys.argv[1])
ovcli_config = Path(sys.argv[2])
workspace = sys.argv[3]
server_url = sys.argv[4]
server_port = int(sys.argv[5])


def load_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"invalid JSON in {path}: expected object")
    return payload


changed = []
config = load_json(ov_config)
storage = config.setdefault("storage", {})
if not isinstance(storage, dict):
    storage = {}
    config["storage"] = storage
if storage.get("workspace") != workspace:
    storage["workspace"] = workspace
    changed.append(str(ov_config))
server = config.setdefault("server", {})
if not isinstance(server, dict):
    server = {}
    config["server"] = server
if server.get("host") != "127.0.0.1":
    server["host"] = "127.0.0.1"
    changed.append(str(ov_config))
if server.get("port") != server_port:
    server["port"] = server_port
    changed.append(str(ov_config))

cli = load_json(ovcli_config)
if cli.get("url") != server_url:
    cli["url"] = server_url
    changed.append(str(ovcli_config))

if str(ov_config) in changed:
    ov_config.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
if str(ovcli_config) in changed:
    ovcli_config.write_text(json.dumps(cli, indent=2, sort_keys=True) + "\n", encoding="utf-8")

if changed:
    print("Updated repo-local OpenViking config paths")
else:
    print("Exists: .agents/openviking/ov.conf")
    print("Exists: .agents/openviking/ovcli.conf")
PY
  elif helper_path="$(find_ov_helper_source)"; then
    python3 "$helper_path" --repo "$TARGET_DIR" ov write-default-config \
      --home "$ov_home" \
      --config "$ov_config" \
      --cli-config "$ovcli_config" \
      --server-url "$server_url" >/dev/null
    echo "Wrote repo-local OpenViking config: .agents/openviking/ov.conf"
    echo "Wrote repo-local OpenViking CLI config: .agents/openviking/ovcli.conf"
  elif dispatcher="$(find_agent_basics_dispatcher)"; then
    "$dispatcher" --repo "$TARGET_DIR" ov write-default-config \
      --home "$ov_home" \
      --config "$ov_config" \
      --cli-config "$ovcli_config" \
      --server-url "$server_url" >/dev/null
    echo "Wrote repo-local OpenViking config: .agents/openviking/ov.conf"
    echo "Wrote repo-local OpenViking CLI config: .agents/openviking/ovcli.conf"
  else
    echo "Error: cannot write repo-local OpenViking config because no agent-basics dispatcher/helper was found." >&2
    exit 1
  fi

  python3 - "$meta_config" "$namespaces_config" "$timestamp" "$repo_slug" "$server_url" "$server_port" "$service_label" <<'PY'
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

meta_path, namespaces_path, timestamp, repo_slug, server_url, server_port, service_label = sys.argv[1:]

def quote(value: str) -> str:
    return json.dumps(value)

def previous_generated_at(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return int(timestamp)
    match = re.search(r"(?m)^generated_at\s*=\s*(\d+)\s*$", text)
    return int(match.group(1)) if match else int(timestamp)

def write_if_changed(path: Path, text: str) -> None:
    try:
        current = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        current = None
    if current != text:
        path.write_text(text, encoding="utf-8")

meta = Path(meta_path)
namespaces = Path(namespaces_path)
generated_at = previous_generated_at(meta)

meta_lines = [
    "version = 1",
    f"generated_at = {generated_at}",
    'data_plane = "repo-local"',
    'shared_runtime_home = "~/.openviking"',
    'ov_config_path = ".agents/openviking/ov.conf"',
    'ov_cli_config_path = ".agents/openviking/ovcli.conf"',
    'workspace_path = ".agents/openviking/workspace"',
    "",
    "[server]",
    'host = "127.0.0.1"',
    f"port = {int(server_port)}",
    f"url = {quote(server_url)}",
    "",
    "[service]",
    f"label = {quote(service_label)}",
    "repo_local = true",
    "",
]
write_if_changed(meta, "\n".join(meta_lines))

namespace_lines = [
    "version = 1",
    f"repo_slug = {quote(repo_slug)}",
    f"resource_root = {quote('viking://resources/projects/' + repo_slug)}",
    'memory_base = "viking://user/default/memories"',
    "",
    "[memory_roots]",
]
for category in ["profile", "preferences", "entities", "events", "cases", "patterns", "tools", "skills"]:
    namespace_lines.append(f"{category} = {quote('viking://user/default/memories/' + category + '/projects/' + repo_slug)}")
namespace_lines.append("")
write_if_changed(namespaces, "\n".join(namespace_lines))
PY
  echo "Wrote repo OpenViking metadata: .agents/openviking/config.toml"
  echo "Wrote repo OpenViking namespaces: .agents/openviking/namespaces.toml"
}

write_repo_config_if_missing() {
  local repo_config="$REPO_AGENTS_DIR/config.toml"
  local timestamp
  local repo_slug

  if [[ -f "$repo_config" ]]; then
    echo "Exists: .agents/config.toml"
    remove_repo_config_language "$repo_config"
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
    handle.write('source_store_path = ".agents/memory"\n')
    handle.write('config_path = ".agents/openviking/ov.conf"\n')
    handle.write('cli_config_path = ".agents/openviking/ovcli.conf"\n')
    handle.write('workspace_path = ".agents/openviking/workspace"\n')
    handle.write('metadata_path = ".agents/openviking/config.toml"\n')
    handle.write('namespaces_path = ".agents/openviking/namespaces.toml"\n')
    handle.write('data_plane = "repo-local"\n\n')
    handle.write("[openviking.mcp]\n")
    handle.write('command = "agent-basics"\n')
    handle.write('args = ["mcp"]\n')
    handle.write('cwd_argument = "cwd"\n')
PY
  echo "Created: .agents/config.toml"
}

remove_repo_config_language() {
  local repo_config="$1"
  local result

  result="$(python3 - "$repo_config" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path


path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
original = text
section_re = re.compile(r"(?ms)^\[agent_basics\]\n(?P<body>.*?)(?=^\[|\Z)")
match = section_re.search(text)

if match:
    body = match.group("body")
    body = re.sub(r"(?m)^language\s*=.*\n?", "", body)
    if body.strip():
        text = text[: match.start("body")] + body + text[match.end("body") :]
    else:
        text = text[: match.start()] + text[match.end():]
        text = re.sub(r"\n{3,}", "\n\n", text)

if text != original:
    path.write_text(text, encoding="utf-8")
    print("changed")
else:
    print("unchanged")
PY
)"

  if [[ "$result" == "changed" ]]; then
    echo "Removed repo-scoped language: .agents/config.toml"
  fi
}

write_repo_mcp_config_snippets() {
  local codex_snippet="$REPO_OPENVIKING_DIR/codex-mcp.json"

  mkdir -p "$REPO_OPENVIKING_DIR"
python3 - "$codex_snippet" <<'PY'
from __future__ import annotations

import json
import sys

path = sys.argv[1]
payload = {
    "mcpServers": {
        "agent-basics": {
            "command": "agent-basics",
            "args": ["mcp"],
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
    echo "Install or repair agent-basics, then run: agent-basics ov bootstrap-system --home \"$ov_home\" --service never --runtime mlx --runtime-best-effort" >&2
    exit 1
  fi

  install_args=(ov bootstrap-system --home "$ov_home" --service never --runtime mlx --runtime-best-effort)
  if [[ "$mode" == "repair" ]]; then
    install_args+=(--force-install)
  fi

  if [[ "${AGENT_BASICS_TEST_OPENVIKING_AUTO_INSTALL:-0}" == "1" && -n "${AGENT_BASICS_TEST_OPENVIKING_INSTALL_DISPATCHER:-}" ]]; then
    echo "Running test-only OpenViking $mode via fake dispatcher: $dispatcher"
  else
    if [[ ! -t 0 ]]; then
      echo "Error: user-level OpenViking $mode is required, but setup is not running interactively." >&2
      echo "Expected executable: $ov_bin" >&2
      echo "Run setup in an interactive terminal, or run this first:" >&2
      echo "  $dispatcher ov bootstrap-system --home \"$ov_home\" --service never --runtime mlx --runtime-best-effort" >&2
      exit 1
    fi

    printf "User-level OpenViking %s is required at %s. Run '%s ov bootstrap-system --home \"%s\" --service never --runtime mlx --runtime-best-effort' now? [y/N]: " \
      "$mode" "$ov_bin" "$dispatcher" "$ov_home" >&2
    read -r choice
    case "$choice" in
      y|Y|yes|YES)
        ;;
      *)
        echo "Error: user-level OpenViking $mode was declined." >&2
        echo "Install or repair OpenViking with: $dispatcher ov bootstrap-system --home \"$ov_home\" --service never --runtime mlx --runtime-best-effort" >&2
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
    echo "Install or repair OpenViking with: agent-basics ov bootstrap-system" >&2
    exit 1
  fi

  if [[ ! -x "$ov_bin" ]]; then
    install_or_repair_user_openviking "$ov_bin" "$ov_home" "installation"
  else
    install_or_repair_user_openviking "$ov_bin" "$ov_home" "repair"
  fi

  echo "Verified user-level OpenViking CLI: $ov_bin"
}

ensure_user_openviking_config() {
  local ov_home
  local ov_config
  local ovcli_config
  local dispatcher

  # Test-only fake CLIs do not imply a real user-level OpenViking config.
  if [[ -n "${AGENT_BASICS_TEST_OPENVIKING_BIN:-}" || "${AGENT_BASICS_TEST_SKIP_OPENVIKING_CHECK:-0}" == "1" ]]; then
    return
  fi

  if [[ -z "${HOME:-}" ]]; then
    echo "Error: HOME is required to locate the user-level OpenViking configuration." >&2
    exit 1
  fi

  ov_home="$HOME/.openviking"
  ov_config="$ov_home/ov.conf"
  ovcli_config="$ov_home/ovcli.conf"

  if [[ -f "$ov_config" && -f "$ovcli_config" ]]; then
    echo "Verified user-level OpenViking config: $ov_config"
    echo "Verified user-level OpenViking CLI config: $ovcli_config"
    return
  fi

  if ! dispatcher="$(find_agent_basics_dispatcher)"; then
    echo "Error: user-level OpenViking configuration is missing, but no executable agent-basics dispatcher was found." >&2
    echo "Run: agent-basics ov bootstrap-system --home \"$ov_home\" --service-best-effort --runtime mlx --runtime-best-effort" >&2
    exit 1
  fi

  if ! "$dispatcher" ov write-default-config --home "$ov_home" --config "$ov_config" --cli-config "$ovcli_config"; then
    echo "Error: failed to write user-level OpenViking configuration." >&2
    echo "Run manually: $dispatcher ov bootstrap-system --home \"$ov_home\" --service-best-effort --runtime mlx --runtime-best-effort" >&2
    exit 1
  fi

  echo "Verified user-level OpenViking config: $ov_config"
  echo "Verified user-level OpenViking CLI config: $ovcli_config"
}

ensure_user_openviking_service() {
  local ov_home
  local dispatcher

  # Test-only fake CLIs do not imply a real user-level OpenViking server binary.
  if [[ -n "${AGENT_BASICS_TEST_OPENVIKING_BIN:-}" || "${AGENT_BASICS_TEST_SKIP_OPENVIKING_CHECK:-0}" == "1" ]]; then
    return
  fi

  if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "Warning: OpenViking service setup is only supported on macOS launchctl." >&2
    return
  fi

  if [[ -z "${HOME:-}" ]]; then
    echo "Warning: HOME is required to install the user-level OpenViking service." >&2
    return
  fi

  ov_home="$HOME/.openviking"

  if ! dispatcher="$(find_agent_basics_dispatcher)"; then
    echo "Warning: no executable agent-basics dispatcher found for OpenViking service setup." >&2
    echo "Re-run manually: agent-basics ov service install --home \"$ov_home\"" >&2
    return
  fi

  if "$dispatcher" ov service status --home "$ov_home" >/dev/null 2>&1 && openviking_health_ready; then
    echo "Verified user-level OpenViking macOS service: com.agent-basics.openviking"
    return
  fi

  if ! "$dispatcher" ov package-server --home "$ov_home"; then
    echo "Warning: OpenViking server packaging failed." >&2
    echo "Re-run manually: $dispatcher ov package-server --home \"$ov_home\"" >&2
    return
  fi

  if "$dispatcher" ov service install --home "$ov_home"; then
    echo "Verified user-level OpenViking macOS service: com.agent-basics.openviking"
    return
  fi

  echo "Warning: OpenViking service setup failed." >&2
  echo "Re-run manually: $dispatcher ov service install --home \"$ov_home\"" >&2
}

ensure_repo_openviking_service() {
  local dispatcher

  # Test-only fake CLIs do not imply a real OpenViking server binary.
  if [[ -n "${AGENT_BASICS_TEST_OPENVIKING_BIN:-}" || "${AGENT_BASICS_TEST_SKIP_OPENVIKING_CHECK:-0}" == "1" ]]; then
    return
  fi

  if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "Warning: repo-local OpenViking service setup is only supported on macOS launchctl." >&2
    return
  fi

  if ! dispatcher="$(find_agent_basics_dispatcher)"; then
    echo "Warning: no executable agent-basics dispatcher found for repo-local OpenViking service setup." >&2
    echo "Re-run manually: agent-basics --repo \"$TARGET_DIR\" ov service install --repo-local" >&2
    return
  fi

  if "$dispatcher" --repo "$TARGET_DIR" ov service status --repo-local >/dev/null 2>&1 && openviking_health_ready; then
    echo "Verified repo-local OpenViking macOS service"
    return
  fi

  if ! "$dispatcher" ov package-server --home "$HOME/.openviking"; then
    echo "Warning: OpenViking server packaging failed." >&2
    echo "Re-run manually: $dispatcher ov package-server --home \"$HOME/.openviking\"" >&2
    return
  fi

  if "$dispatcher" --repo "$TARGET_DIR" ov service install --repo-local; then
    echo "Verified repo-local OpenViking macOS service"
    return
  fi

  echo "Warning: repo-local OpenViking service setup failed." >&2
  echo "Re-run manually: $dispatcher --repo \"$TARGET_DIR\" ov service install --repo-local" >&2
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
    "$SCRIPT_DIR/compat/memory-rag/agent-memory.py"
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
    "$SCRIPT_DIR/compat/memory-rag/memory-mcp.py"
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

find_ov_helper_source() {
  local candidate
  local -a candidates

  candidates=(
    "$SCRIPT_DIR/agent-basics-ov.py"
    "$SCRIPT_DIR/scripts/agent_basics_ov.py"
  )

  for candidate in "${candidates[@]}"; do
    if [[ -f "$candidate" ]]; then
      printf "%s\n" "$candidate"
      return 0
    fi
  done

  return 1
}

install_openviking_hooks() {
  local helper_path
  local dispatcher

  if helper_path="$(find_ov_helper_source)"; then
    if python3 "$helper_path" --repo "$TARGET_DIR" ov install-hooks; then
      return
    fi
    echo "Warning: OpenViking hook installation failed. Re-run manually with: agent-basics ov install-hooks" >&2
    return
  fi

  if dispatcher="$(find_agent_basics_dispatcher)"; then
    if "$dispatcher" --repo "$TARGET_DIR" ov install-hooks; then
      return
    fi
  fi

  echo "Warning: OpenViking hook installation could not be completed. Re-run manually with: agent-basics ov install-hooks" >&2
}

openviking_health_ready() {
  local ov_bin

  if [[ -n "${AGENT_BASICS_TEST_OPENVIKING_BIN:-}" ]]; then
    ov_bin="$AGENT_BASICS_TEST_OPENVIKING_BIN"
  else
    ov_bin="${HOME:-}/.openviking/venv/bin/ov"
  fi

  [[ -x "$ov_bin" ]] || return 1
  OPENVIKING_CLI_CONFIG_FILE="$REPO_OPENVIKING_DIR/ovcli.conf" "$ov_bin" health -o json >/dev/null 2>&1
}

wait_for_openviking_health_for_import() {
  local timeout_seconds="${AGENT_BASICS_OPENVIKING_IMPORT_READY_TIMEOUT:-60}"
  local start_time="$SECONDS"
  local elapsed

  if [[ -n "${AGENT_BASICS_TEST_OPENVIKING_BIN:-}" || "${AGENT_BASICS_TEST_SKIP_OPENVIKING_CHECK:-0}" == "1" ]]; then
    return 0
  fi

  while true; do
    if openviking_health_ready; then
      return 0
    fi

    elapsed=$((SECONDS - start_time))
    if (( elapsed >= timeout_seconds )); then
      return 1
    fi

    echo "Waiting for OpenViking service before source-store import..."
    sleep 2
  done
}

run_openviking_source_import_command() {
  local import_log

  import_log="$(mktemp "${TMPDIR:-/tmp}/agent-basics-ov-import.XXXXXX.log")"
  if "$@" > "$import_log" 2>&1; then
    rm -f "$import_log"
    return 0
  fi

  cat "$import_log" >&2
  rm -f "$import_log"
  return 1
}

import_openviking_source_store() {
  local helper_path
  local dispatcher

  if [[ "${AGENT_BASICS_TEST_SKIP_OPENVIKING_CHECK:-0}" == "1" ]]; then
    echo "Skipped OpenViking source-store import due to test-only skip flag"
    return
  fi

  if ! wait_for_openviking_health_for_import; then
    echo "Error: OpenViking service did not become healthy before source-store import." >&2
    echo "Re-run manually with: agent-basics ov import-repo-memory --write --wait-memory --wait-resources" >&2
    exit 1
  fi

  if helper_path="$(find_ov_helper_source)"; then
    if [[ -n "${AGENT_BASICS_TEST_OPENVIKING_BIN:-}" ]]; then
      if run_openviking_source_import_command env AGENT_BASICS_OV_BIN="$AGENT_BASICS_TEST_OPENVIKING_BIN" python3 "$helper_path" --repo "$TARGET_DIR" ov import-repo-memory --write --wait-memory --wait-resources; then
        echo "Imported OpenViking source store"
        return
      fi
    else
      if run_openviking_source_import_command python3 "$helper_path" --repo "$TARGET_DIR" ov import-repo-memory --write --wait-memory --wait-resources; then
        echo "Imported OpenViking source store"
        return
      fi
    fi
    echo "Error: OpenViking source-store import failed." >&2
    echo "Re-run manually with: agent-basics ov import-repo-memory --write --wait-memory --wait-resources" >&2
    exit 1
  fi

  if dispatcher="$(find_agent_basics_dispatcher)"; then
    if [[ -n "${AGENT_BASICS_TEST_OPENVIKING_BIN:-}" ]]; then
      if run_openviking_source_import_command env AGENT_BASICS_OV_BIN="$AGENT_BASICS_TEST_OPENVIKING_BIN" "$dispatcher" --repo "$TARGET_DIR" ov import-repo-memory --write --wait-memory --wait-resources; then
        echo "Imported OpenViking source store"
        return
      fi
    else
      if run_openviking_source_import_command "$dispatcher" --repo "$TARGET_DIR" ov import-repo-memory --write --wait-memory --wait-resources; then
        echo "Imported OpenViking source store"
        return
      fi
    fi
  fi

  echo "Error: OpenViking source-store import could not be completed." >&2
  echo "Re-run manually with: agent-basics ov import-repo-memory --write --wait-memory --wait-resources" >&2
  exit 1
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
    base_url="$(read_with_default "Embedding API base URL" "http://127.0.0.1:18080/v1")"
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

ensure_agent_basics_install_config
verify_user_openviking_installation
snapshot_existing_legacy_memory
create_memory_layout

agents_template="$(create_template_file "agents")"
agent_basics_template="$(create_template_file "agent-basics")"
trap cleanup_setup EXIT

copy_or_merge_markdown_file "$agents_template" "Agents.md"
seed_agent_basics_from_legacy_instructions
copy_or_merge_markdown_file "$agent_basics_template" ".agents/AGENT-BASICS.md"
copy_memory_template_if_missing "skills-index" "Skills.md"
copy_memory_template_if_missing "skill-prework" ".agents/skills/prework.md"
copy_memory_template_if_missing "skill-memory-update" ".agents/skills/memory-update.md"
copy_memory_template_if_missing "skill-finish-work" ".agents/skills/finish-work.md"
create_empty_file_if_missing ".agents/TODO.md"

copy_memory_template_if_missing "memory-schema" ".agents/memory/SCHEMA.md"
copy_memory_template_if_missing "memory-index" ".agents/memory/INDEX.md"
copy_memory_template_if_missing "memory-adaptation" ".agents/memory/ADAPTATION.md"
write_repo_openviking_metadata_if_missing
write_repo_config_if_missing
write_repo_openviking_config_files_if_missing
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
append_gitignore_entry_if_missing ".agents/openviking/ov.conf"
append_gitignore_entry_if_missing ".agents/openviking/ovcli.conf"
append_gitignore_entry_if_missing ".agents/openviking/workspace/"
append_gitignore_entry_if_missing ".agents/openviking/logs/"
append_gitignore_entry_if_missing ".agents/openviking/tmp/"

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

install_openviking_hooks
ensure_repo_openviking_service

while IFS= read -r markdown_file; do
  ensure_trailing_blank_line "$markdown_file"
done < <(find "Agents.md" ".agents" -type f -name "*.md" 2>/dev/null | sort)

if compat_memory_enabled; then
  start_repo_local_embedding_api_for_setup
  ".agents/memory/rag/agent-memory.py" rebuild
fi

import_openviking_source_store

if agent_basics_language_is_zh; then
cat <<EOT
agent-basics 设置完成。

OpenViking source store:
  .agents/memory/

OpenViking 仓库 metadata:
  .agents/openviking/

OpenViking 仓库 workspace:
  .agents/openviking/workspace/ (ignored)

OpenViking 仓库配置:
  .agents/config.toml
  .agents/openviking/ov.conf
  .agents/openviking/ovcli.conf

agent-basics 安装配置:
  $AGENT_BASICS_CONFIG_FILE

安装语言:
  $AGENT_BASICS_LANGUAGE

Skills:
  Skills.md
  .agents/skills/

MCP 配置片段:
  .agents/openviking/codex-mcp.json

Legacy memory snapshots:
  .agents/openviking/legacy-memory/

冲突备份和 merge sessions:
  .agents/backups/
  .agents/merge-sessions/

Codex Desktop custom MCP 字段:
  Name: agent-basics
  Transport: STDIO
  Command to launch: agent-basics
  Arguments: mcp
  Working directory: 留空/默认
  Tool calls: 用 cwd 传仓库根目录，或仓库内任意目录

如果 legacy material 被 snapshot，按这个文件适配:
  .agents/memory/ADAPTATION.md
EOT
else
cat <<EOT
agent-basics setup complete.

OpenViking source store:
  .agents/memory/

OpenViking repo metadata:
  .agents/openviking/

OpenViking repo workspace:
  .agents/openviking/workspace/ (ignored)

OpenViking repo config:
  .agents/config.toml
  .agents/openviking/ov.conf
  .agents/openviking/ovcli.conf

agent-basics install config:
  $AGENT_BASICS_CONFIG_FILE

Installation language:
  $AGENT_BASICS_LANGUAGE

Skills:
  Skills.md
  .agents/skills/

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
  Working directory: leave unset/default
  Tool calls: pass cwd as the repository root or any directory inside it

If legacy material was snapshotted, adapt it with:
  .agents/memory/ADAPTATION.md
EOT
fi
