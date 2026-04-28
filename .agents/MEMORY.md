# Memory Fallback

Use OpenViking as the canonical memory store for this repo.

This file is only a local fallback and migration queue for environments where OpenViking is unavailable. When OpenViking becomes available, migrate entries into the matching `viking://` paths and remove the migrated fallback notes.

## `viking://user/memories/preferences/agent-basics.md`

- Always keep markdown files ending with an empty trailing line.

## `viking://agent/memories/patterns/agent-basics.md`

- `setup-macos.sh` is intended to be the complete one-command setup surface for this project, so generated markdown templates should remain embedded in the script.
- Keep OpenViking-related local files, configuration, and fallback/export material under `.agents`.

## Migration Queue

- [ ] Migrate the fallback entries above into OpenViking when an OpenViking server is available.
