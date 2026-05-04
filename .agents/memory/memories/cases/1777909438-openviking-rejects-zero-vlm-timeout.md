---
id: ov-memory-1777909438-openviking-rejects-zero-vlm-timeout
record_kind: memory
ov_category: cases
title: OpenViking rejects zero VLM timeout
status: active
created: 1777909438
updated: 1777909438
tags: [openviking, config, timeout, lmstudio]
summary: OpenViking server startup fails when `vlm.timeout` is `0`; use a large positive timeout for local LLM runs instead.
source_paths: []
requires_human_review: false
---

# OpenViking rejects zero VLM timeout

## Problem

Starting `openviking-server` with `vlm.timeout: 0` in `~/.openviking/ov.conf` fails with `Invalid value for 'vlm.timeout': Input should be greater than 0`.

## Workaround

Use a large positive timeout such as `86400` seconds for local LM Studio runs. This preserves the practical "do not time out quickly on local hardware" behavior while satisfying OpenViking config validation.

