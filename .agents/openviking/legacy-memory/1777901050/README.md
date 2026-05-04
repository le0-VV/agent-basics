# Legacy Compatibility Memory Snapshot

Copied at Unix time `1777901050`.

This snapshot preserves the prior agent-basics compatibility memory tree for migration into OpenViking-native records. It intentionally excludes generated compatibility indexes such as `rag/index.sqlite` and `rag/manifest.json`.

## Contents

- `SCHEMA.md`: prior compatibility schema.
- `INDEX.md`: prior compatibility index.
- `templates/`: prior compatibility markdown templates.
- `memory/`: prior decision/fact/preference/gotcha/event records.
- `documentations/`: prior sources, procedures, and references.
- `rag/`: compatibility helper source/config files copied for audit.

## Migration Policy

Use `.agents/memory/ADAPTATION.md` to adapt useful records into `.agents/memory/memories/`, `.agents/memory/resources/`, or `.agents/memory/skills/`. Do not blindly import stale compatibility records.
