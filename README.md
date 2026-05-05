# agent-basics

[中文](README.zh-CN.md)

baby's first coding agent harness.

`agent-basics` sets up a repository so coding agents have a predictable way to keep instructions, memory, and project context consistent.

It uses OpenViking as the memory and retrieval backend. `agent-basics` handles the repo side: instructions, setup, upgrade, MCP wiring, git hooks, and safe markdown conflict handling.

> This adds some prompt and workflow overhead. The tradeoff is better continuity and fewer lost decisions.

## What It Gives You

- A root `Agents.md` that agents can reliably discover.
- A repo-local `.agents/` workspace for agent instructions, skills, memory source files, and OpenViking metadata.
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

The Homebrew install bootstraps the shared OpenViking installation under `~/.openviking`, writes default config when missing, and attempts to install the macOS LaunchAgent. On suitable Apple Silicon hosts, it also attempts best-effort LM Studio setup: install the `lm-studio` cask, install a user LaunchAgent for the LM Studio server, write model defaults, download the configured chat/embedding models, and leave models available for JIT loading.

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

Set the installation-wide language to Simplified Chinese:

```bash
agent-basics setup --language zh-CN /path/to/project
```

The language preference is stored under `~/.agent-basics/config.toml`, not in each repo.

Re-running setup is the upgrade path:

```bash
agent-basics upgrade /path/to/project
```

If setup finds existing markdown files such as `Agents.md`, it asks whether to keep, replace, append, manually merge, use the local web merge UI, or save the incoming file beside the original.

## OpenViking

OpenViking is required and is bootstrapped during Homebrew install. To repair or rerun the full local runtime setup:

```bash
agent-basics ov bootstrap-system
agent-basics lmstudio bootstrap
agent-basics ov doctor
```

On macOS, bootstrap installs OpenViking as a user LaunchAgent so live search, ingest, and MCP calls can use the same always-on server. Foreground server mode is mainly for debugging:

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

Configure your MCP client to run `agent-basics mcp`. Do not pin the server to a project directory; agents pass their current working directory as the `cwd` tool argument.

Example:

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

For Codex Desktop:

- Name: `agent-basics`
- Transport: `STDIO`
- Command: `agent-basics`
- Arguments: `mcp`
- Working directory: leave unset/default
- Tool calls: pass `cwd` as the repository root or any directory inside it

## Daily Use

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
    ├── merge-sessions/
    └── backups/
```

Key files:

- `Agents.md`: root instructions agents should read first.
- `.agents/AGENT-BASICS.md`: operating notes for the agent-basics workflow.
- `.agents/memory/`: repo-owned memory and resource files that OpenViking ingests.
- `.agents/openviking/`: repo metadata, import state, locks, and migration records.
- `.agents/skills/` and `Skills.md`: repeatable workflows for agents.
- `.agents/TODO.md`: current work checklist; ignored by git.

## LM Studio

The default local setup expects LM Studio to expose an OpenAI-compatible API for the chat/VLM model and embedding model. Agents should use HTTP commands through `agent-basics lmstudio` for model management; bootstrap may install a LaunchAgent that runs `lms server start` outside the agent process.

```bash
agent-basics lmstudio bootstrap --dry-run
agent-basics lmstudio service status
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
