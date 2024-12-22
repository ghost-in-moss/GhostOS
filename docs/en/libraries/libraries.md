# Libraries

For traditional agents based on `JSON Schema Function Call`, their interaction object is `Tool`. In contrast, `GhostOS`
provides Turing-complete code to the Agent, making the interaction object `Library`.

The `libraries` here are not for developers but for Large Language Models (LLMs).

There are three steps for LLMs to use Libraries:

1. Define and implement a Library.
2. Register the abstract and implementation of the Library to the IoC (Inversion of Control) Container.
3. Bind the Library to the Moss class.

## Code As Prompt

The core concept here is `Code As Prompt`, which means that while writing code, you are also defining the prompt. Taking
multi-task scheduling as an example:

```python
class Subtasks(Prompter, ABC):
    """
    library that can handle async subtasks by other ghost instance.
    """
    MessageKind = Union[str, Message, Any]
    """message kind shall be string or serializable object"""

    @abstractmethod
    def cancel(self, name: str, reason: str = "") -> None:
        """
        cancel an exists subtask
        :param name: name of the task
        :param reason: the reason to cancel it
        :return:
        """
        pass

    @abstractmethod
    def send(
            self,
            name: str,
            *messages: MessageKind,
            ctx: Optional[Ghost.ContextType] = None,
    ) -> None:
        """
        send message to an existing subtask
        :param name: name of the subtask
        :param messages: the messages to the subtask
        :param ctx: if given, update the ghost context of the task
        :return:
        """
        pass

    @abstractmethod
    def create(
            self,
            ghost: Ghost,
            instruction: str = "",
            ctx: Optional[Ghost.ContextType] = None,
            task_name: Optional[str] = None,
            task_description: Optional[str] = None,
    ) -> None:
        """
        create subtask from a ghost instance
        :param ghost: the ghost instance that handle the task
        :param instruction: instruction to the ghost
        :param ctx: the context that the ghost instance needed
        :param task_name: if not given, use the ghost's name as the task name
        :param task_description: if not given, use the ghost's description as the task description
        """
        pass
```

Bind it to the moss class that the Agent can see:

```python
from ghostos.abcd import Subtasks
from ghostos.core.moss import Moss as Parent


class Moss(Parent):
    subtasks: Subtasks
    """manager your multi-agent tasks"""
```

* The source code of the class will be automatically reflected to the Prompt, allowing the Large Language Model to see
  it.
* The implementation of this library will be automatically injected into the `Moss` instance, and the Large Language
  Model can use the generated code to call it.

For more specific usage, please refer to [MossAgent](/en/usages/moss_agent.md).

We hope that tools provide to the Large Language Models in the future, should be based on industry-standard protocols
similar
to
the [MOSS Protocol](/en/concepts/moss_protocol.md), and be developed and shared in the form of code
repositories.

## Developing Libraries

The libraries that come with GhostOS out of the box are still under development and testing.
These tools are expected to be placed
in [ghostos/libraries](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/libraries).