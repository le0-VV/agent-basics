---
id: procedure-1777766400-local-huggingface-embedding-api
type: procedure
title: Run the compatibility repo-local HuggingFace embedding API
status: compatibility
created: 1777766400
updated: 1777827387
tags: [embeddings, huggingface, rag, compatibility]
summary: Start the generated local embedding API when the compatibility mini-RAG was configured with a HuggingFace model.
---

# Run the compatibility repo-local HuggingFace embedding API

## When To Use

Use this when the transitional `.agents/memory/rag/config.json` has embedding provider `huggingface-local`. OpenViking provider setup should use the OpenViking gateway when available.

## Steps

1. From the repository root, run `.agents/memory/rag/embedding-api/start.sh`.
2. Keep that process running while agents need semantic memory retrieval.
3. Use the configured base URL from `.agents/memory/rag/config.json`, usually `http://127.0.0.1:8765/v1`.

## Verification

Call `/health`, `/v1/models`, or `/v1/embeddings` on the local service.

## Related

- `.agents/memory/documentations/procedures/openviking-gateway.md`
- `.agents/memory/rag/config.json`
- `.agents/memory/rag/embedding-api/README.md`
