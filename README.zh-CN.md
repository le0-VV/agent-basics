# agent-basics

[English](README.md)

coding agent 新手村套装。

`agent-basics` 用来把一个仓库设置成适合 coding agents 长 session、交接和持续更新的稳定工作区。

它使用 OpenViking 作为记忆和检索后端。`agent-basics` 负责仓库侧的事情：说明文件、setup、upgrade、MCP 接线、git hooks、run state，以及安全的 markdown 冲突处理。

> 这会增加一些 prompt 和流程开销。换来的是更好的连续性，以及更少丢失的决策。

## 它提供什么

- 一个 agents 能可靠发现的根目录 `Agents.md`。
- 一个仓库本地 `.agents/` 工作区，用于 agent instructions、run state、skills 和 OpenViking metadata。
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

使用中文输出和仓库默认语言：

```bash
agent-basics setup --language zh-CN /path/to/project
```

重新运行 setup 就是 upgrade 路径：

```bash
agent-basics upgrade /path/to/project
```

如果 setup 发现已有 markdown 文件，例如 `Agents.md`，它会询问是保留、替换、追加、手动合并、使用本地 web merge UI，还是把新文件保存到原文件旁边。

## OpenViking

OpenViking 是必需的。如果还没安装，用下面的命令安装并配置：

```bash
agent-basics ov install-system
agent-basics ov write-default-config --force
agent-basics ov doctor
```

当需要 live search、ingest 或 MCP calls 时，启动 OpenViking server：

```bash
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

把 MCP client 配成从仓库根目录运行 `agent-basics mcp`。

示例：

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

Codex Desktop：

- Name: `agent-basics`
- Transport: `STDIO`
- Command: `agent-basics`
- Arguments: `mcp`
- Working directory: 仓库根目录的绝对路径

## 日常使用

开始或检查长任务：

```bash
agent-basics run start --task "ship the feature"
agent-basics run status
agent-basics run checkpoint --message "what changed"
agent-basics run handoff --message "handoff notes"
agent-basics run finish --message "done"
```

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
    ├── runs/
    ├── merge-sessions/
    └── backups/
```

关键文件：

- `Agents.md`：agents 应该优先读取的根目录说明。
- `.agents/AGENT-BASICS.md`：agent-basics 工作流的操作说明。
- `.agents/memory/`：repo-owned memory 和 resource files，由 OpenViking ingest。
- `.agents/openviking/`：repo metadata、import state、locks 和 migration records。
- `.agents/skills/` 和 `Skills.md`：给 agents 使用的可复用工作流。
- `.agents/runs/`：本地 long-horizon run state 和 handoff files。
- `.agents/TODO.md`：当前工作 checklist；被 git 忽略。

## LM Studio

默认本地设置期望 LM Studio 暴露 OpenAI-compatible API，供 chat/VLM model 和 embedding model 使用。在 macOS 上，agents 应该通过 `agent-basics lmstudio` 的 HTTP 命令操作，而不是使用 `lms` CLI。

```bash
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
