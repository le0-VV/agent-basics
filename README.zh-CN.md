# agent-basics

[English](README.md)

coding agent 新手村套装。

`agent-basics` 用来把一个仓库设置成适合 coding agents 稳定读取说明、记忆和项目上下文的工作区。

> **`agent-basics` 会增加不少的 context 开销，换来更可靠的长线工作。**

## 痛点

Agents 做长线工作很容易掉链子，本质上还是 context 限制。Context window 越大、经历的 compact 越多，agent 越容易不听话、忘事情。用户之前做的决定、代码库里的坑、某个必须按顺序执行的流程，这些东西都会随着项目拖长而丢失，除非仓库里有一套明确的护栏，也就是 harness。

搭护栏本身又很麻烦。从我自己用、也和其他用户聊下来的感觉看，很多人还在找一套可靠、系统化的 agentic programming 护栏。Markdown 文件能解决一部分问题，但项目一大，记录 memory 和项目细节的 markdown 很容易膨胀，agent 读起来费劲，也很吃 context。

这个项目就是想尽量把这件事变简单一点。

一个不需要 OpenViking，也就是不额外依赖 LLM 和 embedding model API 的方案，也在计划中。

## 核心想法

`agent-basics` 是一个基础 repo harness：安装一个共享的记忆后端，把稳定的 agent-facing 文件放在可预测的位置，再教 agents 几个固定流程。

仓库把可人工审核的源文件放在 `.agents/memory/`；OpenViking 负责存储、搜索和检索；MCP 给 agents 一个一致的方式来读取上下文和记录新上下文。Setup 和 upgrade 负责安全地处理已有项目，git hooks 则在提交知识文件变化时刷新 memory backend。

## 它怎么工作

它使用 OpenViking 作为记忆和检索后端，而 OpenViking 本身需要通过 API 访问一个 LLM 和一个 embedding 模型，用来生成结构化记忆和做语义检索。`agent-basics` 负责仓库侧的 instructions、setup、upgrade、MCP 接线、git hooks，以及安全的 markdown 冲突处理。它也会管理一个用户级 OpenViking 安装；如果设备条件允许，还会通过 Homebrew 安装设置 LM Studio，用作本地 LLM 和 embedding model API。

## 它提供什么

- 一个 agents 能可靠发现的根目录 `Agents.md`。
- 一个仓库本地 `.agents/` 工作区，用于 agent instructions、skills、memory source files 和 OpenViking metadata。
- 一个用户级 OpenViking 安装，通常在 `~/.openviking`，可被多个项目共享。
- 仓库感知的 MCP tools，让 agents 通过 OpenViking 搜索和记录项目上下文。
- 当 repo memory files 变化时刷新 OpenViking 的 git hooks。
- 更安全的新项目 setup 和旧项目 upgrade 流程，包括 markdown merge prompts。
- 一个 supervised git commit helper，用配置好的 coding-agent author 提交。

## 安装

```bash
brew tap le0-VV/agent-basics https://github.com/le0-VV/agent-basics.git
brew install --HEAD le0-VV/agent-basics/agent-basics
```

Homebrew 安装时会自动 bootstrap 共享的 OpenViking 到 `~/.openviking`，缺少默认配置时会写入配置，并尝试安装 macOS LaunchAgent。在合适的 Apple Silicon 设备上，它也会尝试设置 LM Studio：安装 `lm-studio` Homebrew cask、安装用户级 LM Studio server LaunchAgent、写入模型默认配置、下载配置好的 chat/embedding 模型，并让模型以 JIT 方式按需加载。

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

重新运行 setup 就是 upgrade 路径：

```bash
agent-basics upgrade /path/to/project
```

如果 setup 发现已有 markdown 文件，例如 `Agents.md`，它会询问是保留、替换、追加、手动合并、使用本地 web merge UI，还是把新文件保存到原文件旁。

## OpenViking

OpenViking 目前是必需的，并且会在 Homebrew 安装时自动 bootstrap。需要修复或重新运行完整本地 runtime setup 时：

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

## 需要帮助的话

可以 clone 这个 repo，然后问你的 agent 应该怎么把它用起来。

## 👉👈

如果 agent-basics 有帮到你，或者你刚好想支持一下，欢迎请我喝杯奶茶。哪怕1分钱对我来说也是莫大的鼓励。

<img src="assets/support/alipay.jpg" alt="支付宝收款码" width="180">

还有 bro 现在真的没有收入 💀。你的投喂会养活我的两只毛孩子：Jessie 和 Yolo <3

完全自愿。不影响 license、issue 优先级、feature 优先级，也不代表任何 support SLA。

### Jessie 和 Yolo

| Jessie 第一天                                                                | Jessie                                                        | 还是 Jessie                                                        |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------ |
| <img src="assets/cats/jessie-first-day.jpg" alt="Jessie 第一天" width="220"> | <img src="assets/cats/jessie-1.jpg" alt="Jessie" width="220"> | <img src="assets/cats/jessie-2.jpg" alt="还是 Jessie" width="220"> |

| 小小 Yolo                                                         | Yolo                                                      | 还是 Yolo                                                      | Jessie 和 Yolo                                                                      |
| ----------------------------------------------------------------- | --------------------------------------------------------- | -------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| <img src="assets/cats/smol-yolo.jpg" alt="小小 Yolo" width="180"> | <img src="assets/cats/yolo-1.jpg" alt="Yolo" width="180"> | <img src="assets/cats/yolo-2.jpg" alt="还是 Yolo" width="180"> | <img src="assets/cats/yolo-and-jessie.jpg" alt="Jessie 和 Yolo 在一起" width="240"> |

## 更多细节

- [ROADMAP.md](ROADMAP.md)：项目方向和仍待确定的设计问题。
- [Agents.md](Agents.md)：本仓库的根目录 agent instructions。
- [.agents/AGENT-BASICS.md](.agents/AGENT-BASICS.md)：agent-basics 操作细节。
