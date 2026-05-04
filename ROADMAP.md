# Roadmap

`agent-basics` is a repo-local programming harness for AI coding agents.

The project should not grow into a second memory engine. OpenViking should own memory, resources, skills, semantic organization, and retrieval when it is viable. `agent-basics` should own the repository contract around that engine: setup, configuration, agent rules, tool wiring, long-horizon work state, validation, migration, and stable commands that agents can call with minimal permission friction.

## Product Direction

- `agent-basics` is the one-command Rust binary entry point.
- OpenViking is the required memory and context backend.
- `agent-basics` installs, verifies, configures, and wraps one user-level OpenViking installation, normally under `~/.openviking`.
- Repository-specific OpenViking metadata, migration manifests, and locks live under `.agents/`; the OpenViking package and workspace do not live inside each repository by default.
- Agents access OpenViking through `agent-basics mcp` or stable `agent-basics ov ...` commands, not by ad hoc shell commands.
- Root `Agents.md` remains the universal agent entrypoint.
- `.agents/AGENT-BASICS.md` contains the agent-basics operating contract that root `Agents.md` points to.
- `ROADMAP.md` records long-horizon project direction.
- `.agents/TODO.md` records current cross-session work state.
- `Skills.md` or `.agents/skills/` should describe repeated workflows, but executable work should be routed through stable `agent-basics` commands.
- Setup and upgrade must treat existing user instructions as valuable project data and provide safe merge/review paths.

## What agent-basics Is

`agent-basics` is the harness layer around a repository.

It answers practical questions:

- What instructions should agents load first?
- Which memory/context backend should agents use?
- How is the backend installed and checked?
- How do agents start, checkpoint, and finish long work?
- How do agents record useful findings for future sessions?
- Which commands are safe, stable, and worth approving once?
- Which repository files are generated, source-of-truth, or user-owned?
- How are setup conflicts reviewed without overwriting user knowledge?

## What agent-basics Is Not

`agent-basics` should avoid becoming:

- A full OpenViking replacement.
- A second long-term memory database.
- A second recursive context organizer.
- A full agentic coding runner before the repo harness is solid.
- A vendor-specific prompt bundle that only works in one agent app.

Custom markdown memory and mini-RAG work should be treated as transitional unless it remains useful as a compatibility or fallback layer.

## OpenViking Integration

The primary architecture should be:

```text
Agent client
  -> root Agents.md
  -> agent-basics MCP or CLI
  -> repo-aware OpenViking gateway
  -> user-level OpenViking plus repo metadata under .agents/
```

`agent-basics` should provide a repo-aware gateway instead of asking every agent to call OpenViking directly.

Responsibilities:

- Detect whether user-level OpenViking is installed.
- Install or guide installation when it is missing.
- Create repo-local OpenViking metadata and lock paths under `.agents/`.
- Keep OpenViking runtime data outside repositories unless the user explicitly chooses another user-level home.
- Verify the configured LLM/VLM and embedding providers.
- Configure local providers such as LM Studio when available.
- Run OpenViking doctor/health checks.
- Expose agent-safe MCP tools for search, record, resource add, skill add, ingest, and doctor.
- Keep raw OpenViking executable/config details out of normal agent workflows.

OpenViking should own:

- Memory storage and retrieval.
- Resource ingestion.
- Semantic summaries.
- Skill/resource/memory organization.
- Embedding indexes and vector search.

`agent-basics` should own:

- Repo setup and upgrade.
- Instruction files.
- Workflow rules.
- MCP wrapper.
- Git hooks and validation.
- Long-horizon task state.
- Merge UI and conflict safety.
- Stable commands and skill workflows.

## Repository Layout

Target layout:

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
    │   ├── repo.json
    │   ├── migration-manifest.json
    │   └── locks/
    ├── skills/
    │   ├── prework.md
    │   ├── memory-update.md
    │   └── finish-work.md
    ├── runs/
    │   └── <run-id>/
    │       ├── state.json
    │       ├── CHECKPOINT.md
    │       └── handoff.md
    ├── merge-sessions/
    └── backups/
```

The existing `.agents/memory/` tree remains important until OpenViking integration is proven and migration is implemented. The roadmap target is to demote custom RAG files to migration/fallback support, then remove them when OpenViking covers the needed behavior.

## Enforcement Model

There is no universal way to force every agent client to perform pre-work and post-work routines. `agent-basics` should use progressive enforcement.

Guidance:

- Root `Agents.md` and `.agents/AGENT-BASICS.md` define expected behavior.
- `Skills.md` and `.agents/skills/` define repeatable workflows.

Structured happy path:

- `agent-basics run start`
- `agent-basics ov search`
- `agent-basics ov record`
- `agent-basics run checkpoint`
- `agent-basics verify`
- `agent-basics run finish`

Boundary enforcement:

- Git hooks validate setup, memory/backend health, stale ingest state, and TODO/run consistency.
- CI can enforce the same checks before merge.
- Client-specific hooks can inject context or run checks where supported.

True enforcement:

- A future `agent-basics run "<task>"` runner could own the agent loop and enforce every pre/post routine.
- This should remain a later milestone, not the first implementation target.

## Long-Horizon Work

Long work needs state that survives chat compaction, branch switches, and agent handoff.

`ROADMAP.md`:

- Project direction.
- Design choices.
- Open questions.
- Milestones and non-goals.

`.agents/TODO.md`:

- Current work plan.
- Cross-session checklist.
- Must be updated while work progresses.
- Should be cleared and rewritten when a new work round starts.

`.agents/runs/<run-id>/`:

- Machine-readable run state.
- Human-readable checkpoint.
- Handoff note for the next agent/session.
- Links to OpenViking memory/resource records created during the run.

Near-term commands:

- `agent-basics run start [--task "..."]`
- `agent-basics run status`
- `agent-basics run checkpoint`
- `agent-basics run finish`
- `agent-basics run handoff`

## Skills And Stable Commands

Skills should reduce repeated prompt overhead and tell agents which workflow to follow. They should not be the only mechanism for reliability.

Initial skills:

- `prework`: read instructions, inspect TODO, query OpenViking, update the plan.
- `memory-update`: decide what is durable, record it through OpenViking, verify ingest.
- `finish-work`: run validation, update TODO, record findings, prepare/commit changes.

Each skill should point to stable commands. The goal is for users to approve command prefixes such as:

```bash
agent-basics ov
agent-basics run
agent-basics verify
agent-basics commit
```

instead of approving many small command variations.

## Setup Flow

`agent-basics setup [directory]` should:

1. Detect project root and git state.
2. Detect existing `Agents.md`, `.agents/AGENT-BASICS.md`, legacy `.agents/INSTRUCTIONS.md`, `.agents/memory/`, and existing OpenViking state.
3. Check whether OpenViking is installed.
4. Install OpenViking or stop with clear instructions when installation is not allowed.
5. Configure repo-local OpenViking metadata under `.agents/openviking/`.
6. Configure LLM/VLM and embedding providers.
7. Verify providers with a doctor check.
8. Write or merge root `Agents.md`.
9. Write or merge `.agents/AGENT-BASICS.md`.
10. Write `.agents/config.toml`.
11. Create `.agents/TODO.md`, `.agents/skills/`, `.agents/runs/`, `.agents/backups/`, and `.agents/merge-sessions/`.
12. Configure `agent-basics mcp` for the repository where possible.
13. Install git hooks.
14. Ingest initial project instructions and selected documentation into OpenViking.
15. Report final paths, health, and next agent actions.

`agent-basics upgrade [directory]` should perform the same checks but treat every existing file as user-owned unless the user explicitly accepts a merge or replacement.

## Migration UI

Build an interactive local web UI for existing projects that already contain agent instruction files.

Initial scope:

- Existing root `Agents.md`.
- Proposed root `Agents.md`.
- Existing `.agents/AGENT-BASICS.md` or legacy `.agents/INSTRUCTIONS.md`.
- Proposed `.agents/AGENT-BASICS.md`.
- Existing `.agents/memory/` markdown that may need migration into OpenViking.

The UI should let users:

- Compare existing and proposed markdown.
- See identical lines highlighted in green.
- See differing or conflicting lines highlighted in red.
- Pick which lines or blocks belong in the final file.
- Reorder selected instructions before writing.
- Preserve custom instruction ordering.
- Preview final markdown before applying changes.
- Save backups under `.agents/backups/`.
- Save unresolved sessions under `.agents/merge-sessions/`.
- Launch from setup conflict prompts.
- Fall back to `$EDITOR` when the web UI cannot run.

## CLI Modes

Core commands:

- `agent-basics setup [directory]`
- `agent-basics upgrade [directory]`
- `agent-basics doctor [--online]`
- `agent-basics mcp`
- `agent-basics ov <command>`
- `agent-basics run <command>`
- `agent-basics verify`
- `agent-basics commit`

OpenViking wrapper commands:

- `agent-basics ov doctor`
- `agent-basics ov install-system`
- `agent-basics ov write-default-config`
- `agent-basics ov search <query>`
- `agent-basics ov record`
- `agent-basics ov add-resource <path-or-url>`
- `agent-basics ov add-skill <path>`
- `agent-basics ov ingest-changed`
- `agent-basics ov status`
- `agent-basics lmstudio status`
- `agent-basics lmstudio hardware`
- `agent-basics lmstudio plan`
- `agent-basics lmstudio load`
- `agent-basics lmstudio unload`
- `agent-basics lmstudio route-test`

Migration commands:

- `agent-basics setup --dry-run <directory>`
- `agent-basics setup --merge-ui <directory>`
- `agent-basics migrate memory-to-openviking`

Compatibility commands:

- `agent-basics memory <command>` remains only while the custom markdown/RAG layer exists.
- `.agents/memory/rag/agent-memory.py` and `.agents/memory/rag/memory-mcp.py` are source-checkout fallbacks until they are removed or replaced by OpenViking-backed equivalents.

## Model Runtime

The local runtime target is LM Studio first, with other OpenAI-compatible providers allowed.

`agent-basics` should be able to:

- Detect available LM Studio models.
- Load and unload models through LM Studio's native REST API when the user allows it.
- Avoid the `lms` CLI from Codex on macOS because it can launch the LM Studio Electron app and crash during AppKit registration.
- Verify OpenAI-compatible chat and embedding endpoints.
- Configure OpenViking with the selected chat/VLM model and embedding model.
- Keep model/provider settings in config files, not scattered environment variables.
- Store only secret environment variable names, never raw secret values.
- Assess host hardware with stable macOS system APIs, then produce a deterministic load plan.

Known local setup:

- Chat/VLM: `google/gemma-4-e2b`
- Embeddings: `text-embedding-embeddinggemma-300m-qat`
- LM Studio base URL: `http://127.0.0.1:1234`

Gemma 4 E2B should be used with shallow structured-output schemas for routing and setup helpers. Deterministic code must validate and apply the result. The default load plan is max context, max GPU offload, concurrency 1, KV cache quantization `q4_0`, flash attention enabled, and temperature 0 for routing tests.

## Milestones

Milestone 1: roadmap and architecture reset.

- Treat OpenViking as the target memory backend.
- Mark custom mini-RAG as transitional.
- Define stable harness responsibilities.
- Define long-horizon run state.
- Define initial skills and stable command surfaces.

Milestone 2: OpenViking setup proof.

- Install and configure OpenViking through `agent-basics`.
- Create repo-local OpenViking metadata under `.agents/openviking/`.
- Verify LM Studio chat/VLM and embedding providers.
- Ingest this repo's current agent instructions and documentation.
- Prove search/record through a repo-aware wrapper.

Milestone 3: MCP gateway.

- Implement `agent-basics mcp` as the repo-aware OpenViking gateway.
- Require `repo_path` or current working directory resolution per tool call.
- Expose search, record, add-resource, add-skill, ingest, and doctor tools.
- Add tests for path safety and repo isolation.

Milestone 4: long-horizon workflow.

- Implement `agent-basics run start/status/checkpoint/finish/handoff`.
- Add `.agents/runs/` state.
- Update agent instructions to require run state for non-trivial work.
- Add git hook checks for incomplete or stale run state.

Milestone 5: skills and command approval reduction.

- Add `Skills.md` or `.agents/skills/`.
- Create prework, memory-update, and finish-work skills.
- Route each skill to stable `agent-basics` commands.
- Dogfood in sample repos and measure approval prompt reduction.

Milestone 6: migration UI.

- Wire the markdown merge prototype into setup.
- Support safe review of `Agents.md` and `.agents/AGENT-BASICS.md`.
- Support migration of legacy `.agents/memory/` markdown into OpenViking.
- Preserve backups and unresolved merge sessions.

Milestone 7: optional runner.

- Evaluate whether a full `agent-basics run "<task>"` agent runner is worth building.
- Only proceed if plugins, hooks, MCP, and git boundaries are not enough.
