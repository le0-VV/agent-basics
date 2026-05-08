---
record_kind: memory
ov_category: events
title: First-run polish before real-world test
status: active
created: 1778219958
updated: 1778219958
tags: [setup, openviking, polish, verification]
summary: Polished public CLI help, MCP help, setup repair commands, README language guidance, and verify output before real-world testing.
source_paths: []
requires_human_review: false
---

# First-run polish before real-world test

Project: agent-basics

## Summary

Polished public CLI help, MCP help, setup repair commands, README language guidance, and verify output before real-world testing.

## Content

On this polish pass, agent-basics hid legacy compatibility memory commands and setup embedding flags from the primary CLI help, added human-readable agent-basics mcp --help guidance, aligned English and Chinese README language setup guidance with installation-wide language configuration, removed outdated README wording about a non-OpenViking first-release path, changed setup repair messages to show stable agent-basics commands instead of temporary extracted runtime paths, and changed agent-basics verify to summarize OpenViking status instead of dumping full JSON state. Verification passed with ./agent-basics verify and fresh setup smoke showed clean service-failure output with stable repair commands.
