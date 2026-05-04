---
id: ov-memory-1777901050-keep-memory-as-ov-source-store
record_kind: memory
ov_category: preferences
title: Keep .agents/memory as the OpenViking source store
status: active
created: 1777901050
updated: 1777901050
tags: [openviking, memory-layout, setup]
summary: The user wants .agents/memory to remain as the repo-specific OpenViking file store instead of being deleted after migration.
source_paths: []
requires_human_review: false
---

# Keep .agents/memory as the OpenViking source store

## Memory

The user wants `.agents/memory/` to remain in repositories as the repo-specific OpenViking file store. Migration should reshape this directory into an OpenViking-compliant source layout rather than deleting it.

## Implications

- Preserve existing memory content elsewhere before reshaping the directory.
- Future setup agents should adapt existing memory and documentation into OV-native categories.
- The directory should hold source material for OpenViking memory, resources, and skills, while generated OpenViking indexes and runtime state stay outside the repository.

## Related

- `.agents/memory/SCHEMA.md`
- `.agents/memory/ADAPTATION.md`
- `.agents/openviking/legacy-memory/1777901050/`
