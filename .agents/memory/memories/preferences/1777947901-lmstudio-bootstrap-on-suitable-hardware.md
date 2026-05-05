---
record_kind: memory
ov_category: preferences
title: LM Studio bootstrap on suitable hardware
status: active
created: 1777947901
updated: 1777947901
tags: [install, lmstudio, openviking, local-models]
summary: agent-basics installs should bootstrap LM Studio on suitable Apple Silicon hosts and keep model loading JIT.
source_paths: []
requires_human_review: false
---

# LM Studio bootstrap on suitable hardware

Project: agent-basics

## Summary

agent-basics installs should bootstrap LM Studio on suitable Apple Silicon hosts and keep model loading JIT.

## Content

When host hardware is good enough for the local runtime, installing agent-basics should attempt to install LM Studio through Homebrew, install a user-level LaunchAgent for the LM Studio server, configure the chat and embedding model defaults, download the configured models, and verify that the downloaded models are visible through the OpenAI-compatible model list for JIT loading. Homebrew and setup should treat this path as best-effort so OpenViking and repo setup are not blocked by app, server, or model-download failures.
