---
record_kind: memory
ov_category: cases
title: Setup managed-path hardening
status: active
created: 1778235958
updated: 1778235958
tags: [security, setup, install, symlink, path-traversal]
summary: 
source_paths: []
requires_human_review: false
---

# Setup managed-path hardening

Project: agent-basics

## Content

Security audit worker A found and patched setup/install attack surfaces in setup-macos.sh. Managed repo writes now reject symlink components and paths resolving outside the target repo before writing templates, backups, merge sessions, OpenViking config, compatibility files, or .gitignore. setup-macos.sh now prefers trusted macOS/Homebrew PATH entries ahead of caller PATH for core tools, and the macOS mktemp template was fixed to avoid literal XXXXXX.md collisions. Regression coverage lives in tests/test_security_setup_attacks.py and covers symlink clobbering, symlinked .agents/backups/merge-sessions, symlinked legacy instructions, symlinked .gitignore, hostile project names with shell metacharacters/newlines, and hostile PATH python3/git hijacking.
