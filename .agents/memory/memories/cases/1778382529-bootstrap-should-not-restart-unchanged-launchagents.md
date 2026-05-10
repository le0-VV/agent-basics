---
record_kind: memory
ov_category: cases
title: Bootstrap should not restart unchanged LaunchAgents
status: active
created: 1778382529
updated: 1778382529
tags: []
summary: 
source_paths: []
requires_human_review: false
---

# Bootstrap should not restart unchanged LaunchAgents

Project: agent-basics

## Content

The bootstrap failure with curl unable to connect to 127.0.0.1:18080 was caused by service install treating unchanged running LaunchAgents as restart operations via launchctl kickstart -k. That killed the MLX runtime, then the 15s wait expired before the M1 preload startup completed. Service install should skip restart when launchctl print reports state = running; explicit restart remains the operation that kills/reloads. MLX wait defaults should allow real preload startup time.
