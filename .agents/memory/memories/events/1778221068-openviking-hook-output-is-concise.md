---
record_kind: memory
ov_category: events
title: OpenViking hook output is concise
status: active
created: 1778221068
updated: 1778221068
tags: [openviking, hooks, polish, verification]
summary: Successful OpenViking hook output is now concise and fast hook ingest no longer dirties import-state for unchanged entries.
source_paths: []
requires_human_review: false
---

# OpenViking hook output is concise

Project: agent-basics

## Summary

Successful OpenViking hook output is now concise and fast hook ingest no longer dirties import-state for unchanged entries.

## Content

The OpenViking pre-commit hook now prints concise success output by default instead of dumping the full JSON ingest payload. Direct diagnostics can still request the full payload with agent-basics ov hook --json. The fast ingest path also preserves existing import-state entries when all matching files are skipped, so a successful hook does not leave .agents/openviking/import-state.json dirty just because unchanged historical entries were skipped. Verification passed with ./agent-basics verify.
