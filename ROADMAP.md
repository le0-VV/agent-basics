# Roadmap

`agent-basics` should become a MemoryHub-backed setup tool for agent-ready projects. MemoryHub is not an optional enhancement: if a user does not want to install and configure the central MemoryHub dependency, they cannot use `agent-basics`.

## Product Principles

- `setup-macos.sh` remains the one-command entry point for macOS users.
- MemoryHub is the canonical memory, documentation, skill, and project context store for agent-basics.
- MemoryHub owns the single OpenViking/runtime/embedding installation for all agent-basics projects.
- MemoryHub remains a separate dependency and source repository; `agent-basics` documents the cross-repo workflow but does not vendor MemoryHub code.
- Project memory files remain in the repository under `.agents/memoryhub/`; the central hub references them through symlinks under `$MEMORYHUB_CONFIG_DIR/projects/`.
- MemoryHub-related project files, backups, merge sessions, and setup metadata live under `.agents`.
- `Agents.md` and `.agents/INSTRUCTIONS.md` are the only markdown instruction files `agent-basics` should create or normalize directly.
- Existing `.agents/DOCUMENTATIONS.md` and `.agents/MEMORY.md` files are migrated automatically into `.agents/memoryhub/` before they are removed from the canonical structure. After that baseline migration, the user's own agents can migrate extra memories and documentation into richer MemoryHub paths.
- `.agents/DOCUMENTATIONS.md` and `.agents/MEMORY.md` are removed from the canonical structure. MemoryHub replaces them.
- Existing user instructions must be treated as valuable project data. Setup should provide review, ordering, and merge controls before changing them.

## Mandatory MemoryHub Setup

1. Detect whether the central `memoryhub` executable is available.
2. If MemoryHub is missing, stop setup and offer to install it into `$MEMORYHUB_CONFIG_DIR/venv`.
3. If the user declines MemoryHub installation, exit without applying `agent-basics`.
4. Initialize the central MemoryHub config and database when needed.
5. Create the repo-local `.agents/memoryhub/` markdown source tree.
6. Create or validate the `$MEMORYHUB_CONFIG_DIR/projects/<project>` symlink to the repo-local markdown source tree.
7. Register the project with MemoryHub so cwd/project resolution can find it.
8. Run the MemoryHub health check before writing agent instruction files.
9. Fail fast when MemoryHub setup is unhealthy, with exact remediation commands.
10. Record setup metadata under `.agents/memoryhub/resources/agent-basics/setup/`.

## Cross-Repo Development

`agent-basics` and MemoryHub are expected to be developed as sibling repositories. The durable workflow lives in [WORKSPACES.md](WORKSPACES.md).

Cross-repo tasks should keep ownership clear:

- `agent-basics`: setup script, Homebrew formula, generated instruction templates, repository memory layout, migration UI, bootstrap docs
- MemoryHub: memory runtime, CLI/API/MCP behavior, project registry, sync/indexing, config, tests

Changes spanning both repos should be tested and committed independently in each git worktree.

## `.agents` MemoryHub Layout

Use `.agents` as the visible project-local home for MemoryHub source files and setup artifacts:

```text
.agents/
├── INSTRUCTIONS.md
├── TODO.md
└── memoryhub/
    ├── README.md
    ├── agent/
    │   ├── memories/
    │   └── skills/
    ├── backups/
    ├── merge-sessions/
    ├── resources/
    ├── setup-state/
    └── user/
        └── memories/
```

The central MemoryHub runtime should default to `$HOME/.memoryhub`. Its `projects/` directory contains symlinks to each repository's `.agents/memoryhub/` directory. This keeps memory files versionable with the project while avoiding per-repo runtime installations.

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
- Apply changes only after creating backups under `.agents/memoryhub/backups/`.
- Save an unresolved merge session under `.agents/memoryhub/merge-sessions/`.

Prefer block-level ordering with line-level highlighting:

- Headings and bullet groups are movable blocks.
- Individual lines remain selectable for fine-grained conflict resolution.
- The output preview should show exactly what will be written.

## Setup Flow

1. Start from `setup-macos.sh`.
2. Verify MemoryHub installation.
3. Initialize/configure the central MemoryHub hub.
4. Create the repo-local `.agents/memoryhub/` tree and hub symlink.
5. Register the repo with MemoryHub.
6. Scan for existing `Agents.md` and `.agents/INSTRUCTIONS.md`.
7. If either file conflicts with the embedded template, launch the merge UI.
8. Write the accepted `Agents.md` and `.agents/INSTRUCTIONS.md`.
9. Create `.agents/TODO.md` and `.agents/memoryhub/`; do not create `.agents/DOCUMENTATIONS.md` or `.agents/MEMORY.md`.
10. Store setup metadata and migration session summaries in MemoryHub markdown.
11. Initialize git when needed.
12. Report final paths, backup locations, and next agent migration tasks.

## CLI Modes

- `agent-basics <directory>`: interactive setup, mandatory MemoryHub.
- `agent-basics --dry-run <directory>`: detect MemoryHub/setup status and show pending file changes without writing.
- `agent-basics --merge-ui <directory>`: open the markdown merge UI directly.
- `agent-basics --doctor <directory>`: verify MemoryHub and agent-basics setup health.

Non-interactive mode should remain conservative. It can validate and fail with a clear report, but it should not overwrite or merge instruction files without an explicit reviewed plan.

## Demo Milestone

The first demo is a static browser prototype that proves the markdown merge interaction:

- Two file tabs: `Agents.md` and `.agents/INSTRUCTIONS.md`
- Existing and proposed line sources
- Green identical-line highlighting
- Red differing-line highlighting
- Pick, remove, and reorder controls
- Final markdown preview

This demo is not the production migration engine. It is a UX checkpoint before adding MemoryHub setup, local server wiring, file writes, and backup/session persistence.
