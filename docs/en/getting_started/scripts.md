# Scripts

`GhostOS` has some cli tools:

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

Brief introductions to the commands:

`ghostos config`: This command utilizes a Streamlit interface to modify configuration settings.

`ghostos init`: Initializes a workspace in the current directory.

`ghostos web`: Launches an agent conversation interface implemented with Streamlit, based on a Python file or module.

`ghostos console`: Starts the agent in the command line, primarily used for debugging purposes.

## Developing Scripts

Here are descriptions of the additional command-line tools under development:

`ghostos main`: Launches the official GhostOS agent, which serves as an introduction to everything about GhostOS.

`ghostos meta`: Utilizes a meta agent to edit a Python file, enabling the implementation
of [MossAgent](/en/usages/moss_agent.md).

`ghostos edit`: Employs an edit agent to edit any file, leveraging context to modify file contents.

`ghostos script`: Executes various automation scripts based on Large Language Models (LLMs), with the capability to
continuously add related scripts to the local environment.