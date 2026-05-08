---
record_kind: memory
ov_category: events
title: Setup service failure output polish
status: active
created: 1778218094
updated: 1778218094
tags: [setup, openviking, homebrew, polish]
summary: Fresh setup now suppresses internal OpenViking JSON and reports service write failures without tracebacks.
source_paths: []
requires_human_review: false
---

# Setup service failure output polish

Project: agent-basics

## Summary

Fresh setup now suppresses internal OpenViking JSON and reports service write failures without tracebacks.

## Content

On 1778218094, agent-basics setup was polished for real-world testing: OpenViking service install now catches OSError/PermissionError and returns structured JSON, setup captures internal OpenViking hook/package/service command output, prints concise failure summaries, avoids duplicate service warnings, and initializes new git repos with main when supported to avoid default-branch hint noise. This keeps Homebrew/setup smoke runs readable while preserving manual repair commands.
