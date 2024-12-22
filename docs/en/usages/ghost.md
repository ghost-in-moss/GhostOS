# Ghost

"Ghost" is the  "minimum stateful unit" of an LLM-driven unit.
The term comes from [Ghost In the Shell](https://en.wikipedia.org/wiki/Ghost_in_the_Shell).

In the architectural design of "GhostOS", an intelligent agent swarm is composed of many "Ghost" units, each with its
own state, memory, and context (Session);
and they can communicate fully asynchronously through the "EventBus".

![architecture](../../assets/architecture.png)

## Why the word `Ghost` instead of `Agent`

In the author's architectural vision, an `Agent` is a robot or interaction interface (like IM) for users, possessing a
physical form (also known as Shell).

However, within a single shell, there may be a Multi-Agent (or Multi-Ghost) swarm running, which serves the following
purposes:

* Parallel execution of multiple tasks.
* Simulation of different roles for thought experimentation.
* Asynchronous executions of long-duration tasks.

Let's take a simple example:

1. The `Agent` for user conversation, by default, runs the fast `gpt-4o` model to control the dialogue.
2. When the user asks a complex question, the main ghost calls `gpt-o3` to run a 30-second thought process.
3. During these 30 seconds, the main agent does not block but continues to converse with the user.
4. After 30 seconds, the main agent receives the asynchronous callback result and informs the user.

In this example, parallel execution and the event bus are the most critical features. Therefore, a Ghost can be:

* An Agent for user conversation.
* A clone opened by the main Agent, using different models, focused on a specific task or thought.
* A workflow running in the background.
* An automated robot running in the background.
* An independent script.
* A component of an embodied intelligent agent that can execute natural language commands.
* A background program that reflects on its own operational effectiveness.

Their common characteristics are:

* Driven by large language models.
* Possessing the ability to run in multiple rounds.
* Similar to operating system threads, they are the smallest synchronous running units with independent contexts.

## Ghost Driver

In `GhostOS`, the prototype of a `Ghost` needs to be defined through at least two classes.

[Ghost](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/abcd/concepts.py):

```python

class Ghost(Identical, EntityClass, ABC):
    """
    the class defines the model of a kind of ghosts.
    four parts included:
    1. configuration of the Ghost, which is Ghost.__init__. we can predefine many ghost instance for special scenes.
    2. context is always passed by the Caller of a ghost instance. each ghost class has it defined context model.
    3. goal is the static output (other than conversation messages) of a ghost instance.
    4. driver is
    """

    ArtifactType: ClassVar[Optional[Type]] = None
    """ the model of the ghost's artifact, is completing during runtime"""

    ContextType: ClassVar[Optional[Type[ContextType]]] = None
    """ the model of the ghost's context, is completing during runtime'"""

    DriverType: ClassVar[Optional[Type[GhostDriver]]] = None
    """ separate ghost's methods to the driver class, make sure the ghost is simple and clear to other ghost"""

```

[GhostDriver](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/abcd/concepts.py) :

```python

class GhostDriver(Generic[G], ABC):
    """
    Ghost class is supposed to be a data class without complex methods definitions.
    so it seems much clear when prompt to the LLM or user-level developer.
    when LLM is creating a ghost class or instance, we expect it only see the code we want it to see,
    without knowing the details codes of it, for safety / fewer tokens / more focus or other reasons.

    so the methods of the ghost class defined in this class.
    only core developers should know details about it.
    """

    def __init__(self, ghost: G) -> None:
        self.ghost = ghost

    def make_task_id(self, parent_scope: Scope) -> str:
        """
        generate unique instance id (task id) of the ghost instance.
        """
        pass

    @abstractmethod
    def get_artifact(self, session: Session) -> Optional[G.ArtifactType]:
        """
        generate the ghost goal from session_state
        may be the Goal Model is a SessionStateValue that bind to it.

        The AI behind a ghost is not supposed to operate the session object,
        but work on the goal through functions or Moss Injections.
        """
        pass

    @abstractmethod
    def get_instructions(self, session: Session) -> str:
        """
        get system instructions of the ghost.
        usually used in client side.
        """
        pass

    @abstractmethod
    def actions(self, session: Session) -> List[Action]:
        """
        return actions that react to the streaming output of llm
        """
        pass

    @abstractmethod
    def providers(self) -> Iterable[Provider]:
        """
        ghost return conversation level container providers.
        the provider that is not singleton will bind to session also.
        """
        pass

    @abstractmethod
    def parse_event(
            self,
            session: Session,
            event: Event,
    ) -> Union[Event, None]:
        """
        intercept the ghost event
        :returns: if None, the event will be ignored
        """
        pass

    @abstractmethod
    def on_creating(self, session: Session) -> None:
        """
        when the ghost task is created first time.
        this method can initialize the thread, pycontext etc.
        """
        pass

    @abstractmethod
    def on_event(self, session: Session, event: Event) -> Union[Operator, None]:
        """
        all the state machine is only handling session event with the predefined operators.
        """
        pass

    @abstractmethod
    def truncate(self, session: Session) -> GoThreadInfo:
        """
        truncate the history messages in the thread
        """
        pass

```

The motivation for this approach is that `GhostOS` employs the `Code As Prompt` concept to directly reflect code into
prompts that the Large Language Model perceives. Within the Multi-Agent architecture, the detailed code of `GhostDriver`
is unnecessary for the Agents that utilize it. By separating the data structure-focused `Ghost` from the
logic-focused `GhostDriver`, it facilitates a more straightforward understanding for other Agents on how to construct an
Agent.

## Ghost Context

The [Context](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/abcd/concepts.py) can be understood as the
input parameters for the `Ghost` runtime. It accepts strongly-typed data structures and generates system prompts for the
Large Language Model to understand the context. At the same time, the Large Language Model can manipulate the context as
a variable.

The Context implements [Prompter](/en/concepts/prompter.md), which is essentially a `Prompt Object Model` similar
to `DOM`. It requires strongly-typed parameters to reflect system instructions as part of the prompt submitted to the
LLM.

The Context is typically used to implement:

* The state of an embodied agent's own body and recognition of the surrounding environment.
* The state of AI applications on the edge side (such as IDEs) and synchronize cognition with users.
* Dynamically changing input data parameters, such as what an AI operator sees on a monitoring panel.

Passed as input to the conversation:

```python
from pydantic import Field
from ghostos.abcd import Context, Conversation, Ghost


class ProjectContext(Context):
    directory: str = Field(description="the root directory of a project")


project_agent: Ghost = ...
project_context: ProjectContext = ...
conversation: Conversation = ...

conversation.talk("your query to edit the project", project_context)
```

If necessary, MossAgent can manipulate a Context through `Moss`:

```python
from ghostos.abcd import Context
from ghostos.core.moss import Moss as Parent
from pydantic import Field


class ProjectContext(Context):
    directory: str = Field(description="the root directory of a project")


class Moss(Parent):
    # the moss agent can operate this ctx instance.
    ctx: ProjectContext
```

## Ghost Artifact

The [Artifact](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/abcd/concepts.py) can be understood as the
output parameter of `Ghost` at runtime. However, this output parameter is subject to continuous changes.

Through `Conversation`, you can obtain the `Artifact` object of `Ghost` at runtime for rendering on the client side.

```python
from ghostos.abcd import Conversation, Ghost, Shell

my_ghost: Ghost = ...
shell: Shell = ...
conversation: Conversation = shell.sync(ghost=my_ghost)

conversation.talk(...)

# get artifact 
artifact = conversation.get_artifact()
```

## ChatBot and MossAgent

[Chatbot](chatbot.md) and [MossAgent](moss_agent.md) are the basic implementations of Ghost in the `GhostOS` project.

## More Ghosts

developing...