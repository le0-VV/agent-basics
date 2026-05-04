---
id: ov-memory-1777901050-legacy-memory-snapshot-created
record_kind: memory
ov_category: events
title: Legacy compatibility memory snapshot created
status: recorded
created: 1777901050
updated: 1777901050
tags: [openviking, migration, memory-layout]
summary: The previous compatibility .agents/memory source tree was copied to .agents/openviking/legacy-memory/1777901050 before reshaping .agents/memory for OpenViking.
source_paths: []
requires_human_review: false
event_timestamp: 1777901050
---

# Legacy compatibility memory snapshot created

## Event

The previous compatibility `.agents/memory/` source tree was copied to `.agents/openviking/legacy-memory/1777901050/` before `.agents/memory/` was redirected toward the OpenViking source-store layout.

## Impact

Future agents can use the snapshot as migration input and audit evidence while adapting useful records into `.agents/memory/memories/`, `.agents/memory/resources/`, and `.agents/memory/skills/`.

## Related

- `.agents/openviking/legacy-memory/1777901050/README.md`
- `.agents/memory/ADAPTATION.md`
