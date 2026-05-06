---
record_kind: memory
ov_category: preferences
title: Prefer lightweight command wrapper over mandatory Rust binary build
status: active
created: 1778045839
updated: 1778045839
tags: [packaging, distribution, rust]
summary: agent-basics should not require users to download Rust, LLVM, or a full native build toolchain just to install the command. Prefer a shell/Python wrapper for near-term distribution; keep Rust binary packaging as optional future work only if prebuilt artifacts or maintainer-only builds avoid end-user install friction.
source_paths: []
requires_human_review: false
---

# Prefer lightweight command wrapper over mandatory Rust binary build

Project: agent-basics

## Summary

agent-basics should not require users to download Rust, LLVM, or a full native build toolchain just to install the command. Prefer a shell/Python wrapper for near-term distribution; keep Rust binary packaging as optional future work only if prebuilt artifacts or maintainer-only builds avoid end-user install friction.

## Content

The user prefers not to make Rust binary packaging mandatory for agent-basics because installing or building it can require downloading Rust, LLVM, and a large native toolchain. Near-term distribution should use a lightweight shell/Python command wrapper when sufficient. Rust can remain a future packaging option only if it avoids end-user build-toolchain friction, such as through prebuilt artifacts.
