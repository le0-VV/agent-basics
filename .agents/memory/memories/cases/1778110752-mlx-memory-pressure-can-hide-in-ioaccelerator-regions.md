---
record_kind: memory
ov_category: cases
title: MLX memory pressure can hide in IOAccelerator regions
status: active
created: 1778110752
updated: 1778110752
tags: []
summary: macOS memory pressure can rise from MLX/Metal allocations even when normal Python RSS does not appear to change.
source_paths: []
requires_human_review: false
---

# MLX memory pressure can hide in IOAccelerator regions

Project: agent-basics

## Summary

macOS memory pressure can rise from MLX/Metal allocations even when normal Python RSS does not appear to change.

## Content

During the live OpenViking demo, the user noticed a sharp memory-pressure change after checking MLX status while the Python process view did not obviously change. Investigation showed that agent-basics mlx status only calls /health and /v1/models and should not trigger model loading or inference. vmmap -summary for the MLX server process showed a 4.2 GB physical footprint with about 3.5 GB resident in IOAccelerator (graphics), while ordinary process views can under-report or present this differently. For MLX memory diagnostics, use top MEM or vmmap physical footprint/IOAccelerator regions, not only ps RSS or Activity Monitor's ordinary Python process column.
