# Agent Mailbox

This directory is a low-tech cross-sandbox communication channel for agents working across `agent-basics` and `MemoryHub`.

Use it when separate agents or sandbox sessions need to coordinate without sharing process state.

## Layout

```text
.agents/agent-mailbox/
├── inbox/      # messages addressed to agents in this repo
├── outbox/     # messages this repo's agents want the other repo to read
└── archive/    # consumed messages, when the repo owner approves archiving
```

## Message Format

Create markdown files with timestamped names:

```text
YYYYMMDD-HHMMSS-to-agent-basics-topic.md
YYYYMMDD-HHMMSS-to-memoryhub-topic.md
```

Each message should include:

- sender repo and branch
- target repo
- short summary
- exact files or commands involved
- whether a response or action is needed

## Rules

- Do not use the mailbox as a source of truth for product behavior; record durable decisions in normal docs or tests.
- Do not delete or rewrite another agent's message unless the user explicitly asks.
- Keep messages short and actionable.
- Check both repos' `git status --short --branch` before acting on a mailbox request.

