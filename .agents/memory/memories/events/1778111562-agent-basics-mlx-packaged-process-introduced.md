---
record_kind: memory
ov_category: events
title: agent-basics-mlx packaged process introduced
status: active
created: 1778111562
updated: 1778111562
tags: []
summary: agent-basics now packages the MLX runtime server behind a first-class agent-basics-mlx process.
source_paths: []
requires_human_review: false
---

# agent-basics-mlx packaged process introduced

Project: agent-basics

## Summary

agent-basics now packages the MLX runtime server behind a first-class agent-basics-mlx process.

## Content

The user requested the MLX server be packaged as a proper process named agent-basics-mlx. Implementation adds a second Cargo binary named agent-basics-mlx, updates MLX bootstrap/write-server/service/server paths to install and run ~/.agent-basics/mlx/agent-basics-mlx, keeps Python source fallback compatibility for source checkout use, and updates LaunchAgent dry-run output so ProgramArguments starts with the agent-basics-mlx process instead of python plus agent-basics-mlx-server.py.
