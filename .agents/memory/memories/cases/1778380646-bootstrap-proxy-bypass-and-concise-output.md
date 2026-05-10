---
record_kind: memory
ov_category: cases
title: Bootstrap proxy bypass and concise output
status: active
created: 1778380646
updated: 1778380646
tags: []
summary: 
source_paths: []
requires_human_review: false
---

# Bootstrap proxy bypass and concise output

Project: agent-basics

## Content

Bootstrap and runtime health checks for localhost/loopback URLs must bypass HTTP proxy environment variables because users may run Privoxy or another proxy locally. The bootstrap commands now print concise human status by default; use --json only when full diagnostic payloads are needed.
