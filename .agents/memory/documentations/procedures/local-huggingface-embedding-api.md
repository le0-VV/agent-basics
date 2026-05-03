---
id: procedure-1777766400-local-huggingface-embedding-api
type: procedure
title: Run the repo-local HuggingFace embedding API
status: active
created: 1777766400
updated: 1777766400
tags: [embeddings, huggingface, rag]
summary: Start the generated local embedding API when agent-basics was configured with a HuggingFace model.
---

# Run the repo-local HuggingFace embedding API

## When To Use

Use this when `.agents/memory/rag/config.json` has embedding provider `huggingface-local`.

## Steps

1. From the repository root, run `.agents/memory/rag/embedding-api/start.sh`.
2. Keep that process running while agents need semantic memory retrieval.
3. Use the configured base URL from `.agents/memory/rag/config.json`, usually `http://127.0.0.1:8765/v1`.

## Verification

Call `/health`, `/v1/models`, or `/v1/embeddings` on the local service.

## Related

- `.agents/memory/rag/config.json`
- `.agents/memory/rag/embedding-api/README.md`
