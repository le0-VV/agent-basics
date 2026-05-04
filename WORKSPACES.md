# Workspaces

This repository is now self-contained for the agent-basics setup contract.

## Default Layout

The expected local checkout layout is:

```text
/Users/leonardw/Projects/
└── agent-basics/
```

`agent-basics` owns project setup, bootstrap scripts, generated instruction templates, the `.agents/memory/` OpenViking source-store schema, repo metadata, hooks, and the repo-aware MCP/CLI gateway. OpenViking owns embedding, storage, summarization, semantic retrieval, and vector indexes in the user-level `~/.openviking` installation.

## Environment

Useful local setup anchor:

```bash
export AGENT_BASICS_ROOT="/Users/leonardw/Projects/agent-basics"
```

Provider URLs, model names, timeouts, runtime paths, and feature flags should be configured with `agent-basics ov write-default-config` and stored in `~/.openviking/ov.conf` plus `~/.openviking/ovcli.conf`. Environment variables are for secrets, compatibility inputs, and one-off overrides.

```bash
agent-basics ov status --offline
agent-basics ov write-default-config
agent-basics ov server
```

## Working Rules

- Check `git status --short --branch` before editing.
- Keep `.agents/memory/` markdown as the repo-owned source store for OpenViking.
- Do not edit `.agents/memory/**` while `.agents/openviking/locks/ingest.lock/` exists. If explicitly using the compatibility mini-RAG, also respect `.agents/memory/rag/write.lock/`.
- Do not commit embedding provider secret values.
- Use `.agents/memory/` for durable coordination records and normal git branches, commits, and pull requests for cross-session handoffs.
- Use the supervised author format for commits: `Coding agent supervised by $(git config --global user.name)`.

## Common Flow

1. Inspect repo status:

   ```bash
   git -C "$AGENT_BASICS_ROOT" status --short --branch
   ```

2. Update `setup-macos.sh` when the setup contract, generated files, OpenViking validation, or bootstrap flow changes.

3. Update `.agents/memory/SCHEMA.md`, `.agents/memory/INDEX.md`, and templates when the memory contract changes.

4. Verify before committing:

   ```bash
   bash -n "$AGENT_BASICS_ROOT/setup-macos.sh"
   ruby -c "$AGENT_BASICS_ROOT/Formula/agent-basics.rb"
   ```

5. For setup integration testing, run `setup-macos.sh` against a temporary directory with the real user-level OpenViking CLI. Use the compatibility embedding API only when testing `AGENT_BASICS_INSTALL_COMPAT_MEMORY=1`.

## Cross-Session Handoffs

Record durable product decisions, project facts, gotchas, and procedures under `.agents/memory/` and ingest them through `agent-basics ov import-repo-memory` or `agent-basics ov ingest-changed`. Use git status, commits, branches, and pull requests for operational handoffs between sessions.
