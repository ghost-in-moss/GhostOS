# GhostOS framework

## Introduce

`GhostOS` is an LLM-driven Agent framework.
It offers a MOSS (LLM-oriented Operating System Simulation) interface to LLM:

1. Reflects python module's codes to prompt, let the LLM knows how to use them. Coding is Prompt Engineering.
2. Injects agent runtime libraries (such as multiple task scheduler) to the python context by IoC Container.
3. Maintain persist python processing context during multiple turns of LLM thinking
4. Execute the LLM generated codes to do almost everything.

With `GhostOS` The LLM Agents can generate Turning-complete python code to operate tools/system/thought...
And Agents are able to write python code to produce and integrate tools itself.
Furthermore, the Agent is built from code, and can be called as function by other Agents;
so the meta-agents are enabled to develop or optimize other domain agents, and integrate them.
By these methods we are aiming to develop the Self-Evolving Meta-Agent.

Article link: ...

## Quick Start

So far the `GhostOS` is still in the early stages of experimentation and exploration.
We are planning to release the first version at early October.
You are welcome to play with the early showcases:

### Prepare

1. make sure you've installed python > 3.12

clone the project

```bash
# clone the repository
git clone https://github.com/ghost-in-moss/GhostOS.git ghostos
# go to the directory
cd ghostos
# install poetry
python -m pip install poetry
# install requirements by poetry
poetry install
```

config the openai api-key

```bash
export export OPENAI_API_KEY="sk-YOUR-KEY"
```

### AIFunc Test

`AIFunc` is a light-weighted agent that act like a function.
The `AIFunc` is able to call other `AIFunc` during processing to accomplish complex requests.

run test case:

```bash
python ghostos/demo/src/examples/run_aifunc_test.py
```

In this case we ask a agent-like AIFunc to do two things:

1. tell about the weather.
2. search news about something.

We expect the `AgentFn` will call `WeatherAIFunc` and `NewsAIFunc` to help with subtasks,
and give a final result to us.

The testing AIFuncs are defined at [ghostos/demo/src/aifuncs]().

### File Editor Agent Test

run test case:

```bash
python ghostos/demo/src/examples/code_edits/file_editor_test.py
```

In this case an agent will follow the instruction,
to replace all the chinese characters in this file [ghostos/demo/src/examples/code_edits/file_editor_test.py]().

The Agent's Thought is defined at [ghostos/thoughts/file_editor_thought.py](),
and the python context that provide to it is [ghostos/thoughts/file_editor_moss.py]().

### Tool Generation Agent Test

run test case:

```bash
python ghostos/demo/src/examples/code_edits/tool_generation_test.py
```

In this case, the agent is told to implements a `MockCache` class from `Cache` abstract class.
After running the case, the file [ghostos/demo/src/examples/code_edits/tool_generation_test.py]() shall be changed.

The Agent's Thought is defined at [ghostos/thoughts/pymodule_editor.py](),
and the python context that provide to it is [ghostos/thoughts/pymodule_editor_moss.py]().

### Planner Agent with Async Multi-Task scheduler Test

run test case:

```bash
python ghostos/demo/src/examples/code_edits/modify_directory_test.py
```

In this case, an agent equipped with [DirectoryEdit](ghostos/libraries/file_editor.py)
and another agent [FileEditThought](ghostos/thoughts/file_editor_thought.py),
is told to modify all files in the `code_edits` directory.
It is supposed to call `MultiTask` library to dispatch several tasks
to [FileEditThought](ghostos/thoughts/file_editor_thought.py),
and the tasks will run parallely. After all tasks are finished, the agent will reply the result proactively.

The Agent's Thought and python context are both defined at [ghostos/thoughts/directory_editor_thought.py]()

### Ghost Func Test

`GhostFunc` is a toy we used to test MOSS in the early development.
It provides decorators, can wrap a signature only function to a LLM-driven function that produce code during calling.

run test case:

```bash
python ghostos/demo/src/examples/ghostfunc/get_weather.py
```

See more details in [ghostos/demo/src/examples/ghostfunc/get_weather.py]()



