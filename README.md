# agent-basics

[中文](README.zh-CN.md)

baby's first coding agent harness.

`agent-basics` sets up a repository so coding agents have a predictable way to work across long sessions, handoffs, and repeated project updates.

It uses OpenViking as the memory and retrieval backend. `agent-basics` handles the repo side: instructions, setup, upgrade, MCP wiring, git hooks, run state, and safe markdown conflict handling.

> This adds some prompt and workflow overhead. The tradeoff is better continuity and fewer lost decisions.

## What It Gives You

- A root `Agents.md` that agents can reliably discover.
- A repo-local `.agents/` workspace for agent instructions, run state, skills, and OpenViking metadata.
- A user-level OpenViking install, normally under `~/.openviking`, shared across projects.
- Repo-aware MCP tools so agents can search and record project context through OpenViking.
- Git hooks that refresh OpenViking when repo memory files change.
- A safer setup and upgrade flow for existing projects, including markdown merge prompts.
- A supervised commit helper that uses the configured coding-agent author.

## Install

```bash
brew tap le0-VV/agent-basics https://github.com/le0-VV/agent-basics.git
brew install --HEAD le0-VV/agent-basics/agent-basics
```

Verify the command:

```bash
agent-basics --version
agent-basics doctor --online
```

## Set Up A Repo

For a new or existing project:

```bash
agent-basics setup /path/to/project
```

Use Chinese output and repo defaults:

```bash
agent-basics setup --language zh-CN /path/to/project
```

Re-running setup is the upgrade path:

```bash
agent-basics upgrade /path/to/project
```

If setup finds existing markdown files such as `Agents.md`, it asks whether to keep, replace, append, manually merge, use the local web merge UI, or save the incoming file beside the original.

## OpenViking

OpenViking is required. If it is missing, install and configure it with:

```bash
agent-basics ov install-system
agent-basics ov write-default-config --force
agent-basics ov service install
agent-basics ov doctor
```

On macOS, setup installs OpenViking as a user LaunchAgent so live search, ingest, and MCP calls can use the same always-on server. Foreground server mode is mainly for debugging:

```bash
agent-basics ov service status
agent-basics ov service restart
agent-basics ov server
```

Useful commands:

```bash
agent-basics ov status
agent-basics ov import-repo-memory --write
agent-basics ov search "what did we decide about memory?"
agent-basics ov record
agent-basics ov add-resource ./docs/api.md
agent-basics ov add-skill .agents/skills/finish-work.md
agent-basics ov ingest-changed
agent-basics ov install-hooks
```

## MCP Setup

Configure your MCP client to run `agent-basics mcp` from the repository root.

Example:

```json
{
  "mcpServers": {
    "agent-basics": {
      "command": "agent-basics",
      "args": ["mcp"],
      "cwd": "/path/to/project"
    }
  }
}
```

For Codex Desktop:

- Name: `agent-basics`
- Transport: `STDIO`
- Command: `agent-basics`
- Arguments: `mcp`
- Working directory: absolute path to the repository root

## Daily Use

Start or inspect long-running work:

```bash
agent-basics run start --task "ship the feature"
agent-basics run status
agent-basics run checkpoint --message "what changed"
agent-basics run handoff --message "handoff notes"
agent-basics run finish --message "done"
```

Validate and commit:

```bash
agent-basics verify
agent-basics commit "feat(scope): description"
```

The commit helper stages nothing by itself. Stage the intended files first, then commit.

## Repo Layout

After setup, a project usually has:

```text
.
├── Agents.md
├── ROADMAP.md
├── Skills.md
└── .agents/
    ├── AGENT-BASICS.md
    ├── TODO.md
    ├── config.toml
    ├── openviking/
    ├── memory/
    ├── skills/
    ├── runs/
    ├── merge-sessions/
    └── backups/
```

Key files:

- `Agents.md`: root instructions agents should read first.
- `.agents/AGENT-BASICS.md`: operating notes for the agent-basics workflow.
- `.agents/memory/`: repo-owned memory and resource files that OpenViking ingests.
- `.agents/openviking/`: repo metadata, import state, locks, and migration records.
- `.agents/skills/` and `Skills.md`: repeatable workflows for agents.
- `.agents/runs/`: local long-horizon run state and handoff files.
- `.agents/TODO.md`: current work checklist; ignored by git.

## LM Studio

The default local setup expects LM Studio to expose an OpenAI-compatible API for the chat/VLM model and embedding model. Agents should use HTTP commands through `agent-basics lmstudio`, not the `lms` CLI on macOS.

```bash
agent-basics lmstudio status
agent-basics lmstudio hardware
agent-basics lmstudio plan
agent-basics lmstudio configure --write
agent-basics lmstudio load --dry-run
agent-basics lmstudio route-test
```

## More Detail

- [ROADMAP.md](ROADMAP.md): direction and open design questions.
- [Agents.md](Agents.md): root agent instructions for this repository.
- [.agents/AGENT-BASICS.md](.agents/AGENT-BASICS.md): agent-basics operating details.
