from typing import Optional, Tuple, List, Dict
from abc import ABC, abstractmethod

from ghostos.abc import Identifier
from ghostos.container import Container, provide
from ghostos.contracts.storage import Storage
from ghostos.contracts.modules import Modules
from ghostos.contracts.logger import LoggerItf
from ghostos.core.ghosts import (
    Ghost, Operator, Inputs, Shell, Thoughts, Thought,
    MultiTask, Taskflow, Utils
)
from ghostos.core.moss import MossCompiler
from ghostos.core.messages import Caller
from ghostos.core.session import Session, Event, DefaultEventType
from ghostos.framework.operators import OnEventOperator
from ghostos.framework.multitasks import MultiTaskBasicImpl
from ghostos.framework.taskflow import TaskflowBasicImpl
from ghostos.core.moss.impl import MossCompilerImpl

__all__ = ['InputsPipe', 'BasicGhost']


class InputsPipe:
    def __init__(self, ghost: Ghost):
        self.ghost = ghost

    @abstractmethod
    def intercept(self, inputs: Inputs) -> Optional[Inputs]:
        pass


class BasicGhost(Ghost, ABC):
    inputs_pipes: List[InputsPipe] = []

    def __init__(
            self,
            container: Container,
            session: Session,
            shell: Shell,
            identifier: Identifier,
            root_thought: Thought,
            max_operator_runs: int,
    ):
        self._identifier = identifier
        self._max_operator_runs = max_operator_runs
        self._container = Container(parent=container)
        self._shell = shell
        self._session = session
        self._root_thought = root_thought
        # 日志的加工.
        logger = container.force_fetch(LoggerItf)
        trace = self._make_trace(session, shell)
        ghost_logger = logger.with_trace(trace)
        self._logger = ghost_logger
        # 初始化 container 的相关绑定.
        self._bootstrap_self_container()

    def _bootstrap_self_container(self):
        self._container.set(Ghost, self)
        self._container.set(Shell, self._shell)
        self._container.set(Session, self._session)
        self._container.set(LoggerItf, self._logger)
        self._container.register(provide(Thoughts, True)(lambda c: self.thoughts()))

    def identifier(self) -> Identifier:
        return self._identifier

    @abstractmethod
    def meta_prompt(self) -> str:
        pass

    @abstractmethod
    def thoughts(self) -> "Thoughts":
        pass

    @abstractmethod
    def modules(self) -> "Modules":
        pass

    @abstractmethod
    def workspace(self) -> Storage:
        pass

    def on_inputs(self, inputs: Inputs) -> Optional["Event"]:
        for pipe in self.inputs_pipes:
            inputs = pipe.intercept(inputs)
            if inputs is None:
                return None
        event = DefaultEventType.INPUT.new(
            task_id=inputs.task_id,
            messages=inputs.messages,
        )
        return event

    def init_operator(self, event: "Event") -> Tuple["Operator", int]:
        return OnEventOperator(event), self._max_operator_runs

    def container(self) -> Container:
        return self._container

    def session(self) -> Session:
        return self._session

    def shell(self) -> "Shell":
        return self._shell

    def root_thought(self) -> "Thought":
        return self._root_thought

    def logger(self) -> "LoggerItf":
        return self._logger

    def multitasks(self) -> "MultiTask":
        return MultiTaskBasicImpl(self)

    def taskflow(self, caller: Optional[Caller] = None) -> "Taskflow":
        return TaskflowBasicImpl(caller)

    def moss(self) -> "MossCompiler":
        return MossCompilerImpl(container=self._container)

    def utils(self) -> "Utils":
        return Utils(self)

    def fail(self, err: Optional[Exception]) -> None:
        self._logger.error(f"ghost run failed: {err}")

    def _make_trace(self, session: Session, shell: Shell) -> Dict:
        session_id = session.id()
        process_id = session.process().process_id
        task_id = session.task().task_id
        identifier = self.identifier()
        return {
            "ghost_id": identifier.id,
            "ghost_name": identifier.name,
            "shell_id": shell.id(),
            "session_id": session_id,
            "process_id": process_id,
            "task_id": task_id,
        }

    def done(self) -> None:
        self._logger.info(f"ghost is done")

    def destroy(self) -> None:
        self._container.destroy()
        del self._container
        del self._session
        del self._logger
        del self._shell
