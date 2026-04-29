# Roadmap

`agent-basics` should become an OpenViking-backed setup tool for agent-ready projects. OpenViking is not an optional enhancement: if a user does not want to install and configure OpenViking, they cannot use `agent-basics`.

## Product Principles

- `setup-macos.sh` remains the one-command entry point for macOS users.
- OpenViking is the canonical memory, documentation, skill, and project context store.
- OpenViking-related local files, configuration, backups, fallback exports, and setup metadata live under `.agents`.
- OpenViking uses a repo-local lightweight GGUF embedding model by default so new projects can start without external embedding credentials.
- `Agents.md` and `.agents/INSTRUCTIONS.md` are the only markdown instruction files `agent-basics` should create or normalize directly.
- Existing `.agents/DOCUMENTATIONS.md` and `.agents/MEMORY.md` files are migrated automatically into OpenViking before they are removed from the canonical structure. After that baseline migration, the user's own agents can migrate extra memories and documentation into richer OpenViking paths.
- `.agents/DOCUMENTATIONS.md` and `.agents/MEMORY.md` are removed from the canonical structure. OpenViking replaces them.
- Existing user instructions must be treated as valuable project data. Setup should provide review, ordering, and merge controls before changing them.

## Mandatory OpenViking Setup

1. Detect whether `openviking-server` is installed.
2. If OpenViking is missing, stop setup and offer to install it.
3. If the user declines OpenViking installation, exit without applying `agent-basics`.
4. Initialize OpenViking when needed, keeping project-local OpenViking files under `.agents`.
5. Run the OpenViking health check before writing agent instruction files.
6. Fail fast when OpenViking setup is unhealthy, with exact remediation commands.
7. Record setup metadata under an OpenViking path such as `viking://resources/agent-basics/setup/`.

## `.agents` OpenViking Layout

Use `.agents` as the visible project-local home for OpenViking integration files:

```text
.agents/
├── INSTRUCTIONS.md
├── TODO.md
└── openviking/
    ├── README.md
    ├── backups/
    ├── exports/
    ├── merge-sessions/
    └── setup-state/
```

The exact OpenViking database/storage location should follow OpenViking's documented configuration model. If OpenViking supports project-local storage, point it under `.agents/openviking/`. If it requires an external service or user-level store, keep project-local config, exports, and setup state under `.agents/openviking/`.

## Migration UI

Build an interactive local web UI for existing projects that already contain agent instruction files.

The first supported scope is intentionally narrow:

- Existing `Agents.md`
- agent-basics proposed `Agents.md`
- Existing `.agents/INSTRUCTIONS.md`
- agent-basics proposed `.agents/INSTRUCTIONS.md`

The UI should let users:

- Compare existing and proposed markdown.
- See identical lines highlighted in green.
- See differing or conflicting lines highlighted in red.
- Pick which lines or blocks belong in the final file.
- Reorder selected instructions before writing the final file.
- Preserve custom instruction ordering.
- Preview the final markdown before applying changes.
- Apply changes only after creating backups under `.agents/openviking/backups/`.
- Save an unresolved merge session under `.agents/openviking/merge-sessions/`.

Prefer block-level ordering with line-level highlighting:

- Headings and bullet groups are movable blocks.
- Individual lines remain selectable for fine-grained conflict resolution.
- The output preview should show exactly what will be written.

## Setup Flow

1. Start from `setup-macos.sh`.
2. Verify OpenViking installation.
3. Initialize/configure OpenViking for the project.
4. Scan for existing `Agents.md` and `.agents/INSTRUCTIONS.md`.
5. If either file conflicts with the embedded template, launch the merge UI.
6. Write the accepted `Agents.md` and `.agents/INSTRUCTIONS.md`.
7. Create `.agents/TODO.md` and `.agents/openviking/`; do not create `.agents/DOCUMENTATIONS.md` or `.agents/MEMORY.md`.
8. Store setup metadata and migration session summaries in OpenViking.
9. Initialize git when needed.
10. Report final paths, backup locations, and next agent migration tasks.

## CLI Modes

- `agent-basics <directory>`: interactive setup, mandatory OpenViking.
- `agent-basics --dry-run <directory>`: detect OpenViking/setup status and show pending file changes without writing.
- `agent-basics --merge-ui <directory>`: open the markdown merge UI directly.
- `agent-basics --doctor <directory>`: verify OpenViking and agent-basics setup health.

Non-interactive mode should remain conservative. It can validate and fail with a clear report, but it should not overwrite or merge instruction files without an explicit reviewed plan.

## Demo Milestone

The first demo is a static browser prototype that proves the markdown merge interaction:

- Two file tabs: `Agents.md` and `.agents/INSTRUCTIONS.md`
- Existing and proposed line sources
- Green identical-line highlighting
- Red differing-line highlighting
- Pick, remove, and reorder controls
- Final markdown preview

This demo is not the production migration engine. It is a UX checkpoint before adding OpenViking setup, local server wiring, file writes, and backup/session persistence.
