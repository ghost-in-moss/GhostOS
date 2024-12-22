# Chat

## Quick start

`GhostOS` use [Streamlit](https://streamlit.io/) to offer open-box Agent UI.

run:

```bash
ghostos web python_modulename_or_filename
```

can convert a python module or file into a streamlit Agent.

The system default testing Agent is:

```bash
# start chatbot
ghostos web ghostos.demo.agents.jojo
```

You can launch a standalone Python file as an Agent to interpret file content and call the file's relevant
methods. `GhostOS` will automatically reflect the code to generate the context visible to the Agent.

![streamlit_chat](assets/streamlit_chat.png)

## Realtime Chat

`GhostOS` Implements [OpenAI Realtime Beta](https://platform.openai.com/docs/api-reference/realtime).

To use it, you need to install the relevant libraries first:

```bash
pip install ghostos[realtime]
```

For configuration details of the real-time model, see [configuration](./configuration.md).

> There are still many bugs and experience issues with the current real-time model.
> After all, it is still a personal project, so...

## Runtime files

When you converse with an agent using `GhostOS`, the system generates various runtime files, such as:

* thread: stores historical messages.
* task: stores the state of the conversation state machine.
* images and audio: images and audio from the process.
* logs: runtime logs.

All these runtime files are saved in
the [\[workspace\]/runtime](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/app/runtime) directory.

If you need to clear them, please run:

```bash
ghostos clear-runtime
```

## Create Your Agent

see [Usage](/en/usages/moss_agent.md)