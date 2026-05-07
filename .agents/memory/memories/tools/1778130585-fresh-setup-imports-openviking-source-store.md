---
record_kind: memory
ov_category: tools
title: Fresh setup imports OpenViking source store
status: active
created: 1778130585
updated: 1778130585
tags: [setup, openviking, fresh-repo]
summary: Fresh setup now waits for OpenViking health and imports generated base source-store resources.
source_paths: []
requires_human_review: false
---

# Fresh setup imports OpenViking source store

Project: agent-basics

## Summary

Fresh setup now waits for OpenViking health and imports generated base source-store resources.

## Content

As of 1778130545, setup-macos.sh waits for the user-level OpenViking service to become healthy before initial repo import, then runs agent-basics ov import-repo-memory --write after all generated markdown files are normalized. A successful fresh setup should create .agents/openviking/import-state.json with stale_count 0 for .agents/memory/ADAPTATION.md, INDEX.md, and SCHEMA.md. agent-basics verify now selects Python 3.11+ for unit tests so Apple/Xcode Python 3.9 does not fail on tomllib.
