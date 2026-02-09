# agent-basics

1 command to setup a directory for reliable agent workflows

> **THIS SETUP WILL INCREASE TOKEN USAGE IN EXCHANGE FOR MORE RELIABLE AGENT OPERATIONS**

## How it works

The command will check for the existence for, and if they're not present, add the following files:

```
.
├── .agents
│   ├── DOCUMENTATIONS.md
│   ├── INSTRUCTIONS.md
│   ├── MEMORY.md
│   └── TODO.md
├── .gitignore
└── Agents.md
```

And then check if the folder is a git repo. If not, then set it up as one.

## The files

- ### Agents.md

    Basic instructions telling the agent to follow further instructions and how to use the files under `.agents`

- ### INSTRUCTIONS.MD

    A slightly modified version of the [custom instruction made by u/Shir_man](https://www.reddit.com/r/ChatGPT/comments/1fv59m7/im_stupid_and_spent_200_to_mmlubenchmark_my/). Mostly just spelling and markdown layout amendments.

    This set of instructions is originally designed for ChatGPT assistants. It yields measurably more accurate responses across topics, helps reinforce the agent to respond in a more predictable manner, and helps alleviate the "GPT-ish" response tone.

    However, the reliability of this set of instructions will start falling off as a conversation gets longer and the context gets compacted. The effects mostly exhibits in how the agent starts responding not in strict accordance to the answering format. The quality of the response may or may not change.

- ### DOCUMENTATIONS.MD

    A place for agents to record URLs of documentations for the project. This combined with the instruction help reinforce the agent to write more standard-compliant code

- ### TODO.md

    The instructions will tell agents to use this TODO to record and stick to their work plan. This helps agents to work more coherently, write better structured code, and is especially effective in helping agent stays on track when it had to compact context mid-work. This is untracked by git by design to avoid triggering git too frequently andd bloating the git files as it will change very frequently.

- ### MEMORY.md

    Anything that needs to be remembered but doesn't go into documentations or todo (like project work preferences, test methods etc) goes in here. Helps with cross-agent consistency and can get new agent sessions up to speed faster.
