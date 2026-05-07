# Roadmap

`agent-basics` is a repo-local programming harness for AI coding agents.

The project should not grow into a second memory engine. OpenViking should own memory, resources, skills, semantic organization, and retrieval when it is viable. `agent-basics` should own the repository contract around that engine: setup, configuration, agent rules, tool wiring, long-horizon work state, validation, migration, and stable commands that agents can call with minimal permission friction.

## Product Direction

- `agent-basics` is one user-facing command entry point. Rust binary packaging is optional future work, not a required product constraint.
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

## Current State

This section separates shipped behavior from target architecture.

Implemented and verified in this repository:

- User-level OpenViking is installed under `~/.openviking`.
- Homebrew install runs `agent-basics ov bootstrap-system` to install/configure OpenViking, package the OpenViking server as `~/.openviking/openviking`, attempt macOS LaunchAgent setup, and run best-effort MLX runtime/model setup.
- OpenViking is configured for the local agent-basics MLX chat/VLM and embedding endpoints.
- `.agents/memory/` is preserved as the repo-owned OpenViking source store.
- `.agents/openviking/migration-manifest.json` records migration/adaptation state.
- `.agents/openviking/import-state.json` records import hashes, targets, and status.
- `agent-basics ov import-repo-memory --write` writes reviewed OV-native memory files directly into OpenViking memory categories.
- `agent-basics ov import-repo-memory --write` ingests reviewed source-store resources through OpenViking resource ingestion.
- Direct `ov read` and semantic `ov find` were verified against imported repo memory.
- `agent-basics ov search`, `read`, `record`, `add-resource`, `add-skill`, `ingest-changed`, `server`, and `status` are implemented as repo-aware OpenViking wrappers.
- `agent-basics mcp` is implemented as a repo-aware OpenViking-backed stdio MCP server.
- MLX is the bundled local runtime on Apple Silicon; non-MLX providers are configured as custom OpenAI-compatible APIs instead of provider-specific command families.
- Setup/upgrade creates the modern source-store structure, verifies or installs user-level OpenViking, writes `.agents/config.toml`, generates a Codex-style MCP snippet, creates `Skills.md` plus `.agents/skills/`, and creates first-class markdown merge sessions for conflicts.
- Managed OpenViking hooks refresh source-store changes before commits.
- Fast dogfood coverage exercises fresh setup and existing-repo upgrade with fake user-level OpenViking.

Still transitional or incomplete:

- The custom mini-RAG still exists as fallback compatibility under `compat/memory-rag/`.
- Decision: keep checked-in compatibility source outside `.agents/memory/` so the active source store stays OpenViking-native. Fresh setup must not install the mini-RAG into target repos unless `AGENT_BASICS_INSTALL_COMPAT_MEMORY=1` is set.
- Broader live dogfood against real OpenViking/MLX should continue, especially for large ingests and model/provider edge cases.

## What agent-basics Is

`agent-basics` is the harness layer around a repository.

It answers practical questions:

- What instructions should agents load first?
- Which memory/context backend should agents use?
- How is the backend installed and checked?
- How do agents preserve handoff context across app/client sessions without a custom run-state command?
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

One OpenViking server should handle many repositories. Repository isolation should come from repo-scoped URI namespaces and repo metadata, not from one OpenViking installation per repo:

```text
viking://user/default/memories/<category>/projects/<repo-slug>/<file>.md
viking://resources/projects/<repo-slug>/...
```

The gateway should infer the repository from `cwd` by default, allow an explicit `repo_path` for MCP clients that cannot set `cwd`, and scope search/write operations to the current repository unless the caller explicitly requests wider search.

Responsibilities:

- Detect whether user-level OpenViking is installed.
- Install or guide installation when it is missing.
- Create repo-local OpenViking metadata and lock paths under `.agents/`.
- Keep OpenViking runtime data outside repositories unless the user explicitly chooses another user-level home.
- Verify the configured LLM/VLM and embedding providers.
- Configure OpenViking for the bundled MLX server or a user-supplied custom OpenAI-compatible API.
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
    │   ├── legacy-memory/
    │   └── locks/
    ├── memory/
    │   ├── SCHEMA.md
    │   ├── INDEX.md
    │   ├── ADAPTATION.md
    │   ├── memories/
    │   ├── resources/
    │   ├── skills/
    │   └── imports/
    ├── skills/
    │   ├── prework.md
    │   ├── memory-update.md
    │   └── finish-work.md
    ├── merge-sessions/
    └── backups/
```

`.agents/memory/` remains important permanently as the repo-owned OpenViking source store. The roadmap target is to adapt old custom mini-RAG memory into OV-native `memories/`, `resources/`, and `skills/` files, preserve legacy snapshots under `.agents/openviking/legacy-memory/`, and keep custom RAG code isolated as fallback support under `compat/memory-rag/` until it is retired or split out.

Fresh setup should create only the OpenViking source-store shape under `.agents/memory/`. Existing legacy mini-RAG trees should be copied to `.agents/openviking/legacy-memory/<unix-timestamp>/` as migration input, not reinstalled into new projects unless the user explicitly enables compatibility fallback.

Current `.agents/memory/` status:

- Canonical OV source store: `.agents/memory/memories/`, `.agents/memory/resources/`, `.agents/memory/skills/`, `.agents/memory/imports/`, `SCHEMA.md`, `INDEX.md`, and `ADAPTATION.md`.
- Legacy/transitional compatibility snapshots: `.agents/openviking/legacy-memory/`.
- Compatibility mini-RAG implementation: `compat/memory-rag/`.
- `agent-basics ov import-repo-memory` imports canonical OV source-store files and ignores archived legacy material unless it has been adapted into the canonical layout.

## Enforcement Model

There is no universal way to force every agent client to perform pre-work and post-work routines. `agent-basics` should treat those routines as instruction-driven behavior, not as local run-state enforcement.

Guidance:

- Root `Agents.md` and `.agents/AGENT-BASICS.md` define expected behavior.
- `Skills.md` and `.agents/skills/` define repeatable workflows.

Structured happy path:

- Agent reads `Agents.md`, `.agents/AGENT-BASICS.md`, `Skills.md`, `ROADMAP.md`, and `.agents/TODO.md`.
- Agent searches OpenViking through MCP before context-dependent work.
- Agent records durable findings through MCP/OpenViking.
- Agent validates, updates `.agents/TODO.md`, summarizes the handoff, and commits when appropriate.

Boundary enforcement:

- Git hooks validate OpenViking source-store ingest state where possible.
- CI can enforce the same checks before merge.
- Client-specific hooks can inject context or run checks where supported.

## Long-Horizon Work

Long work needs state that survives chat compaction, branch switches, and agent handoff without requiring users to leave their agent app or CLI.

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

Handoff should use existing surfaces:

- `.agents/TODO.md` for current checklist and blockers.
- OpenViking records for durable decisions, preferences, facts, cases, events, patterns, tools, and skills.
- Git commits, branches, pull requests, and review comments for operational transfer.
- Chat handoff notes when the agent app provides them.

`agent-basics` intentionally does not own a local `run` lifecycle command.

## Skills And Stable Commands

Skills should reduce repeated prompt overhead and tell agents which workflow to follow. They should not be the only mechanism for reliability.

Initial skills:

- `prework`: read instructions, inspect TODO, query OpenViking, update the plan.
- `memory-update`: decide what is durable, record it through OpenViking, verify ingest.
- `finish-work`: run validation, update TODO, record findings, prepare/commit changes.

Each skill should point to stable commands. The goal is for users to approve command prefixes such as:

```bash
agent-basics ov
agent-basics verify
agent-basics commit
```

instead of approving many small command variations.

## Distribution Packaging

Near-term distribution should prefer the smallest reliable command surface that works on a normal macOS developer machine. A shell/Python command wrapper is acceptable if it avoids forcing users to download Rust, LLVM, and a full native build toolchain during installation.

Rust can remain potential future work if it improves distribution or runtime reliability without increasing install friction. If Rust packaging is revived, prefer prebuilt release artifacts or maintainer-only build steps so end users are not required to build the binary locally.

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
11. Create `.agents/TODO.md`, `.agents/skills/`, `.agents/backups/`, and `.agents/merge-sessions/`.
12. Configure `agent-basics mcp` for the repository where possible.
13. Install git hooks.
14. Snapshot any existing legacy `.agents/memory/{templates,memory,documentations,rag}` material before adaptation.
15. Ingest initial project instructions and selected documentation into OpenViking.
16. Report final paths, health, and next agent actions.

`agent-basics upgrade [directory]` should perform the same checks but treat every existing file as user-owned unless the user explicitly accepts a merge or replacement.

## Migration UI

Build an interactive local web UI for existing projects that already contain agent instruction files.

Initial scope:

- Existing root `Agents.md`.
- Proposed root `Agents.md`.
- Existing `.agents/AGENT-BASICS.md` or legacy `.agents/INSTRUCTIONS.md`.
- Proposed `.agents/AGENT-BASICS.md`.
- Existing `.agents/memory/` or legacy agent-basics markdown that may need adaptation into the OV-native source-store layout.

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

Status legend:

- Implemented: callable and covered by basic tests or manual verification.
- Partial: callable, but behavior is compatibility-backed or lacks the final OpenViking/repo-aware contract.
- Planned: target interface only.

Core commands:

| Command | Status | Notes |
| --- | --- | --- |
| `agent-basics setup [directory]` | Implemented | Creates the modern source-store shape, verifies or installs user-level OV, writes repo config, emits MCP snippets, creates skills, and opens or records merge UI sessions for markdown conflicts. |
| `agent-basics upgrade [directory]` | Implemented | Uses the setup path for existing repos; existing user files stay user-owned unless a safe merge/replace/append/save path is selected. |
| `agent-basics doctor [--online]` | Partial | Needs stronger OV/provider/repo-state checks. |
| `agent-basics mcp` | Implemented | Repo-aware OpenViking-backed MCP server with search, read, record, add-resource, add-skill, ingest, status, and doctor tools. |
| `agent-basics ov <command>` | Implemented | Repo-aware setup/import/search/read/record/resource/skill/server/status wrappers exist; polish remains for setup integration. |
| `agent-basics mlx <command>` | In progress | Default local Apple Silicon runtime status/install/pull/service/server/bootstrap for MLX chat/VLM and embedding models. |
| `agent-basics migrate memory-to-openviking` | Implemented | Inventories/adapts legacy memory into OV-native categories and manifest state. |
| `agent-basics memory <command>` | Implemented | Transitional mini-RAG compatibility only. |
| `agent-basics verify` | Implemented | Runs unit tests, Cargo tests, shell syntax, formula syntax, and offline OV status when available. |
| `agent-basics commit` | Implemented | Commits staged changes with the supervised coding-agent author and validates commit-message shape. |

OpenViking wrapper commands:

| Command | Status | Notes |
| --- | --- | --- |
| `agent-basics ov doctor` | Partial | Should become the full OV install/config/provider/repo-state doctor. |
| `agent-basics ov install-system` | Implemented | Installs OpenViking under user-level home. |
| `agent-basics ov bootstrap-system` | Implemented | Idempotently installs OpenViking when missing, writes default user-level config, and installs the macOS service when available. |
| `agent-basics ov write-default-config` | Implemented | Writes provider-backed `ov.conf` plus `ovcli.conf` with long local HTTP timeouts. MLX is the default provider target. |
| `agent-basics ov server` | Implemented | Starts the configured user-level OpenViking HTTP server in the foreground. |
| `agent-basics ov import-repo-memory` | Implemented | Writes OV-native memories directly and ingests source-store resources/skills. |
| `agent-basics ov search <query>` | Implemented | Repo-scoped semantic search wrapper. |
| `agent-basics ov read <uri>` | Implemented | Exact read wrapper for URIs returned by search. |
| `agent-basics ov record` | Implemented | Durable memory writer with category validation and repo source-store files. |
| `agent-basics ov add-resource <path-or-url>` | Implemented | Repo-aware resource ingestion wrapper. |
| `agent-basics ov add-skill <path>` | Implemented | Registers skills through OpenViking; OpenViking currently does not expose a target URI for skills. |
| `agent-basics ov ingest-changed` | Implemented | Incremental import/ingest after source-store changes. |
| `agent-basics ov install-hooks` | Implemented | Installs managed `pre-commit` and `post-merge` hooks that run repo-scoped OpenViking ingest for source-store changes. |
| `agent-basics ov status` | Implemented | Repo-scoped import, source-store, namespace, and OpenViking status. |

MLX runtime commands:

| Command | Status | Notes |
| --- | --- | --- |
| `agent-basics mlx status` | In progress | Checks the agent-basics MLX OpenAI-compatible server and configured model ids. |
| `agent-basics mlx install` | In progress | Creates a user-level MLX Python environment under `~/.agent-basics/mlx`. |
| `agent-basics mlx write-server` | Compatibility fallback | Installs a script-based `agent-basics-mlx` OpenAI-compatible MLX process when standalone packaging is disabled. |
| `agent-basics mlx package` | In progress | Builds the Python MLX server into a one-file `agent-basics-mlx` executable with PyInstaller. |
| `agent-basics mlx pull` | In progress | Downloads configured Hugging Face MLX model snapshots. |
| `agent-basics mlx service` | In progress | Installs and manages a macOS LaunchAgent for the MLX runtime. |
| `agent-basics mlx server` | In progress | Runs `agent-basics-mlx` in the foreground for debugging. |
| `agent-basics mlx bootstrap` | In progress | Orchestrates install, standalone server packaging, model download, service setup, and health checks. |

OpenViking runtime commands:

| Command | Status | Notes |
| --- | --- | --- |
| `agent-basics ov package-server` | In progress | Builds the OpenViking server entrypoint into a one-file `openviking` executable with PyInstaller so macOS process listings do not show the service as `python3.12`. |
| `agent-basics ov service` | Implemented | Installs and manages a macOS LaunchAgent that prefers the packaged `~/.openviking/openviking` server executable. |
| `agent-basics ov bootstrap-system` | Implemented | Orchestrates OpenViking install, server packaging, config, service setup, and bundled runtime setup. |

`agent-basics ov import-repo-memory` should write OV-native memory source files directly into `viking://user/default/memories/<category>/projects/<repo>/` and use OpenViking resource/skill ingestion only for resources and skills. Repo source memory should not depend on `ov add-memory` extraction to rediscover already-structured records. Memory writes should retry when OpenViking reports a busy memory tree because previous extraction or indexing jobs may still hold locks.

Migration commands:

- `agent-basics setup <directory>`
- `agent-basics upgrade <directory>`
- `agent-basics migrate memory-to-openviking`

Compatibility commands:

- `agent-basics memory <command>` remains only while the custom markdown/RAG layer exists.
- `compat/memory-rag/agent-memory.py` and `compat/memory-rag/memory-mcp.py` are source-checkout fallback implementations. Explicit compatibility installs still copy them into `.agents/memory/rag/` inside target repositories.

## Model Runtime

The local runtime target is the agent-basics MLX server first on supported Apple Silicon Macs, with other OpenAI-compatible providers allowed as fallbacks. For the first release, bundled local MLX support requires an Apple Silicon Mac with at least 16 GB unified memory.

`agent-basics` should be able to:

- Install a user-level MLX runtime under `~/.agent-basics/mlx`.
- Package and run the local server as the standalone `agent-basics-mlx` executable so macOS process listings do not show the long-running server as `python3.12`.
- Download configured Hugging Face MLX model snapshots and verify that `/v1/models` exposes them.
- Verify OpenAI-compatible chat and embedding endpoints.
- Launch OpenViking with localhost proxy bypass variables so local runtime requests do not get intercepted by system HTTP proxies.
- Configure OpenViking with the selected chat/VLM model and embedding model.
- Keep model/provider settings in config files, not scattered environment variables.
- Store only secret environment variable names, never raw secret values.
- Assess host hardware with stable macOS system APIs when choosing larger local models.

Known local setup:

- Chat/VLM: `mlx-community/gemma-4-e2b-it-4bit`
- Embeddings: `mlx-community/embeddinggemma-300m-4bit`
- MLX base URL: `http://127.0.0.1:18080`
- First-release local MLX hardware floor: Apple Silicon Mac with at least 16 GB unified memory
- Custom API providers must expose OpenAI-compatible `/v1/chat/completions`, `/v1/embeddings`, and `/v1/models` endpoints.

Gemma 4 E2B should be used with shallow structured-output schemas for routing and setup helpers. Deterministic code must validate and apply the result. OpenViking should send request-time prompt/schema settings instead of relying on provider UI defaults.

## Immediate Next Work

The next unlock is hardening the now-usable OpenViking-backed harness:

1. Run longer live dogfood passes against real OpenViking/MLX on messy existing repositories.
2. Decide whether `compat/memory-rag/` should be retired completely or split into a separate legacy package after old-repo fallback support has a stable distribution path.
3. Add CI examples that run `agent-basics verify` plus `agent-basics ov status --offline`.
4. Measure whether `Skills.md` plus stable command prefixes actually reduce approval prompts in sample project work.
5. Defer a full agent runner until hooks, MCP, skills, and command workflows show a concrete gap.

## Milestones

Milestone 1: roadmap and architecture reset.

Status: complete.

- Treat OpenViking as the target memory backend.
- Mark custom mini-RAG as transitional.
- Define stable harness responsibilities.
- Define long-horizon handoff as instruction-driven state in `.agents/TODO.md`, OpenViking, and git.
- Define initial skills and stable command surfaces.

Milestone 2: OpenViking setup proof.

Status: complete for this repository.

- Install and configure OpenViking through `agent-basics`.
- Create repo-local OpenViking metadata under `.agents/openviking/`.
- Verify bundled MLX chat/VLM and embedding providers.
- Ingest this repo's current agent instructions and documentation.
- Prove search/record through a repo-aware wrapper.

Acceptance criteria:

- A fresh repo can install or verify user-level OpenViking without placing the OpenViking package/workspace in the repo.
- `agent-basics ov import-repo-memory --write` imports reviewed OV-native memory/resources/skills and records import state.
- `agent-basics ov search` and `agent-basics ov read` can retrieve imported repo context without raw `ov` calls.

Milestone 3: MCP gateway.

Status: implemented, with broader live integration tests still planned.

- Keep `agent-basics mcp` as the repo-aware OpenViking gateway.
- Require `cwd` or backward-compatible `repo_path` resolution per tool call.
- Maintain search, read, record, add-resource, add-skill, ingest, status, and doctor tools.
- Add broader tests for path safety and repo isolation.

Acceptance criteria:

- A Codex custom MCP config can use `command: agent-basics`, `args: ["mcp"]`, and no fixed working directory.
- Agents pass `cwd` on each repo-scoped tool call.
- Every MCP tool resolves a repository root before touching OpenViking.
- Search defaults to the current repo namespace and can optionally include wider context.
- Record writes to the correct `viking://user/default/memories/<category>/projects/<repo-slug>/` namespace.
- Add-resource writes to the correct `viking://resources/projects/<repo-slug>/` namespace; add-skill uses OpenViking's skill registration surface and includes repo attribution in source content.
- Tests cover at least two repositories sharing one mocked OpenViking command layer; a live shared-server test is still desirable.

Milestone 4: command-backed long-horizon workflow.

Status: retired.

- Earlier builds implemented `agent-basics run start/status/checkpoint/finish/handoff`.
- Decision: retire this surface from setup, docs, and enforcement.
- Rationale: users operate through agent apps/CLIs, and agents can only be reliably nudged by instructions, MCP tools, git state, and OpenViking memory.
- Handoff belongs in `.agents/TODO.md`, OpenViking, git commits/PRs, and agent-app handoff notes.

Acceptance criteria:

- Fresh setup does not create `.agents/runs/`.
- Git hooks do not block on run state.
- Agent instructions and skills describe pre/post work routines without requiring `agent-basics run`.

Milestone 5: skills and command approval reduction.

Status: implemented, with measurement still planned.

- Add `Skills.md` or `.agents/skills/`.
- Create prework, memory-update, and finish-work skills.
- Route each skill to stable `agent-basics` commands.
- Dogfood in sample repos and measure approval prompt reduction.

Acceptance criteria:

- Repeated workflows are documented as skills and backed by stable command prefixes.
- Sample repo runs need fewer one-off approvals than the current ad hoc command flow.

Milestone 6: migration UI.

Status: implemented for markdown instruction conflicts; broader memory adaptation UI remains planned.

- Wire the markdown merge prototype into setup.
- Support safe review of `Agents.md` and `.agents/AGENT-BASICS.md`.
- Support migration of legacy agent-basics markdown into `.agents/memory/` OV-native source files and then into OpenViking in a later expansion.
- Preserve backups and unresolved merge sessions.

Acceptance criteria:

- Setup conflict prompts can launch the markdown merge UI.
- Users can select, reorder, preview, and save merged instruction files.
- Backups and unresolved sessions are written under `.agents/`.

Milestone 7: optional runner.

Status: rejected for current scope.

- Do not build a custom agent runner unless agent-basics changes scope into an agent framework.
- Keep agent-basics as setup, MCP, OpenViking, hooks, migration, docs, and install tooling.
