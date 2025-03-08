# GhostOS

> The AI `Ghosts` wonder in the `Shells`.

* [Documents](https://ghost-in-moss.github.io/GhostOS/#/)
* [Discord Server](https://discord.gg/NG6VKwd5jV)
* [Releases](RELEASES.md)

(This document is translated from zh-cn to english by [Moonshot](https://moonshot.cn/))

## Example

Using Python code [SpheroBoltGPT](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/demo/sphero/bolt_gpt.py),
an intelligent robot with a [SpheroBolt](https://sphero.com/products/sphero-bolt) as its body is defined.
If you have a SpheroBolt, running `ghostos web ghostos.demo.sphero.bolt_gpt` can start this robot.

![SpheroBoltGPT](https://github.com/ghost-in-moss/GhostOS/tree/main/docsassets/ask_sphero_spin_gif.gif)

The demo initially implements the following features:

1. Real-time voice conversation.
2. Control of body movements and drawing graphics on an 8x8 LED matrix.
3. Learning skills that include actions and animations through natural language dialogue.
4. Expressing emotions through movements during conversation.

## Introduce

`GhostOS` is an AI Agent framework designed to replace `JSON Schema `
with a Turing-complete code interaction
interface ([Moss Protocol](https://github.com/ghost-in-moss/GhostOS/tree/main/docszh-cn/concepts/moss_protocol.md)),
becoming the core method for interaction between LLM and Agent system capabilities. For more details:
[MOSS: Enabling Code-Driven Evolution and Context Management for AI Agents](https://arxiv.org/abs/2409.16120)

The expected objects called through code
include `tools`, `personality`, `agent swarm`, `workflows`, `thinking`, `planning`, `knowledge`, and `memory`.
This allows a Meta-Agent to become an intelligent entity capable of continuous learning and growth through code
generation and project management.

And such an intelligent agent implemented with a code repository can also be shared and installed in the form of a
repository.

`GhostOS` Still in the early experimental developing, the current version mainly implements out-of-the-box capabilities,
including:

- [x] Turn a python file into a web agent
- [x] Agent web UI built by [Streamlit Web](https://streamlit.io/)
- [x] Support llms like `OpenAI`, `Moonshot`
- [x] Support [OpenAI vision](https://platform.openai.com/docs/guides/vision)
- [x] Support [OpenAI Realtime Beta](https://platform.openai.com/docs/guides/realtime)

## Quick Start

> `GhostOS` remains a beta AI project, strongly recommending installation in containers such as Docker rather than
> running locally.

Install `GhostOS` package:

```bash
pip install ghostos
```

Initialize `workspace` (directory `app` as default), The runtime files of the current version will be stored in the
directory.

```bash
ghostos init
```

Configure the model. Default to use OpenAI `gpt-4o`, requiring the environment variable `OPENAI_API_KEY`.

```bash
export OPENAI_API_KEY="your openai api key"
# Optionals: 
export OPENAI_PROXY="sock5://localhost:[your-port]" # setup openai proxy
export DEEPSEEK_API_KEY="your deepseek api key"
epoxrt MOONSHOT_API_KEY="your moonshot api key"
```

Or you can use configuration ui by streamlit:

```bash
ghostos config
```

Then test the default agent:

```bash
# run an agent with python filename or modulename
ghostos web ghostos.demo.agents.jojo
```

Or turn a local Python file into an Agent,
that can be instructed to call functions or methods within the file through natural language conversations.

```bash
ghostos web [my_path_file_path]
```

some demo agents

```bash
ghostos web ghostos.demo.agents.jojo
ghostos web ghostos.demo.test_agents.moonshot         # moonshot-v1-32k model
ghostos web ghostos.demo.test_agents.deepseek_chat    # deepseek chat model
ghostos web ghostos.demo.test_agents.openai_o1_mini   # openai o1 mini model
```

You can create a local Python file and define your own Agents. For more details

* [Chatbot](https://github.com/ghost-in-moss/GhostOS/tree/main/docszh-cn/usages/chatbot.md): simplest chatbot
* [MossAgent](https://github.com/ghost-in-moss/GhostOS/tree/main/docszh-cn/usages/moss_agent.md): an agent that can
  interact with the python module

## Install Realtime

`GhostOS` support [OpenAI Realtime](https://platform.openai.com/docs/guides/realtime),
using [pyaudio](https://pypi.org/project/PyAudio/) to handle realtime audio i/o.
Need to install the dependencies first:

```bash
pip install 'ghostos[realtime]'
```

> You may face some difficulties while install pyaudio on your device,
> I'm sure gpt-4o, google or stackoverflow will offer you solutions.

## Use In Python

```python
from ghostos.bootstrap import make_app_container, get_ghostos
from ghostos.ghosts.chatbot import Chatbot

# create your own root ioc container.
# register or replace the dependencies by IoC service providers.
container = make_app_container(...)

# fetch the GhostOS instance.
ghostos = get_ghostos(container)

# Create a shell instance, which managing sessions that keep AI Ghost inside it.
# and initialize the shell level dependency providers.
shell = ghostos.create_matrix("your robot shell")
# Shell can handle parallel ghosts running, and communicate them through an EventBus.
# So the Multi-Agent swarm in GhostOS is asynchronous.
shell.background_run()  # Optional

# need an instance implements `ghostos.abcd.Ghost` interface.
my_chatbot: Chatbot = ...

# use Shell to create a synchronous conversation channel with the Ghost.
conversation = shell.sync(my_chatbot)

# use the conversation channel to talk
event, receiver = conversation.talk("hello?")
with receiver:
  for chunk in receiver.recv():
    print(chunk.content)
```

## Developing Features

* [ ] Out-of-the-box Agent capability libraries.
* [ ] Variable type messaging and Streamlit rendering.
* [ ] Asynchronous Multi-Agent.
* [ ] Long-term task planning and execution.
* [ ] Atomic thinking capabilities.
* [ ] Automated execution and management of tree-based projects.
* [ ] Configurable components of the framework.
* [ ] Experiments with toy-level embodied intelligence.

> GhostOS, as a personal project, currently lacks the energy to focus on improving documentation, storage modules,
> stability, or security issues.
>
> The project's iteration will be centered on validating three directions for a long time:
> code-driven embodied intelligence, code-based thinking capabilities, and code-based learning.
> I will also aim to optimize out-of-the-box agent abilities.

# So What is GhostOS purpose?

The GhostOS project is developed by the author for exploring AI applications. The basic idea is as follows:

AI Agent technology has two parallel evolutionary paths:
one is the perfection of the model's own capabilities, and the other is the evolution of the Agent engineering
framework.
The productivity level of the Agent framework determines the feasibility of AI models in practical application
scenarios.

GhostOS reflects the capabilities of an Agent from code into prompts, providing them to AI models,
and the code generated by the models runs directly in the environment.
Expecting the large language model do everything through a Turing-complete programming language interface,
including computation, tool invocation, body control, personality switching, thinking paradigms, state scheduling,
Multi-Agent, memory and recall, and other actions.

This will have stronger interaction capabilities and lower overhead than methods based on JSON schema.
The conversation data generated in this process can be used for post-training or reinforcement learning of the model,
thereby continuously optimizing the code generation.

The AI Agent itself is also defined by code.
Therefore, a Meta-Agent can develop other Agents just like a normal programming task.

Ideally, the Meta-Agent can write code, write its own tools, define memories and chain of thoughts with data structures,
and develop other Agents for itself.

![meta-agent-cycle](https://github.com/ghost-in-moss/GhostOS/tree/main/docsassets/meta-agent-cycle.png)

Furthermore, most complex tasks with rigorous steps can be described using tree or graph data structures.
Constructing a nested graph or tree using methods like JSON is very difficult,
while using programming languages is the most efficient.

models can consolidate the results learned from conversations into nodes in the code,
and then plan them into trees or graphs, thereby executing sufficiently complex tasks.

In this way, an AI Agent can store the knowledge and capabilities learned from natural language in the form of files and
code,
thereby evolving itself. This is a path of evolution beyond model iteration.

Based on this idea,
GhostOS aims to turn an Agent swarm into a project constructed through code.
The Agents continuously precipitate new knowledge and capabilities in the form of code, enriching the project.
The Agent project can be copied, shared, or deployed in the form of repositories,

In this new form of productivity, interacting purely through code is the most critical step.

The author's ultimate goal is not `GhostOS` itself,
but to verify and promote the code interaction design and applications.
The hope is that one day, agents, paradigms, bodies, and tools for AI Agents can all be designed based on the same
programming language protocols,
achieving cross-project universality.

