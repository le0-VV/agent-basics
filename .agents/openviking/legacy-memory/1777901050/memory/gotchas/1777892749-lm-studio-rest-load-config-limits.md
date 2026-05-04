---
id: gotcha-1777892749-lm-studio-rest-load-config-limits
type: gotcha
title: LM Studio REST load config limits
status: active
created: 1777892749
updated: 1777892749
tags: [lm-studio, rest, gemma-4, model-loading]
summary: LM Studio 0.4.12 REST model loading accepts flattened supported fields and does not expose every GUI load setting.
---

# LM Studio REST load config limits

## Problem

`agent-basics lmstudio load` initially sent the older nested `load_config` payload to LM Studio 0.4.12 and received `Missing required field 'model'`, then `Unrecognized key(s) in object: 'identifier', 'load_config'`.

## Cause

The current LM Studio v1 REST load endpoint expects flattened load fields such as `model`, `context_length`, `eval_batch_size`, `flash_attention`, and `offload_kv_cache_to_gpu`. It does not expose every GUI or runtime setting agent-basics wants to recommend, including parallelism/concurrency, CPU thread pool, GPU ratio, or KV cache quantization.

## Workaround

Use `agent-basics lmstudio load` with the flattened REST payload only. Treat unsupported settings as recommendations that must be configured in LM Studio or by another runtime interface, not as REST-enforced settings. Do not call the `lms` CLI from Codex on this host.

## Related

- `scripts/agent_basics_ov.py`
- `.agents/memory/memory/gotchas/1777890776-avoid-lms-cli-from-codex.md`
