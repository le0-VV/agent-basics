---
record_kind: memory
ov_category: tools
title: agent-basics-mlx local snapshot and worker thread rules
status: active
created: 1778124668
updated: 1778124668
tags: [mlx, huggingface, worker-thread, startup]
summary: MLX service boot should avoid remote HF resolution and keep all MLX work on one worker thread.
source_paths: []
requires_human_review: false
---

# agent-basics-mlx local snapshot and worker thread rules

Project: agent-basics

## Summary

MLX service boot should avoid remote HF resolution and keep all MLX work on one worker thread.

## Content

The packaged agent-basics-mlx service must resolve cached Hugging Face models to local snapshot paths before calling mlx_vlm.load or mlx_embeddings.load; otherwise snapshot_download may try network during LaunchAgent boot even when models are already cached. The server should also route all MLX model load, generation, embedding, and cache clearing through one dedicated runtime thread. Loading in startup thread and generating in the route thread can trigger MLX errors such as 'There is no Stream(gpu, 0) in current thread.' Disable generation padding for single prompt requests to avoid Gemma tokenizer padding to the large context window during startup checks.
