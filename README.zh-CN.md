# agent-basics

[English](README.md)

coding agent 新手村套装。

`agent-basics` 用来把一个仓库设置成适合 coding agents 稳定读取说明、记忆和项目上下文的工作区。

它使用 OpenViking 作为记忆和检索后端。`agent-basics` 负责仓库侧的事情：说明文件、setup、upgrade、MCP 接线、git hooks，以及安全的 markdown 冲突处理。

> 这会增加一些 prompt 和流程开销。换来的是更好的连续性，以及更少丢失的决策。

## 问题是什么

Coding agents 很有用，但它们不擅长把项目上下文稳定带过长会话、新聊天、分支切换和多个 agents 的交接。重要决策很容易散落在聊天记录、TODO、临时笔记和半记得的 instructions 里。每个新 agent 又得重新搞清楚项目怎么工作、哪些文件重要、用户偏好是什么、什么方案已经踩过坑。

大多数仓库也没有给 agents 一个稳定的操作界面。Instructions 可能缺失、重复、过期，或者藏在 agent 不一定会读的文件里。就算有 memory system，也常常和 git 分离，导致项目知识和对应代码慢慢漂开。

## 核心想法

`agent-basics` 是一个轻量 repo harness：安装一个共享的 memory backend，把稳定的 agent-facing 文件放在可预测的位置，再教 agents 几个固定流程。

仓库把可人工 review 的 source files 放在 `.agents/memory/`；OpenViking 负责存储、搜索和检索；MCP 给 agents 一个一致的方式来读取上下文和记录新上下文。Setup 和 upgrade 负责安全地处理已有项目，git hooks 则在提交知识文件变化时刷新 memory backend。

## 它提供什么

- 一个 agents 能可靠发现的根目录 `Agents.md`。
- 一个仓库本地 `.agents/` 工作区，用于 agent instructions、skills、memory source files 和 OpenViking metadata。
- 一个用户级 OpenViking 安装，通常在 `~/.openviking`，可被多个项目共享。
- 仓库感知的 MCP tools，让 agents 通过 OpenViking 搜索和记录项目上下文。
- 当 repo memory files 变化时刷新 OpenViking 的 git hooks。
- 更安全的新项目 setup 和旧项目 upgrade 流程，包括 markdown merge prompts。
- 一个 supervised commit helper，用配置好的 coding-agent author 提交。

## 安装

```bash
brew tap le0-VV/agent-basics https://github.com/le0-VV/agent-basics.git
brew install --HEAD le0-VV/agent-basics/agent-basics
```

Homebrew 安装时会自动 bootstrap 共享的 OpenViking 到 `~/.openviking`，缺少默认配置时会写入配置，并尝试安装 macOS LaunchAgent。在合适的 Apple Silicon 机器上，它也会 best-effort 设置 LM Studio：安装 `lm-studio` cask、安装用户级 LM Studio server LaunchAgent、写入模型默认配置、下载配置好的 chat/embedding 模型，并让模型以 JIT 方式按需加载。

验证命令：

```bash
agent-basics --version
agent-basics doctor --online
```

## 设置仓库

对新项目或已有项目运行：

```bash
agent-basics setup /path/to/project
```

把整个 agent-basics 安装的语言设成简体中文：

```bash
agent-basics setup --language zh-CN /path/to/project
```

语言偏好保存在 `~/.agent-basics/config.toml`，不写进每个仓库。

重新运行 setup 就是 upgrade 路径：

```bash
agent-basics upgrade /path/to/project
```

如果 setup 发现已有 markdown 文件，例如 `Agents.md`，它会询问是保留、替换、追加、手动合并、使用本地 web merge UI，还是把新文件保存到原文件旁边。

## OpenViking

OpenViking 是必需的，并且会在 Homebrew 安装时自动 bootstrap。需要修复或重新运行完整本地 runtime setup 时：

```bash
agent-basics ov bootstrap-system
agent-basics lmstudio bootstrap
agent-basics ov doctor
```

在 macOS 上，bootstrap 会把 OpenViking 装成用户级 LaunchAgent，让 live search、ingest 和 MCP calls 共用同一个常驻 server。Foreground server mode 主要用来 debug：

```bash
agent-basics ov service status
agent-basics ov service restart
agent-basics ov server
```

常用命令：

```bash
agent-basics ov status
agent-basics ov import-repo-memory --write
agent-basics ov search "what did we decide about memory?"
agent-basics ov record
agent-basics ov add-resource ./docs/api.md
agent-basics ov add-skill .agents/skills/finish-work.md
agent-basics ov ingest-changed
agent-basics ov install-hooks
```

## MCP 设置

把 MCP client 配成运行 `agent-basics mcp`。不要把 server 绑定到某个项目目录；agents 在每次 tool call 里用 `cwd` 传当前工作目录。

示例：

```json
{
  "mcpServers": {
    "agent-basics": {
      "command": "agent-basics",
      "args": ["mcp"]
    }
  }
}
```

Codex Desktop：

- Name: `agent-basics`
- Transport: `STDIO`
- Command: `agent-basics`
- Arguments: `mcp`
- Working directory: 留空/默认
- Tool calls: 用 `cwd` 传仓库根目录，或仓库内任意目录

## 日常使用

验证和提交：

```bash
agent-basics verify
agent-basics commit "feat(scope): description"
```

commit helper 不会自己 stage 文件。先 stage 需要提交的文件，再运行 commit。

## 仓库结构

setup 之后，一个项目通常会有：

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
    ├── memory/
    ├── skills/
    ├── merge-sessions/
    └── backups/
```

关键文件：

- `Agents.md`：agents 应该优先读取的根目录说明。
- `.agents/AGENT-BASICS.md`：agent-basics 工作流的操作说明。
- `.agents/memory/`：repo-owned memory 和 resource files，由 OpenViking ingest。
- `.agents/openviking/`：repo metadata、import state、locks 和 migration records。
- `.agents/skills/` 和 `Skills.md`：给 agents 使用的可复用工作流。
- `.agents/TODO.md`：当前工作 checklist；被 git 忽略。

## LM Studio

默认本地设置期望 LM Studio 暴露 OpenAI-compatible API，供 chat/VLM model 和 embedding model 使用。agents 应该通过 `agent-basics lmstudio` 的 HTTP 命令管理模型；bootstrap 可以安装一个在 agent 进程之外运行 `lms server start` 的 LaunchAgent。

```bash
agent-basics lmstudio bootstrap --dry-run
agent-basics lmstudio service status
agent-basics lmstudio status
agent-basics lmstudio hardware
agent-basics lmstudio plan
agent-basics lmstudio configure --write
agent-basics lmstudio load --dry-run
agent-basics lmstudio route-test
```

## 更多细节

- [ROADMAP.md](ROADMAP.md)：项目方向和仍待确定的设计问题。
- [Agents.md](Agents.md)：本仓库的根目录 agent instructions。
- [.agents/AGENT-BASICS.md](.agents/AGENT-BASICS.md)：agent-basics 操作细节。
