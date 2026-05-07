---
record_kind: memory
ov_category: events
title: First release local MLX requires Apple Silicon 16GB
status: active
created: 1778128274
updated: 1778128274
tags: [mlx, release, hardware]
summary: For the first release, bundled local MLX support requires an Apple Silicon Mac with at least 16 GB unified memory.
source_paths: []
requires_human_review: false
---

# First release local MLX requires Apple Silicon 16GB

Project: agent-basics

## Summary

For the first release, bundled local MLX support requires an Apple Silicon Mac with at least 16 GB unified memory.

## Content

The user decided that agent-basics first-release bundled local MLX runtime support should require users to have an Apple Silicon Mac with at least 16 GB unified memory. Unsupported hosts should not get a half-installed local MLX server; direct MLX bootstrap should fail clearly, while best-effort install flows may skip runtime bootstrap and direct users to configure a custom OpenAI-compatible provider.
