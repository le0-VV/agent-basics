---
record_kind: memory
ov_category: cases
title: Runtime cache and repo path hardening audit
status: active
created: 1778278673
updated: 1778278673
tags: [testing, security, runtime, openviking]
summary: 
source_paths: []
requires_human_review: false
---

# Runtime cache and repo path hardening audit

Project: agent-basics

## Content

A rigorous verification pass found and fixed two issue classes in agent-basics: Rust runtime wrappers trusted a .complete cache marker without confirming the bundled runtime payload still existed and was executable, and repo-local OpenViking operations could follow symlinked .agents/openviking or .agents/memory paths outside the repository. The fix requires complete executable payload checks in both wrappers, exact repo-scoped memory URI prefix matching, and repo-local path validation before reading or writing OV configs, import state, memory source files, and hook lock files. Regression coverage now includes marker-only and non-executable runtime caches, malicious memory URI prefix smuggling, symlinked memory category escapes, symlinked repo OpenViking config leaks/writes, and symlinked lock directory escapes. Final ./agent-basics verify passed with 150 Python tests, 6 Rust tests, setup shell syntax, Homebrew formula syntax, OpenViking offline status, and licensing notices.
