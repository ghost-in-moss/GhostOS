# Scripts

`GhostOS` 自带了部分命令行工具:

```bash
$ ghostos help

Commands:
  clear-runtime  clear workspace runtime files
  config         config the ghostos in streamlit web app
  console        turn a python file or module into a console agent
  docs           See GhostOS Docs
  help           Print this help message.
  init           init ghostos workspace
  web            turn a python file or module into a streamlit web agent
```

简单介绍几个命令:

`ghostos config` : 使用 streamlit 界面修改配置项.

`ghostos init` : 初始化 workspace 到当前目录.

`ghostos web` : 基于 python 文件或者模块, 启动一个 streamlit 实现的 agent 对话界面.

`ghostos console` : 用命令行启动 agent, 主要用来 debug.

## Developing Scripts

更多的命令行工具还在开发中. 预期有以下几个:

`ghostos main` : 启动 ghostos 的官方 agent, 用来介绍 ghostos 的一切.

`ghostos meta` : 使用 meta agent 编辑一个 python 文件, 可以实现 [MossAgent](/zh-cn/usages/moss_agent.md)

`ghostos edit` : 使用 edit agent 编辑任何一个文件, 结合上下文, 可以修改文件内容.

`ghostos script` : 运行各种基于 LLM 实现的自动化脚本, 可以不断增加相关脚本到本地.  