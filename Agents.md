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
- Prefer the repo-aware agent-basics OpenViking gateway over direct OpenViking calls. Use `agent-basics mcp` and `agent-basics ov ...` commands when they are available.
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

1. Use the language of the user's message.
2. Search OpenViking or the compatibility memory layer before relying on assumptions about prior work.
3. Combine project context and clear reasoning to answer with concrete details.
4. Keep answers direct and actionable.
