# Workspaces

This repository is designed to be developed together with a local MemoryHub checkout.

## Default Layout

The expected sibling checkout layout is:

```text
/Users/leonardw/Projects/
├── agent-basics/
└── MemoryHub/
```

`agent-basics` owns project setup, bootstrap scripts, and agent instruction templates. MemoryHub owns the central memory runtime, project registry, indexing, MCP/API surfaces, and markdown-backed memory implementation.

## Environment

Use these variables when working across both repositories:

```bash
export AGENT_BASICS_ROOT="/Users/leonardw/Projects/agent-basics"
export MEMORYHUB_SOURCE_DIR="/Users/leonardw/Projects/MemoryHub"
export MEMORYHUB_CONFIG_DIR="${MEMORYHUB_CONFIG_DIR:-$HOME/.memoryhub}"
export PATH="$MEMORYHUB_CONFIG_DIR/venv/bin:$PATH"
```

`setup-macos.sh` uses `MEMORYHUB_SOURCE_DIR` when it needs to install MemoryHub into the central hub virtualenv. If the variable is not set, it also checks common sibling checkout paths.

## Working Rules

- Treat the two repositories as separate git worktrees with separate commits.
- Check `git status --short --branch` in both repos before editing.
- Do not overwrite dirty MemoryHub files unless the user explicitly asks for that exact change.
- Make `agent-basics` changes in `/Users/leonardw/Projects/agent-basics`.
- Make MemoryHub changes in `/Users/leonardw/Projects/MemoryHub`.
- Use `.agents/agent-mailbox/` in either repo for timestamped cross-sandbox handoffs when separate agents need to coordinate.
- When a change spans both repos, commit each repo separately with a message that explains its half of the integration.
- Use the supervised author format for commits: `Coding agent supervised by $(git config --global user.name)`.

## Common Flow

1. Inspect both repos:

   ```bash
   git -C "$AGENT_BASICS_ROOT" status --short --branch
   git -C "$MEMORYHUB_SOURCE_DIR" status --short --branch
   ```

2. Update `agent-basics` when the setup contract, generated files, or user-facing bootstrap flow changes.

3. Update MemoryHub when the hub needs new CLI/API behavior, config fields, project registry behavior, sync behavior, or tests.

4. Verify both sides before committing:

   ```bash
   bash -n "$AGENT_BASICS_ROOT/setup-macos.sh"
   ruby -c "$AGENT_BASICS_ROOT/Formula/agent-basics.rb"
   cd "$MEMORYHUB_SOURCE_DIR" && uv run pytest
   ```

   Use a narrower MemoryHub test command when the change is scoped to a specific module.

## Agent Mailbox

Each repo may contain `.agents/agent-mailbox/` with `inbox/`, `outbox/`, and `archive/` folders.

Use timestamped markdown messages:

```text
YYYYMMDD-HHMMSS-to-agent-basics-topic.md
YYYYMMDD-HHMMSS-to-memoryhub-topic.md
```

Mailbox messages should be short handoffs that name the sender repo, target repo, branch, relevant files or commands, and whether action is needed. Durable product decisions still belong in normal docs, code, or tests.

## Current Integration Boundary

`agent-basics` should not vendor MemoryHub code. It depends on a local MemoryHub checkout or an installed `memoryhub` executable.

`setup-macos.sh` should:

- install/reuse one central MemoryHub virtualenv under `$MEMORYHUB_CONFIG_DIR/venv`
- use `MEMORYHUB_SOURCE_DIR` for editable MemoryHub installs
- keep repo-local memory markdown under `.agents/memoryhub/`
- symlink repo memory into `$MEMORYHUB_CONFIG_DIR/projects/<project-name>`
- register the project with `memoryhub project add`

MemoryHub should provide:

- stable project registration and discovery commands
- cwd/repository project resolution
- local markdown source-of-truth behavior
- safe sync/indexing for symlinked project directories
- tests covering config, registry, routing, and sync behavior
