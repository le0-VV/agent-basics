---
record_kind: memory
ov_category: preferences
title: Use repo-local OpenViking workspaces
status: active
created: 1778156831
updated: 1778156831
tags: [openviking, architecture, repo-local]
summary: agent-basics should share the OpenViking executable/runtime system-wide but keep each repo's OpenViking config, workspace, database, index, queues, locks, import state, and source store under .agents/.
source_paths: []
requires_human_review: false
---

# Use repo-local OpenViking workspaces

Project: agent-basics

## Summary

agent-basics should share the OpenViking executable/runtime system-wide but keep each repo's OpenViking config, workspace, database, index, queues, locks, import state, and source store under .agents/.

## Content

Project direction changed on 1778130000-era roadmap work: agent-basics should not use a hidden global ~/.openviking/workspace as the normal data plane. The target architecture is a shared system-wide OpenViking executable/Python environment plus repo-local .agents/openviking/config.toml, namespaces.toml, workspace, database, vector index, queue state, locks, import state, and .agents/memory source files. Repo-local workspace contents are generated cache/build artifacts and should be ignored by git, while selected config/manifests/source files are committed. The MCP server remains system-wide and directory-agnostic by accepting or inferring repo_path, then invoking the shared OV executable with that repo's local config/workspace.
