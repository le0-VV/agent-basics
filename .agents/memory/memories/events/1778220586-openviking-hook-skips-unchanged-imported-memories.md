---
record_kind: memory
ov_category: events
title: OpenViking hook skips unchanged imported memories
status: active
created: 1778220586
updated: 1778220586
tags: [openviking, hooks, setup, polish]
summary: Fixed the fast ingest path so pre-commit hooks do not re-verify or re-ingest unchanged historical memory targets.
source_paths: []
requires_human_review: false
---

# OpenViking hook skips unchanged imported memories

Project: agent-basics

## Summary

Fixed the fast ingest path so pre-commit hooks do not re-verify or re-ingest unchanged historical memory targets.

## Content

On this polish pass, agent-basics fixed a pre-commit blocker where agent-basics ov ingest-changed called the full import path and re-verified every historical memory target, causing the hook to wait on old records such as LM Studio bootstrap notes. The fast ingest-changed path now trusts matching import-state entries and skips unchanged files without target stat/write verification, while import-repo-memory keeps full target verification for explicit repair/import runs. Verification passed with ./agent-basics verify after the change.
