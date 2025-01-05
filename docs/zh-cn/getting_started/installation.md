# Installation

> `GhostOS` 仍然是一个验证中的 AI 项目, 强烈建议安装到 docker 之类的容器中, 而不在本地执行.

## PIP install

```bash
pip install ghostos
```

初始化 `workspace` (默认 `app`), 当前版本的运行时文件都会存入目录.

```bash
ghostos init
```

配置大模型. 默认使用 OpenAI `gpt-4o`, 要求环境变量存在 `OPENAI_API_KEY`.
或者运行 `streamlit` 编辑界面:

```bash
ghostos config
```

测试运行自带的 agent:

```bash
# run an agent with python filename or modulename
ghostos web ghostos.demo.agents.jojo
```

或者将本地的 Python 文件变成一个 Agent, 可以通过自然语言对话要求它调用文件中的函数或方法:

```bash
ghostos web [my_path_file_path]
```

## Install Realtime

安装 realtime 所需的依赖: 

```bash
pip install 'ghostos[realtime]'
```

## Workspace

`GhostOS` 当前版本使用本地文件来存运行时数据. 所以需要初始化一个 workspace.

运行 `ghostos init` 可以用脚本复制 workspace 到当前目录.

`GhostOS` 在运行中产生的数据会存放到这个目录下. 当需要清除历史数据时, 请执行:

```bash
ghostos clear-runtime
```

## Env

`GhostOS` 依赖各种模型的 `access token`, 默认是从环境变量中读取.
定义这些环境变量有两种方法:

- export 环境变量到命令行中. 
- 使用 `.env` 文件 (自动通过 `dotenv` 读取)

```bash

copy [workspace]/.example.env [workspace]/.env
vim [workspace]/.env
```

配置项详见 [.example.env](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/app/.example.env)