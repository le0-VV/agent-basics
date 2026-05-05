# Third-Party Notices

This project is distributed under the MIT license in `LICENSE`.

`agent-basics` does not vendor OpenViking, LM Studio, model weights, or Python package dependencies into this repository or into the Rust wrapper binary. The installer and helper commands can install or call those tools on the user's machine, so their separate terms still apply.

This notice is not legal advice. Before redistributing a packaged build, image, bundle, model cache, or modified OpenViking runtime, re-check the effective licenses for the exact artifacts being shipped.

## Direct Runtime Integrations

| Component | How agent-basics uses it | License / terms to respect |
| --- | --- | --- |
| OpenViking | Installed into a user-level virtualenv, normally `~/.openviking`, and called as an external CLI/server. It is not vendored into this repo. | OpenViking's main project is AGPL-3.0. The upstream repo also documents `ov_cli` under Apache-2.0. If you modify, redistribute, or network-host OpenViking, comply with OpenViking's upstream license terms. Source: <https://github.com/volcengine/OpenViking> |
| LM Studio | Optionally installed through the Homebrew cask and managed as a local service for OpenAI-compatible chat and embedding APIs. It is not bundled by agent-basics. | LM Studio is separately licensed by LM Studio. Users must comply with LM Studio's app and service terms. Source: <https://lmstudio.ai/> |
| Gemma chat model | The default local chat/VLM model id is `google/gemma-4-e2b`, usually downloaded by LM Studio or supplied by the user. Model weights are not bundled. | Gemma models are governed by Google's Gemma terms and any model-card terms for the exact artifact downloaded. Source: <https://ai.google.dev/gemma/terms> |
| EmbeddingGemma model | The default local embedding model id is `text-embedding-embeddinggemma-300m-qat`, usually downloaded by LM Studio or supplied by the user. Model weights are not bundled. | The downloaded embedding model is governed by its model-card terms and any applicable Google model terms. Check the exact LM Studio or Hugging Face artifact before redistribution. |
| uv | Required by the Homebrew formula and used to create virtualenvs and install Python packages. It is not vendored by agent-basics. | uv is distributed under MIT or Apache-2.0 terms. Source: <https://github.com/astral-sh/uv> |

## Optional Generated Embedding API

The legacy compatibility path can generate `.agents/memory/rag/embedding-api/` for a repo-local Hugging Face embedding server. That generated environment installs packages at setup time and should not be committed with its virtualenv or model cache.

Direct requirements written by setup:

- FastAPI: MIT license. Source: <https://github.com/fastapi/fastapi>
- sentence-transformers: Apache-2.0 license. Source: <https://github.com/UKPLab/sentence-transformers>
- Uvicorn: BSD-3-Clause license. Source: <https://github.com/encode/uvicorn>

Transitive Python packages are resolved by the user's package installer at setup time. If the generated virtualenv or a frozen package bundle is redistributed, include license notices for the resolved transitive dependency set.

## Project Compliance Rules

- Keep `Cargo.lock` free of third-party Rust dependencies unless their licenses are audited and added here.
- Do not vendor OpenViking source, LM Studio binaries, model weights, or generated virtualenvs into this repository.
- Do not describe OpenViking, LM Studio, Gemma, EmbeddingGemma, or optional Python packages as covered by the agent-basics MIT license.
- If a future release bundles third-party source or binaries, add the upstream license text or required notice before release.
