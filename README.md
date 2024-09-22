# GhostOS framework

<div align="center">
  <img src="./assets/logo.png" alt="Logo" width="200">
  <h1 align="center">GhostOS framework</h1>
</div>


<div align="center">
  <a href="https://discord.gg/NG6VKwd5jV">Join our Discord community</a>
  <a href="https://discord.gg/NG6VKwd5jV"><img src="https://img.shields.io/badge/Discord-Join%20Us-purple?logo=discord&logoColor=white&style=for-the-badge" alt="Join our Discord community"></a>
</div>


## Introduce

`GhostOS` is an LLM-driven Agent framework.
It offers a MOSS (LLM-oriented Operating System Simulation) interface to LLM, which does:

1. Coding is Prompt Engineering: reflects python module's codes to prompt, let the LLM knows its python context. 
2. Injects agent runtime libraries (such as multiple task scheduler) to the python context by IoC Container.
3. Maintain persist python processing context during multiple turns of LLM thinking
4. Execute the LLM generated codes to use tools, call domain agents, operate mindflow and almost everything.

`GhostOS` provides the LLM Agents a Turing-complete python interface.
And Agents are able to write python code to produce tools (as libraries) and integrate them (import modules or dependency injections) itself;
Furthermore, the Agent is built from code, and can be called as function by other Agents.

So the meta-agents are enabled to define or optimize other domain agents, and integrate them during processing (theoretically).
By these methods we are aiming to develop the Self-Evolving Meta-Agent.

Article link: ...

## Quick Start

So far the `GhostOS` is still in the early stages of experimentation and exploration.
We are planning to release the first version at October.
You are welcome to play with the demo testcases:

### Prepare

First make sure you've installed python > 3.12, then:

clone repository:

```bash
# clone the repository
git clone https://github.com/ghost-in-moss/GhostOS.git ghostos_test
# go to the directory
cd ghostos_test
# create python venv
python -m venv venv
# activate venv
source venv/bin/activate
```

after activate the python venv, then install dependencies by poetry:

```bash
# install poetry in the venv
python -m pip install poetry
# install requirements by poetry
poetry install
```

config the llms api-key:

```bash
export OPENAI_API_KEY="sk-YOUR-KEY"  # openai api-key
# optional:
export MOONSHOT_API_KEY="sk-YOUR-Key"  # moonshot api-key
export OPENAI_PROXY="xxxx" # OPENAI proxy if you need
```

### Config LLMs API

`GhostOS` use yaml file to configure the [LLMs](ghostos/core/llms/llm.py) library.
You can edit [ghostos/demo/configs/llm_conf.yaml]() as you want,
the yaml structure follows [LLMConfig](ghostos/core/llms/configs.py)

### AIFunc Test

`AIFunc` is a light-weighted agent that act like a function.
The `AIFunc` is able to call other `AIFunc` during processing to accomplish complex requests.

run test case:

```bash
venv/bin/python ghostos/demo/src/examples/run_aifunc_test.py
```

In [this case](ghostos/demo/src/examples/run_aifunc_test.py) we ask an agent-like AIFunc to do two things:

1. tell about the weather.
2. search news about something.

We expect the `AgentFn` will call `WeatherAIFunc` and `NewsAIFunc` to help with subtasks,
and give a final result to us.

The testing AIFuncs are defined at [aifuncs](ghostos/demo/src/aifuncs).

### File Editor Agent Test

run test case:

```bash
venv/bin/python ghostos/demo/src/examples/code_edits/file_editor_test.py
```

In [this case](ghostos/demo/src/examples/code_edits/file_editor_test.py) an agent will follow the instruction,
to replace all the chinese characters in the
file: [file_editor_test.py](ghostos/demo/src/examples/code_edits/file_editor_test.py).

The Agent's Thought is defined at [file_editor_thought.py](ghostos/thoughts/file_editor_thought.py),
and the python context of it is [file_editor_moss.py](ghostos/thoughts/file_editor_moss.py).
What the llm get in the runtime is what you see in this file.

### Tool Generation Agent Test

run test case:

```bash
venv/bin/python ghostos/demo/src/examples/code_edits/tool_generation_test.py
```

In [this case](ghostos/demo/src/examples/code_edits/tool_generation_test.py),
the agent is told to implements a `MockCache` class from `Cache` abstract class.
After running the case, the file [tool_generation_test.py](ghostos/demo/src/examples/code_edits/tool_generation_test.py)
shall be changed.

The Agent's Thought is defined at [pymodule_editor.py](ghostos/thoughts/pymodule_editor.py),
and the python context of it is [pymodule_editor_moss.py](ghostos/thoughts/pymodule_editor_moss.py).

### Planner Agent with Async Multi-Task scheduler Test

run test case:

```bash
venv/bin/python ghostos/demo/src/examples/code_edits/modify_directory_test.py
```

In [this case](ghostos/demo/src/examples/code_edits/modify_directory_test.py), an agent equipped with [DirectoryEdit](ghostos/libraries/file_editor.py)
and another agent [FileEditThought](ghostos/thoughts/file_editor_thought.py),
is told to modify all files in the `code_edits` directory.
It is supposed to call `MultiTask` library to dispatch several tasks
to [FileEditThought](ghostos/thoughts/file_editor_thought.py),
and the tasks will run parallely. After all tasks are finished, the agent will reply the result proactively.

The Agent's Thought and python context are both defined
at [directory_editor_thought.py](ghostos/thoughts/directory_editor_thought.py).
We are expecting the meta-agent can define an domain agent with its python context just like this.

### Ghost Func Test

`GhostFunc` is a toy we used to test MOSS in the early development.
It provides decorators, can wrap a signature only function to a LLM-driven function that produce code during calling.

run test case:

```bash
venv/bin/python ghostos/demo/src/examples/ghostfunc/get_weather.py
```

See more details in [get_weather.py](ghostos/demo/src/examples/ghostfunc/get_weather.py)

# Release plan

We are planning to release first version of this project at October,
The project supposed to be an agent framework with app prototypes rather than an application.
Right now we focus on developing some `GhostOS`'s components by itself.
Still a lot of works to do...
