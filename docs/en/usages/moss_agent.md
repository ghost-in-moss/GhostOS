# Moss Agent

`MossAgent` is the most fundamental Agent unit in the `GhostOS` project. It uses
the [MOSS Protocol](/en/concepts/moss_protocol.md) to provide a code interaction interface, allowing Large
Language Models to generate code to drive their own behavior.

## Simplest Example

create file `foo.py`:

```python

def plus(a: int, b: int) -> int:
    return a + b
```

run `ghostos web foo.py`, and ask the agent to call `plus` function.

## Run Agent

Running the command `ghostos web [python_modulename_or_filename]` can directly turn a Python file into an Agent and run
it with Streamlit.

For example:

```bash
ghostos web ghostos/demo/agents/jojo.py
# or 
ghostos web ghostos.demo.agents.jojo
```

When the command is executed, if the target file does not have a `__ghost__` attribute, it will reflect the target file
and generate an instance
of [MossAgent](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/ghosts/moss_agent/agent.py). This Agent can
call the functions and classes provided by the target file to perform tasks you propose in natural language.

Here is the source code:

```python
class MossAgent(ModelEntity, Agent):
    """
    Basic Agent that turn a python module into a conversational agent.
    """

    """ subclass of MossAgent could have a GoalType, default is None"""

    moss_module: str = Field(description="Moss module name for the agent")
    persona: str = Field(description="Persona for the agent, if not given, use global persona")
    instructions: str = Field(description="The instruction that the agent should follow")

    # optional configs
    name: str = Field(default="", description="name of the agent")
    description: str = Field(default="", description="description of the agent")
    code: Optional[str] = Field(default=None, description="code override the module")
    compile_module: Optional[str] = Field(None, description="Compile module name for the agent")
    llm_api: str = Field(default="", description="name of the llm api, if none, use default one")
    truncate_at_turns: int = Field(default=40, description="when history turns reach the point, truncate")
    truncate_to_turns: int = Field(default=20, description="when truncate the history, left turns")
```

You can also manually define a `__ghost__` instance:

```python

# the python module codes
...

# <moss-hide>
# add and agent definition manually at the tail of the file.
from ghostos.ghosts.moss_agent import MossAgent

__ghost__ = MossAgent(
    moss_module=__name__,
    name="agent name",
    description="agent desc",
    persona="persona",
    instruction="system instructions",
    # use llms model defined at app/configs/llms_conf.yml
    llm_api="moonshot-v1-128k",
)

# </moss-hide>
```

> Normally, a Python file can be started as an agent without any modifications. For example, a unit test file.Normally,
> a Python file can be started as an agent without any modifications. For example, a unit test file.

## Code As Prompt

MossAgent will automatically reflect the target Python module into a Prompt, providing it to the large model.
To see the detailed prompt, you can use `ghostos web` to generate the `instructions` button on the interface to view its
system instruction.

The default reflection principle can be found in [MOSS Protocol](/en/concepts/moss_protocol.md). In short:

1. Referenced functions will automatically reflect the function name + doc
2. Abstract classes will reflect the source code

The large model will call a tool named `moss` based on the instruction to generate code.
The generated code will be executed in the temporary module compiled
by [Moss](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/moss/ghostos_moss/abcd.py).

Source
Code: [MossAction](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/ghosts/moss_agent/agent.py#MossAction).

If some code you want hide from LLM, use `# <moss-hide>` and `# </moss-hide>` markers:

```python

# <moss-hide>
...
# the code here is not visible to llm
# </moss-hide>
```

If the results of automatic reflection are not satisfactory, you can also manually define it through the magic
method `__moss_attr_prompts__`.

```python
from foo import Foo


# <moss-hide>

def __moss_attr_prompts__():
    """
    :return: Iterable[Tuple[attr_name: str, attr_prompt: str]]
    """
    yield "Foo", ""  # if the prompt is empty, won't prompt it to llm
# </moss-hide>
```

## Magic lifecycle functions

The `MossAgent` uses magic methods within various files to define its special operational logic.
The benefits of this approach are, first, to simplify the use for developers; and second, for the Meta-Agent, to reduce
the workload when creating an Agent.

All lifecycle methods can be found in the following three files:

- [for developer](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/ghosts/moss_agent/for_developer.py):
  Lifecycle management for developers.
    - `__moss_agent_providers__`
    - `__shell_providers__`
    - `__moss_agent_creating__`
    - `__moss_agent_truncate__`
    - `__moss_agent_parse_event__`
    - `__moss_agent_injections__`
    - `__moss_agent_on_[event_type]__`:
- [for meta ai](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/ghosts/moss_agent/for_meta_ai.py): for
  developer and Meta AI
    - `__moss_agent_artifact__`
    - `__moss_agent_actions__`
    - `__moss_agent_thought__`
    - `__moss_agent_instruction__`
    - `__moss_agent_persona__`
- [moss lifecycle](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/moss/ghostos_moss/lifecycle.py)

Copy these methods into the current file to activate custom magic methods.
All these magic methods are **optional**. If they can solve the problem, then you can use them.

If all magic methods are insufficient, then the best approach is to implement your own `Ghost` and `GhostDriver`
classes,
see [concepts.py](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/abcd/concepts.py).

## Define Moss Class

Usually importing classes and methods is sufficient for an Agent to operate. However, there are two situations where you
need to introduce the `Moss` class. (Model-oriented Operating System Simulator):

1. `Context Manage`: Wish to define variables that can be changed continuously in multi-turn conversations.
2. `Runtime Injection`: use [IoC Container](/en/concepts/ioc_container.md) for dependencies injections.

Define a Moss class in the target module:

```python
from ghostos_moss import Moss as Parent


class Moss(Parent):
    ...
    pass
```

Whether this class is defined or not, a `moss` object will be generated during the execution of MossAgent. The code
written for MossAgent also uses it, with a prompt as follows:

(Will be continuously optimized):

```markdown
You are able to call the `moss` tool, generate code to fulfill your will.
the python code you generated, must include a `run` function, follow the pattern:

\```python
def run(moss: Moss):
"""
:param moss: instance of the class `Moss`, the properties on it will be injected with runtime implementations.
:return: Optional[Operator]
if return None, the outer system will perform default action, or observe the values you printed.
Otherwise, the outer system will execute the operator.
You shall only return operator by the libraries provided on `moss`.
"""
\```
```

详见 [instructions](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/ghosts/moss_agent/instructions.py)

### Define Variables On Moss

The `str`, `float`, `int`, `bool`, `str`, and `pydantic.BaseModel` types mounted on the Moss class will be automatically
saved, so MossAgent can directly use them as variables.

Note that these variable types must be serializable. For example:

```python
from ghostos_moss import Moss as Parent
from pydantic import BaseModel, Field


class YourVariables(BaseModel):
    variables: dict = Field(default_factory=dict, description="you can manage your variables here")


# 名为 Moss 的类是一个特殊的类. 
class Moss(Parent):
    vars: YourVariables = YourVariables()
```

Furthermore, if the mounted data object
implements [ghostos_common.prompter.Prompter](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/prompter.py),
MossAgent will automatically generate a prompt in the system instruction to be provided to the large model.

For more information on this logic, see the `ghostos.ghosts.moss_agent.instructions.get_moss_context_prompter` function.

### Runtime Injection

The `abstract class` mounted on the Moss class will automatically perform dependency injection from
the [IoC Container](/en/concepts/ioc_container.md). There are three ways to provide implementations for these
abstract classes:

- Pass in instances at definition:

```python
from ghostos_moss import Moss as Parent


class Foo:
    ...
    pass


# 名为 Moss 的类是一个特殊的类. 
class Moss(Parent):
    foo: Foo = Foo()
```

- Through the magic method `__moss_agent_injections__`, manually define the instances to be injected.

```python
from ghostos_moss import Moss as Parent
from foo import Foo


class Moss(Parent):
    foo: Foo


# <moss-hide>
# the code in moss-hide is invisible to llm

def __moss_agent_injections__(agent, session) -> Dict[str, Any]:
    """
    manually define some of the injections to the Moss Class.
    if a property of Moss is not injected here, the session container will inject it by typehint.
    """
    from foo.impl import FooImpl
    return {
        "foo": FooImpl(...)
    }
# </moss-hide>
```

The third method is to register dependency implementations in the [IoC Container](/en/concepts/ioc_container.md).
The `Moss` class will perform type analysis upon instantiation and automatically perform dependency injection. There are
several ways to register dependencies:

## Register dependencies

`GhostOS` isolates dependencies at different levels during runtime through an inheritable `IoC Container Tree`. The
system has the following default container levels:

- [App Root Container](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/bootstrap.py): Unique container for
  the process
- `GhostOS.container`: Unique container for the process, essentially the same as the App Root Container.
- `Shell.container`: A container shared by all ghosts running in parallel within the same process. Typically used to
  launch singletons related to the body.
- `Conversation.container`: Dependencies owned by a single Ghost.
- `MossRuntime.container`: A temporary container generated each time `MossRuntime` is compiled. Used to
  register `MossRuntime` itself.

During the runtime of `MossAgent`, dependency injection is performed by `MossRuntime.container`, so it inherits
registered dependencies from each parent container and can also override them.

Some dependencies provided by the `GhostOS` system are as follows:

- [LoggerItf](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/contracts/logger.py)
- [Configs](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/contracts/configs.py)
- [Workspace](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/contracts/workspace.py)
- [Variables](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/contracts/variables.py)
- [LLMs](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/core/llms/llms.py)
- [Assets](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/contracts/assets.py)
- [GhostOS](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/abcd/concepts.py)
- [Shell](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/abcd/concepts.py)
- [Conversation](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/abcd/concepts.py)
- [Session](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/abcd/concepts.py)
- [Scope](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/abcd/concepts.py)
- [Ghost](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/abcd/concepts.py)
- [MossCompiler](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/moss/ghostos_moss/abcd.py)
- [Tasks](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/core/runtime/tasks.py)
- [Threads](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/core/runtime/threads.py)
- [EventBus](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/core/runtime/events.py)

More system-level bindings can be debugged by calling `Container.contracts(recursively=True)`.

### Register MossAgent dependencies

The simplest method is to define dependencies directly in a Python file using magic methods:

```python

# <moss-hide>

def __moss_agent_providers__(agent: A) -> Iterable[Provider]:
    """
    return conversation level providers that specially required by the Agent.
    the conversation container will automatically register the providers and run them.

    :param agent: the moss agent instance.
    :return: providers that register to the session container.
    """
    return []

# </moss-hide>
```

These dependencies will be registered when the `Conversation` is created.

### Register root dependencies

Modifying the global container, or creating your own container, both can register services in the process:

```python
from ghostos.bootstrap import reset, make_app_container

# 定义新的全局容器
new_root_container = make_app_container(...)

# 重置 ghostos.bootstrap.app_container
reset(new_root_container)
```

This way, you can register process-level dependencies that take effect for all containers.

### Register Shell dependencies

Dependencies can be registered when Shell is launched. A process may repeatedly start multiple Shells, hence Shell has a
separate isolation level.

The simplest way is to register at the start of the life cycle when the shell is launched:

```python
from ghostos.bootstrap import get_ghostos

ghostos = get_ghostos()

# register shell level providers at when shell is creating
shell = ghostos.create_shell("shell name", providers=[...])
```

对于使用 `ghostos web` 或 `ghostos console` 启动的 python 文件, 也可以简单注册在文件的魔术方法内:

```python
# <moss-hide>

def __shell_providers__() -> Iterable[Provider]:
    """
    return shell level providers that specially required by the Agent.
    if the shell is running by `ghostos web` or `ghostos console`,
    the script will detect the __shell_providers__ attribute and register them into shell level container.

    You can consider the Shell is the body of an agent.
    So shell level providers usually register the body parts singletons, bootstrap them and register shutdown functions.
    """
    return []
# </moss-hide>
```

For Python files launched with `ghostos web` or `ghostos console`, they can also be simply registered within the magic
method of the file:

## Register Conversation dependencies

The `__moss_agent_providers__` magic method can usually handle the registration of dependencies for Conversation.
However,
if manual registration is needed, it should be done when creating the Conversation:

```python
from ghostos.abcd import Shell, Conversation, Ghost

shell: Shell = ...
my_ghost: Ghost = ...

conversation = shell.sync(my_ghost)

# register here. usually not necessary
conversation.container().register(...)

```

## Meta-Agent

`GhostOS` will provide a `MossAgent` to generate other `MossAgent`s, which is the Meta-Agent.
Currently, it is still in development and testing.