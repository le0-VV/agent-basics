# agent-basics

[English](README.md)

用一个命令把仓库设置成更可靠的 agent 编程工作区。

> **这套设置会增加 token 使用量，换取更可靠的 agent 操作。**

`agent-basics` 是一个仓库本地的编程 harness。它的方向是让一个用户级 OpenViking 安装成为必需的记忆、文档、资源、技能、语义组织和检索后端，而 `agent-basics` 负责这个后端周围的仓库契约。

`.agents/memory/` 是仓库拥有的 OpenViking source store。旧版 agent-basics mini-RAG 内容会作为迁移输入保存在 `.agents/openviking/legacy-memory/` 下；fallback mini-RAG 源码放在 `compat/memory-rag/` 下，只在显式兼容安装时使用。

## 方向

`agent-basics` 应该提供一个稳定命令：

```bash
agent-basics setup /path/to/project
agent-basics upgrade /path/to/project
agent-basics doctor --online
agent-basics mcp
agent-basics ov doctor
agent-basics ov install-system
agent-basics ov write-default-config --force
agent-basics ov server
agent-basics ov import-repo-memory --write
agent-basics ov search "what did we decide about memory?"
agent-basics ov record
agent-basics ov add-resource ./docs/api.md
agent-basics ov add-skill .agents/skills/finish-work.md
agent-basics ov ingest-changed
agent-basics ov install-hooks
agent-basics lmstudio status
agent-basics lmstudio hardware
agent-basics lmstudio plan
agent-basics lmstudio configure --write
agent-basics lmstudio load --dry-run
agent-basics lmstudio route-test
agent-basics migrate memory-to-openviking --write
agent-basics run start --task "ship the feature"
agent-basics run status
agent-basics run checkpoint --message "what changed"
agent-basics run handoff --message "handoff notes"
agent-basics run finish --message "done"
agent-basics verify
agent-basics commit "feat(scope): description"
```

目标职责：

- `agent-basics` 安装、验证、配置并包装用户级 OpenViking 安装，通常位于 `~/.openviking`。
- `agent-basics` 写入并安全升级根目录 `Agents.md`、`.agents/AGENT-BASICS.md`、`.agents/config.toml`、`.agents/openviking/`、`.agents/skills/` 和 `.agents/runs/`。
- `agent-basics mcp` 暴露仓库感知的 OpenViking 工具，用于搜索、记录、资源 ingest、技能 ingest、变更文件 ingest 和健康检查。
- OpenViking 负责持久记忆、文档资源、语义摘要、embedding 索引、向量搜索和上下文组织。
- 根目录 `Agents.md` 仍然是 agent 入口。
- `.agents/AGENT-BASICS.md` 仍然是 agent-basics 操作手册。
- `Skills.md` 和 `.agents/skills/` 提供可复用的 agent 工作流，并指向稳定的命令前缀。
- `ROADMAP.md` 记录长期项目方向。
- `.agents/TODO.md` 记录当前跨 session 工作状态。

## 当前兼容命令

这些兼容命令保留给旧仓库或显式 fallback 安装：

```bash
agent-basics setup /path/to/project
agent-basics upgrade /path/to/project
agent-basics memory validate
agent-basics memory rebuild
agent-basics memory search "what did we decide about memory?"
agent-basics memory doctor --online
```

`setup` 和 `upgrade` 执行同一个安全设置流程。在已有仓库中重新运行 setup，是升级旧版 agent-basics layout 的受支持路径：遇到重叠 markdown 文件时，会提示选择保留、替换、追加、手动合并、web 合并或另存到旁边。

全新 setup 现在会把 `.agents/memory/` 创建为 OpenViking source store，而不是默认安装旧版 mini-RAG layout。如果已有旧版 `.agents/memory/{templates,memory,documentations,rag}` 树，setup 会在 `.agents/openviking/legacy-memory/<unix-timestamp>/` 下保留 source snapshot，让 agents 可以把有用内容适配成 OV-native records。旧版兼容 mini-RAG 仍可通过 `AGENT_BASICS_INSTALL_COMPAT_MEMORY=1` 显式安装，用作 fallback。

## 目标仓库结构

```text
.
├── Agents.md
├── ROADMAP.md
├── Skills.md
└── .agents/
    ├── AGENT-BASICS.md
    ├── TODO.md
    ├── config.toml
    ├── openviking/
    │   ├── repo.json
    │   ├── migration-manifest.json
    │   ├── legacy-memory/
    │   └── locks/
    ├── memory/
    │   ├── SCHEMA.md
    │   ├── INDEX.md
    │   ├── ADAPTATION.md
    │   ├── memories/
    │   ├── resources/
    │   ├── skills/
    │   └── imports/
    ├── skills/
    │   ├── prework.md
    │   ├── memory-update.md
    │   └── finish-work.md
    ├── runs/
    │   └── <run-id>/
    │       ├── state.json
    │       ├── CHECKPOINT.md
    │       └── handoff.md
    ├── merge-sessions/
    └── backups/
```

迁移期间，或在使用 `AGENT_BASICS_INSTALL_COMPAT_MEMORY=1` 时，目标仓库中仍可能存在旧版兼容 mini-RAG layout：

```text
.agents/memory/
  templates/
  memory/
  documentations/
  rag/
    agent-memory.py
    memory-mcp.py
    config.json
    index.sqlite
    manifest.json
```

在重塑这个仓库之前，现有兼容 source tree 已复制到 `.agents/openviking/legacy-memory/1777901050/`。未来 setup agents 应该把已有项目记忆保存在 `.agents/memory/imports/<timestamp>-<source>/` 或 `.agents/openviking/legacy-memory/<timestamp>/`，然后适配进 OV-native 的 `memories/`、`resources/` 和 `skills/` records。setup 不应该删除 `.agents/memory/`；这个目录是 OpenViking ingest 的仓库专属 source store。

这个开发 checkout 把兼容实现放在 `compat/memory-rag/`，而不是放进活动的 `.agents/memory/` source store。

## OpenViking Gateway

gateway 让普通 agent 工作流不用关心 OpenViking executable 细节：

- `agent-basics ov doctor`：验证用户级 OpenViking 安装、仓库配置、provider 健康状态和 ingest 状态。
- `agent-basics ov install-system`：当 OpenViking 缺失时安装到 `~/.openviking`。
- `agent-basics ov write-default-config`：为 LM Studio Gemma 4 E2B 加 EmbeddingGemma 写入默认 `~/.openviking/ov.conf` 和 `~/.openviking/ovcli.conf`。
- `agent-basics ov server`：以前台方式启动配置好的用户级 OpenViking HTTP server。
- `agent-basics ov import-repo-memory`：把 `.agents/memory/` 下的 OV-native memories 写入 OpenViking memory categories，并 ingest resources/skills。
- `agent-basics ov search <query>`：搜索 memory、docs、resources 和 skills。
- `agent-basics ov record`：把持久上下文记录到正确的 OpenViking category。
- `agent-basics ov add-resource <path-or-url>`：ingest 项目文档或外部来源。
- `agent-basics ov add-skill <path>`：注册可复用 agent workflows。
- `agent-basics ov ingest-changed`：相关文件变化后更新 OpenViking。
- `agent-basics ov status`：报告仓库专属 OpenViking 状态。

支持 MCP 的 agents 应该使用 repo-aware MCP server，而不是直接调用原始 OpenViking：

```json
{
  "mcpServers": {
    "agent-basics": {
      "command": "agent-basics",
      "args": ["mcp"],
      "cwd": "/path/to/project"
    }
  }
}
```

Codex Desktop 自定义 MCP 设置：

- Name: `agent-basics`
- Transport: `STDIO`
- Command to launch: `agent-basics`
- Arguments: `mcp`
- Environment variables: 只填写 provider secret variables，变量名由 agent-basics/OpenViking config 指定
- Environment variable passthrough: 同样只在需要时透传 provider secret variables
- Working directory: 仓库根目录的绝对路径

## 设置与迁移

目标 setup 流程应该：

1. 检测项目根目录和 git 状态。
2. 检测现有 `Agents.md`、`.agents/AGENT-BASICS.md`、旧版 `.agents/INSTRUCTIONS.md`、`.agents/memory/` 和现有 OpenViking 状态。
3. 检查 OpenViking 是否已安装。
4. 安装 OpenViking；如果不允许安装，则停止并给出明确说明。
5. 在 `.agents/openviking/` 下配置仓库本地 OpenViking metadata。
6. 配置 LLM/VLM 和 embedding providers。
7. 用 doctor check 验证 providers。
8. 写入或安全合并根目录 `Agents.md`。
9. 写入或安全合并 `.agents/AGENT-BASICS.md`。
10. 写入 `.agents/config.toml`。
11. 创建 `.agents/TODO.md`、`.agents/skills/`、`.agents/runs/`、`.agents/backups/` 和 `.agents/merge-sessions/`。
12. 在可行时配置 `agent-basics mcp`。
13. 安装 git hooks。
14. 把初始项目说明和选定文档 ingest 到 OpenViking。
15. 报告最终路径、健康状态和下一步 agent actions。

当前 setup script 会安全处理 markdown 冲突。当已有 markdown 文件与 agent-basics template 不同时，它会逐个文件提示：保留、带备份替换、带备份追加、在 `$EDITOR` 中手动合并、使用本地 web merge UI，或把 incoming template 保存到旁边的 `*.agent-basics.new`。web merge 路径会在 `.agents/merge-sessions/<unix-timestamp>-<file>/` 下创建 unresolved session，包含 `existing.md`、`proposed.md`、`final.md`、`session.json` 和 bundled merge UI 的副本。如果浏览器启动被禁用或不可用，setup 会打印准确 session 路径，并保持现有文件不变。

全新 setup 也会写入 `Skills.md`、`.agents/skills/prework.md`、`.agents/skills/memory-update.md`、`.agents/skills/finish-work.md` 和 `.agents/runs/`。run instances 是本地状态，会被 git 忽略；`.agents/TODO.md` 仍然是人类可读的跨 session checklist。

如果存在旧版 `.agents/DOCUMENTATIONS.md`、`.agents/MEMORY.md` 或更早 agent-basics memory trees，setup 应该先保存原始材料，再做适配。Agents 应该遵循 `.agents/memory/ADAPTATION.md`：盘点、复制、分类为 memory/resource/skill/ignore、拆分混合 records、保留 `source_paths`、把不确定 records 标记为需要人工 review、通过 OpenViking ingest，然后验证检索。

## 兼容 Embedding 设置

兼容 mini-RAG setup 需要一个 embedding 配置，并且不再属于默认 setup 路径。只有需要旧版 fallback memory CLI/MCP 时才使用它：

使用现有 OpenAI-compatible embeddings API：

```bash
AGENT_BASICS_INSTALL_COMPAT_MEMORY=1 agent-basics setup /path/to/project \
  --embedding-mode api \
  --embedding-base-url http://127.0.0.1:1234/v1 \
  --embedding-model text-embedding-embeddinggemma-300m-qat
```

Setup 会验证这些值，并把持久 mini-RAG runtime settings 写入 `.agents/memory/rag/config.json`。`runtime.embedding_timeout_seconds: 0` 表示无限等待本地 embedding API 响应。如果你希望 setup 和 RAG commands 更快失败，可以用 `--embedding-timeout` 设置一个正秒数。

如果 embedding provider 需要 secret，把 secret 留在 shell 里，只传变量名：

```bash
export MY_EMBEDDING_API_KEY="..."
AGENT_BASICS_INSTALL_COMPAT_MEMORY=1 agent-basics setup /path/to/project \
  --embedding-mode api \
  --embedding-base-url https://embedding.example/v1 \
  --embedding-model my-embedding-model \
  --embedding-api-key-env MY_EMBEDDING_API_KEY
```

Environment variables 仍可作为 setup 输入、secret pointers 和一次性 overrides，但它们不是持久项目配置。

也可以提供 HuggingFace model id 或 URL。Setup 会安装 repo-local Python virtualenv、拉取模型、验证它能产生有限向量，并在 `.agents/memory/rag/embedding-api/` 下写入一个小型 OpenAI-compatible API。

```bash
AGENT_BASICS_INSTALL_COMPAT_MEMORY=1 agent-basics setup /path/to/project \
  --embedding-mode huggingface \
  --embedding-hf-model Qwen/Qwen3-Embedding-0.6B
```

启动生成的本地 API：

```bash
.agents/memory/rag/embedding-api/start.sh
```

## 通过自定义 Homebrew Tap 安装

```bash
brew tap le0-VV/agent-basics
brew install --HEAD le0-VV/agent-basics/agent-basics
```

这会构建并安装一个 binary：

- `agent-basics setup [DIR]`：设置或升级仓库，包括带有重叠 markdown 文件的旧版 agent-basics layouts。
- `agent-basics ov doctor`：检查用户级 OpenViking 安装和配置。
- `agent-basics ov install-system`：把 OpenViking 安装到 `~/.openviking`。
- `agent-basics ov write-default-config`：写入默认 LM Studio-backed OpenViking runtime config 和 OV CLI HTTP config。
- `agent-basics ov server`：使用配置好的用户级 `ov.conf` 运行 `openviking-server`，agents 不需要知道 executable path。
- `agent-basics ov import-repo-memory`：把 repo-owned OpenViking source store import 进用户级 OpenViking database。OV-native memory files 会直接写到 `viking://user/default/memories/<category>/projects/<repo>/`；它们不会再绕回 `ov add-memory`。如果 OpenViking 报告 memory tree busy，该命令会在失败前重试 memory writes。
- `agent-basics ov search|read|record|add-resource|add-skill|ingest-changed|install-hooks|status`：默认 scoped 到当前仓库的 repo-aware OpenViking operations。
- `agent-basics ov install-hooks`：安装 managed hooks，在 OpenViking source-store 变化时刷新 OpenViking，并在 `.agents/runs/current` 损坏、完成或 stale 时阻止 pre-commit。用 `.agents/config.toml` 中的 `[run].stale_after_seconds` 配置 stale threshold；`AGENT_BASICS_RUN_HOOK_SKIP=1` 只应用于紧急绕过。
- `agent-basics lmstudio status|hardware|plan|configure|load|unload|route-test`：只通过 persisted model defaults 和 REST/OpenAI-compatible HTTP 检查并管理 LM Studio。
- `agent-basics migrate memory-to-openviking`：把旧版 `.agents/memory/` records inventory 到 OV-native categories。
- `agent-basics run start|status|checkpoint|handoff|finish`：在 `.agents/runs/` 下创建并维护 repo-local long-horizon run state。
- `agent-basics verify`：运行仓库标准本地 validation checks。
- `agent-basics commit "type(scope): description"`：用 supervised coding-agent author 提交 staged changes。
- `agent-basics memory ...`：对当前工作仓库运行兼容 memory/RAG operations。
- `agent-basics mcp`：为当前工作仓库运行 OpenViking-backed stdio MCP server。

升级：

```bash
brew update
brew upgrade agent-basics
```

## 关键文件

- `Agents.md`：项目根目录 agent entrypoint。保持这个文件位于仓库根目录，让 agents 能可靠发现它。
- `.agents/AGENT-BASICS.md`：OpenViking-backed harness 方向和当前兼容层的 agent-basics 操作手册。
- `ROADMAP.md`：长期架构、milestones 和 non-goals。
- `.agents/TODO.md`：当前 agent work plan 和跨 session 状态。它按设计不进入 git。
- `.agents/config.toml`：目标持久 repo config。
- `.agents/openviking/`：目标 repo-local OpenViking metadata、migration manifests 和 locks。除非用户明确选择另一个用户级路径，否则 OpenViking install 和 workspace 保持在 `~/.openviking` 下。
- `.agents/skills/` 或 `Skills.md`：目标重复工作流，指向稳定的 `agent-basics` commands。
- `.agents/runs/`：目标 long-horizon run state 和 handoff files。
- `.agents/memory/`：repo-owned OpenViking source store，用于 memory、resources、skills、imports 和 adaptation instructions。
- `.agents/openviking/legacy-memory/`：保存下来的旧版 memory snapshots，用作迁移输入。

## LM Studio 安全

在 macOS 上，`agent-basics` 不应该从 Codex 或其他 sandboxed agent hosts 使用 `lms` CLI。在这台机器上，`lms` 会启动 LM Studio Electron app，并在 AppKit registration 期间崩溃。安全路径是：

1. 用户启动 LM Studio 和它的本地 server。
2. Agents 调用 `agent-basics lmstudio status` 验证 HTTP 可达。
3. Agents 调用 `agent-basics lmstudio plan` 检查建议的 E2B load settings。
4. Agents 调用 `agent-basics lmstudio configure --write` 为 Gemma 4 E2B 和 EmbeddingGemma 写入带备份的 LM Studio defaults。
5. 只有当希望通过 REST load model 时，agents 才调用 `agent-basics lmstudio load`。

默认本地模型计划是 Gemma 4 E2B，使用 max context、max GPU offload、concurrency 1、KV cache quantization `q4_0`、启用 flash attention，并在 routing tests 中使用 temperature 0。

`agent-basics lmstudio configure` 默认是 dry-run。加上 `--write` 时，它会更新 LM Studio 已观察到的 persisted defaults，路径在 `~/.lmstudio/.internal/user-concrete-model-default-config/`，保留无关字段，并在原文件旁边备份变更文件。它会清理 stale persisted routing system-prompt 和 structured-output defaults，因为它们可能与 OpenViking 自己的 request-time grammar 冲突。Routing tests 仍会在每个 request 中显式发送 system prompt 和 `response_format`。

`agent-basics ov server` 会在启动 OpenViking 前为 `127.0.0.1`、`localhost` 和 `::1` 设置 `NO_PROXY`/`no_proxy`，避免本地 LM Studio requests 被系统 HTTP proxies 接管。
