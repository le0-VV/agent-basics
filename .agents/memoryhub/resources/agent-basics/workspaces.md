# agent-basics and MemoryHub Workspaces

Use `/Users/leonardw/Projects/agent-basics` for setup/template work and `/Users/leonardw/Projects/MemoryHub` for central memory hub runtime work.

Keep the repositories separate:

- inspect both `git status --short --branch` outputs before editing
- preserve dirty MemoryHub files unless the user explicitly asks to change them
- commit each repo independently
- use `MEMORYHUB_SOURCE_DIR=/Users/leonardw/Projects/MemoryHub` when installing MemoryHub through `setup-macos.sh`

The central integration contract is documented in `WORKSPACES.md`.

