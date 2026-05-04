# OpenViking Memory Adaptation Guide

Use this guide when converting existing project memory, documentation notes, agent instructions, or compatibility mini-RAG files into the `.agents/memory/` OpenViking source-store shape.

## Goal

The goal is not to preserve the old folder taxonomy. The goal is to preserve useful project knowledge as OpenViking-ready source material with clear provenance and one independently updatable idea per file.

## Required Steps

1. Inventory existing files before changing them.
2. Copy original material into `.agents/memory/imports/<unix-timestamp>-<source>/` or `.agents/openviking/legacy-memory/<unix-timestamp>/`.
3. Decide whether each item is `memory`, `resource`, `skill`, or `ignore`.
4. For memory records, choose one OpenViking category: `profile`, `preferences`, `entities`, `events`, `cases`, `patterns`, `tools`, or `skills`.
5. Split mixed records. Do not combine a user preference, project fact, tool gotcha, and dated event in one file.
6. Preserve `source_paths` and important related links.
7. Mark stale, transitional, or conflicting records with `requires_human_review: true`.
8. Ingest only reviewed or clearly safe records through `agent-basics ov ...` or the OpenViking-backed MCP gateway.
9. Run `ov wait` or the equivalent `agent-basics ov` command after ingest.
10. Verify representative queries with OpenViking retrieval before deleting, demoting, or ignoring legacy material.

## Mapping Rules

- Legacy `preference` records usually become `record_kind: memory` and `ov_category: preferences`.
- Stable facts about projects, tools, repositories, or configuration usually become `entities`.
- Decisions and dated milestones usually become `events`.
- Gotchas, crashes, caveats, and workaround records usually become `cases`.
- Procedures usually become `patterns`, unless they are packaged as reusable OpenViking skills.
- Documentation source records and URL-only files become `record_kind: resource` and `ov_category: none`.
- Reusable agent workflows can become `record_kind: skill` and may also have an associated `skills` memory record summarizing when to use them.
- Compatibility-only instructions for retired tooling should be preserved as `ignore` or marked `requires_human_review: true`.

## Front Matter

Use this shape for adapted memory records:

```yaml
---
id: ov-memory-UNIXTIMESTAMP-short-name
record_kind: memory
ov_category: preferences
title: Short title
status: active
created: UNIX_TIMESTAMP
updated: UNIX_TIMESTAMP
tags: []
summary: One sentence summary.
source_paths: []
requires_human_review: false
---
```

Use `record_kind: resource` and `ov_category: none` for documentation resources. Use `record_kind: skill` for reusable workflows intended for OpenViking skill registration.

## Quality Bar

- Keep one idea per file.
- Prefer concrete, searchable wording over broad summaries.
- Do not store raw secrets.
- Do not erase user-specific preferences during cleanup.
- Do not treat stale compatibility machinery as active project direction.
- Record uncertainty explicitly instead of guessing.
