---
record_kind: memory
ov_category: cases
title: agent-basics-mlx service process and memory accounting
status: active
created: 1778124643
updated: 1778124643
tags: [mlx, service, memory-accounting]
summary: agent-basics-mlx shows a PyInstaller parent/child pair and RSS can underreport loaded MLX model memory.
source_paths: []
requires_human_review: false
---

# agent-basics-mlx service process and memory accounting

Project: agent-basics

## Summary

agent-basics-mlx shows a PyInstaller parent/child pair and RSS can underreport loaded MLX model memory.

## Content

After LaunchAgent startup, two agent-basics-mlx processes are expected for the packaged onefile runtime: the parent has PPID 1 and tiny RSS, and the child has the server. Activity Monitor/RSS can still look low because MLX model memory is mostly resident under IOAccelerator graphics regions. Verify real load with /health loaded.chat and loaded.embedding, plus vmmap -summary on the child. On 1778124300, health showed both models loaded and vmmap reported a 4.1G physical footprint with 3.5G in IOAccelerator graphics.
