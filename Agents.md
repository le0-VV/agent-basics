# Agent Base Instructions

## Protected Files

- **DO NOT**, unless explicitly instructed by the user, modify `Agents.md` or `.agents/AGENT-BASICS.md`.
- Follow `.agents/AGENT-BASICS.md` for agent-basics memory, documentation, RAG, setup, and repository workflow rules.

## Base Rules

- Be logical.
- For coding tasks, never use placeholders or omit required code in snippets.
- If you hit a character limit, stop abruptly; the user will send `continue`.
- Do not overlook critical context.
- If you have questions or concerns that block safe progress, clarify with the user immediately.

## Memory First

- Use `.agents/memory/` as the canonical project memory and documentation source.
- Before answering a request that may depend on prior project context, call the memory MCP server's `memory_search` tool. If MCP is unavailable, search `.agents/memory/INDEX.md` and use `agent-basics memory search "<query>"` or `.agents/memory/rag/agent-memory.py search "<query>"` as a fallback.
- Anything the user asks you to remember must be recorded with the memory MCP server's `memory_record` tool. If MCP is unavailable, use `agent-basics memory record` or `.agents/memory/rag/agent-memory.py record`.
- Do not edit `.agents/memory/**` while `.agents/memory/rag/write.lock/` exists.
- If you add, move, or remove memory/documentation files, keep `.agents/memory/INDEX.md` current and rebuild or validate the memory index.

## Work Rules

- Before making codebase changes, write the concrete plan in `.agents/TODO.md` and follow it.
- Read a file fully before editing it.
- Keep comments rare and useful. Explain why or constraints, not obvious mechanics.
- Keep diffs narrow and task-focused.
- Do not guess at attribute names, control flow, or config behavior.
- Prefer fail-fast behavior over silent fallback logic.
- Add tests for new behavior unless the change is strictly docs/metadata cleanup.
- Tick off every completed item in `.agents/TODO.md`.
- After ticking off an item, commit the changes made for that item.
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
2. Combine project context and clear reasoning to answer with concrete details.
3. Use the memory RAG before relying on assumptions about prior work.
4. Keep answers direct and actionable.
