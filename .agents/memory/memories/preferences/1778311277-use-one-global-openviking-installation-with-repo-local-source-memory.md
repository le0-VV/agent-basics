---
record_kind: memory
ov_category: preferences
title: Use one global OpenViking installation with repo-local source memory
status: active
created: 1778311277
updated: 1778311277
tags: [openviking, architecture, memory-sync]
summary: agent-basics uses a single global OV runtime while repo-local source memory stays version-controlled and synchronized into repo-scoped global OV namespaces.
source_paths: []
requires_human_review: false
---

# Use one global OpenViking installation with repo-local source memory

Project: agent-basics

## Summary

agent-basics uses a single global OV runtime while repo-local source memory stays version-controlled and synchronized into repo-scoped global OV namespaces.

## Content

agent-basics should use one global OpenViking installation, service, config, workspace, queues, and vector indexes under ~/.openviking. Repositories keep reviewed source memory, resources, namespace metadata, hooks, locks, migration records, and import state under .agents/memory/ and .agents/openviking/. agent-basics keeps the global instance current by importing repo-local source files into repo-scoped OpenViking namespaces and by verifying imported global targets during online status checks.
