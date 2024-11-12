from typing import Optional, List, Iterable, Tuple, Self

from ghostos.core.abcd.concepts import Session, G
from ghostos.core.messages import MessageKind, Message, Caller
from ghostos.core.runtime import TaskBrief
from ghostos.prompter import Prompter
from ghostos.container import Container


class SessionImpl(Session):

    def __init__(
            self,
            container: Container,
    ):
        self.container = container
        stream: Stream

        scope: Scope
        """the running scope of the session"""

        state: Dict[str, Union[Dict, BaseModel]]
        """session state that keep session state values"""

        container: Container
        """Session level container"""

        task: GoTaskStruct
        """current task"""

        thread: GoThreadInfo
        """thread info of the task"""

        logger: LoggerItf

    def is_alive(self) -> bool:
        pass

    def get_ghost(self) -> G:
        pass

    def get_context(self) -> Optional[Prompter]:
        pass

    def get_artifact(self) -> G.Artifact:
        pass

    def goal(self) -> G.Artifact:
        pass

    def refresh(self) -> Self:
        pass

    def flow(self) -> Flow:
        pass

    def messenger(self) -> "Messenger":
        pass

    def respond(self, messages: Iterable[MessageKind], remember: bool = True) -> Tuple[List[Message], List[Caller]]:
        pass

    def cancel_subtask(self, ghost: G, reason: str = "") -> None:
        pass

    def create_tasks(self, *tasks: "GoTaskStruct") -> None:
        pass

    def fire_events(self, *events: "Event") -> None:
        pass

    def get_task_briefs(self, *task_ids) -> List[TaskBrief]:
        pass

    def save(self) -> None:
        pass

    def fail(self, err: Optional[Exception]) -> bool:
        pass

    def done(self) -> None:
        pass

    def destroy(self) -> None:
        pass