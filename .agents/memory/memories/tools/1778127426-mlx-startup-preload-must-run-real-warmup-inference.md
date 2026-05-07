---
record_kind: memory
ov_category: tools
title: MLX startup preload must run real warmup inference
status: active
created: 1778127426
updated: 1778127426
tags: [mlx, preload, warmup]
summary: agent-basics-mlx preload must complete minimal chat and embedding compute, not only model object load.
source_paths: []
requires_human_review: false
---

# MLX startup preload must run real warmup inference

Project: agent-basics

## Summary

agent-basics-mlx preload must complete minimal chat and embedding compute, not only model object load.

## Content

The user observed that MLX memory only rose to the expected footprint after an OpenViking request, proving that load-only startup telemetry was too weak. agent-basics-mlx startup preload should run a minimal real chat generation and a minimal embedding request, then expose chat_warmed and embedding_warmed in health. Treat loaded=true as object residency only; warmed=true is the signal that the runtime has faulted weights through compute. On 1778127266, the patched service completed warmup in about 48 seconds and vmmap later showed a 4.8G physical footprint with 3.5G in IOAccelerator graphics.
