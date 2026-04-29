# agent-basics

1 command to setup a directory for reliable agent workflows

> **THIS SETUP WILL INCREASE TOKEN USAGE IN EXCHANGE FOR MORE RELIABLE AGENT OPERATIONS**

`agent-basics` depends on [OpenViking](https://github.com/volcengine/OpenViking). If OpenViking is not installed and configured, setup stops instead of falling back to markdown memory files.

## How it works

The command will check for the existence for, and if they're not present, add the following files:

```
.
├── .agents
│   ├── INSTRUCTIONS.md
│   ├── TODO.md
│   └── openviking
│       ├── README.md
│       ├── backups
│       ├── data
│       │   └── viking
│       ├── exports
│       ├── merge-sessions
│       ├── models
│       │   └── bge-small-zh-v1.5-q4_k_m.gguf
│       └── setup-state
├── .gitignore
└── Agents.md
```

Setup installs OpenViking into `.agents/openviking/venv`, copies the repo-local GGUF embedding model into `.agents/openviking/models`, uses `llama.cpp` to serve the model through a local OpenAI-compatible embedding shim, initializes project-local OpenViking configuration under `.agents/openviking` when needed, runs `openviking-server doctor`, verifies a real local embedding call, migrates legacy `.agents/DOCUMENTATIONS.md` and `.agents/MEMORY.md` content into OpenViking when those files exist, and then checks if the folder is a git repo. If not, then it sets it up as one.

OpenViking commands for a project should run with:

```bash
export PATH="$PWD/.agents/openviking/venv/bin:$PATH"
export OPENVIKING_CONFIG_FILE="$PWD/.agents/openviking/ov.conf"
export OPENVIKING_CLI_CONFIG_FILE="$PWD/.agents/openviking/ovcli.conf"
```

The default embedding model is `bge-small-zh-v1.5-q4_k_m.gguf`, a 512-dimensional local GGUF model stored under `.agents/openviking/models`. On macOS, setup uses Homebrew `llama.cpp`; the embedding shim first tries Metal through `llama-embedding` and falls back to `--device none` when Metal is unavailable.

The script writes `Agents.md` and `.agents/INSTRUCTIONS.md` from embedded templates. When an existing markdown file differs from the template, it prompts per file to keep the existing file, replace it after creating a backup, append the template after creating a backup, manually merge both versions in `$EDITOR`, or save the incoming template beside the existing file as `*.agent-basics.new`.
For `.gitignore`, the script is non-interactive: it appends `.agents/TODO.md` only when missing; if present, it does nothing.

## Install via custom Homebrew tap

```bash
brew tap le0-VV/agent-basics
brew install --HEAD le0-VV/agent-basics/agent-basics
```

### Upgrade

```bash
brew update
brew upgrade agent-basics
```

## The files

- ### Agents.md

    Basic instructions telling the agent to follow further instructions and how to use the files under `.agents`

- ### INSTRUCTIONS.MD

    A slightly modified version of the [custom instruction made by u/Shir_man](https://www.reddit.com/r/ChatGPT/comments/1fv59m7/im_stupid_and_spent_200_to_mmlubenchmark_my/). Mostly just spelling and markdown layout amendments.

    This set of instructions is originally designed for ChatGPT assistants. It yields measurably more accurate responses across topics, helps reinforce the agent to respond in a more predictable manner, and helps alleviate the "GPT-ish" response tone.

    However, the reliability of this set of instructions will start falling off as a conversation gets longer and the context gets compacted. The effects mostly exhibits in how the agent starts responding not in strict accordance to the answering format. The quality of the response may or may not change.

- ### DOCUMENTATIONS.MD

    Removed from the agent-basics structure. Agents should store documentation source URLs in OpenViking under `viking://resources/`.

- ### TODO.md

    The instructions will tell agents to use this TODO to record and stick to their work plan. This helps agents to work more coherently, write better structured code, and is especially effective in helping agent stays on track when it had to compact context mid-work. This is untracked by git by design to avoid triggering git too frequently bloating the git files as it will change very frequently.

- ### MEMORY.md

    Removed from the agent-basics structure. Agents should store user memories under `viking://user/memories/` and agent-learned memories under `viking://agent/memories/`.
