# Workspaces

This repository is now self-contained for the agent-basics setup contract.

## Default Layout

The expected local checkout layout is:

```text
/Users/leonardw/Projects/
└── agent-basics/
```

`agent-basics` owns project setup, bootstrap scripts, generated instruction templates, the `.agents/memory/` schema, embedding setup, and future RAG/MCP glue.

## Environment

Useful variables for local setup work:

```bash
export AGENT_BASICS_ROOT="/Users/leonardw/Projects/agent-basics"
export AGENT_BASICS_EMBEDDING_BASE_URL="http://127.0.0.1:1234/v1"
export AGENT_BASICS_EMBEDDING_MODEL="text-embedding-embeddinggemma-300m-qat"
export AGENT_BASICS_EMBEDDING_API_KEY=""
```

For repo-local HuggingFace embedding service testing:

```bash
export AGENT_BASICS_EMBEDDING_HF_MODEL="Qwen/Qwen3-Embedding-0.6B"
```

## Working Rules

- Check `git status --short --branch` before editing.
- Keep `.agents/memory/` markdown as source of truth.
- Do not edit `.agents/memory/**` while `.agents/memory/rag/write.lock/` exists.
- Do not commit embedding provider secret values.
- Use `.agents/agent-mailbox/` for timestamped handoffs if a future task involves multiple sandboxes.
- Use the supervised author format for commits: `Coding agent supervised by $(git config --global user.name)`.

## Common Flow

1. Inspect repo status:

   ```bash
   git -C "$AGENT_BASICS_ROOT" status --short --branch
   ```

2. Update `setup-macos.sh` when the setup contract, generated files, embedding validation, or bootstrap flow changes.

3. Update `.agents/memory/SCHEMA.md`, `.agents/memory/INDEX.md`, and templates when the memory contract changes.

4. Verify before committing:

   ```bash
   bash -n "$AGENT_BASICS_ROOT/setup-macos.sh"
   ruby -c "$AGENT_BASICS_ROOT/Formula/agent-basics.rb"
   ```

5. For setup integration testing, run `setup-macos.sh` against a temporary directory with a local fake or real OpenAI-compatible embedding API.

## Agent Mailbox

This repo may contain `.agents/agent-mailbox/` with `inbox/`, `outbox`, and `archive/` folders.

Use timestamped markdown messages:

```text
YYYYMMDD-HHMMSS-topic.md
```

Mailbox messages should be short handoffs that name the sender, branch, relevant files or commands, and whether action is needed. Durable product decisions belong in `.agents/memory/`.
