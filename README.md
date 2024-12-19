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
And Agents are able to write python code to produce tools (as libraries) and integrate them (import modules or
dependency injections) itself;
Furthermore, the Agent is built from code, and can be called as function by other Agents.

So the meta-agents are enabled to define or optimize other domain agents, and integrate them during processing (
theoretically).
By these methods we are aiming to develop the Self-Evolving Meta-Agent.

Paper list: 
- [MOSS: Enabling Code-Driven Evolution and Context Management for AI Agents](https://arxiv.org/abs/2409.16120)

## Example

An agent named `DirectoryEditThought` is equipped with python context like this:

```python

from typing import TYPE_CHECKING
from ghostos.thoughts.magic_moss_thought import MagicMossThought
from ghostos.core.ghosts import Replier, MultiTask, NewTask
from ghostos.core.moss import Moss as Parent
from ghostos.libraries.file_editor import DirectoryEditor, FileEditor
from ghostos.thoughts.file_editor_thought import FileEditorThought
from pydantic import Field


class Moss(Parent):
    """
    you are equipped with some tools helping you to manage the current directory.
    and the FileEditorThought are helpful to manage a single file.
    """

    replier: Replier

    multitask: MultiTask
    """useful to handle multiple tasks, such as manage several files by FileEditorThought."""

    dir_editor: DirectoryEditor
    """ 
    the editor of the current directory.
    you can read or edit the files by FileEditorThought.
    so don't make up anything, based on what you informed.
    """
```

What we see is what `DirectoryEditThought` get,
MOSS reflect this module into prompt to the LLM,
with details of imported values such as `FileEditThought`, `DirectoryEditor` and `MultiTask`.
`DirectoryEditThought` shall code its plan With these tools:

User Query: `please checkout content of the '.py' files in code_edits directory,
and translate the comments in  chinese into english if you found them in the code.`

The LLM generation:

```python
def main(moss: Moss) -> Operator:
    # List all .py files in the code_edits directory
    code_edits_files = moss.dir_editor.edit_dir("code_edits").list(pattern="*.py", absolute=True, formated=False,
                                                                   summary=False)

    # Create tasks for checking out the content of each file
    tasks = []
    for file in code_edits_files:
        task = (
            f"translate_comments_{file.split('/')[-1]}",
            f"Translate comments in {file} from Chinese to English",
            FileEditorThought(filepath=file),
            "Please read the file content and translate any comments in Chinese to English."
        )
        tasks.append(task)

    # Run the tasks
    return moss.multitask.wait_on_tasks(*tasks)
```

In this code generation, `DirectoryEditThought` does:

1. know the directories through its prompt.
2. iterate files in `/code_edits` by `moss.dir_editor`.
3. create a task for each file by sub-agent `FileEditorThought`.
4. dispatch the tasks through `MultiTask` scheduler, and operate its thought to wait for the results.

## Quick Start

So far the `GhostOS` is still in the early stages of experimentation and exploration.
We are planning to release the first version at October.
You are welcome to play with the demo testcases:

### Prepare

First make sure you've installed `python > 3.12`, then:

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

`GhostOS` use yaml file to configure the [LLMs](ghostos/core/llms/abcd.py) library.
You can edit [ghostos/demo/configs/llms_conf.yml](ghostos/demo/configs/llms_conf.yml) as you want,
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

The testing AIFuncs are defined at [aifuncs](ghostos/demo/aifuncs_demo).

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
