from typing import Optional, Tuple, List, Dict, Type, ClassVar
from abc import ABC, abstractmethod

from ghostos.container import provide
from ghostos.contracts.storage import Storage
from ghostos.contracts.logger import LoggerItf
from ghostos.contracts.shutdown import Shutdown
from ghostos.contracts.pool import Pool
from ghostos.core.ghosts import (
    Ghost, GhostConf, Operator, Inputs, Shell, Mindset, Thought,
    MultiTask, Taskflow, Utils, Workspace
)
from ghostos.core.ghosts.schedulers import Replier
from ghostos.core.llms import LLMs
from ghostos.core.moss import MossCompiler
from ghostos.core.messages import Caller
from ghostos.core.session import (
    Session, Event, DefaultEventType,
    EventBus, Tasks, Processes, Threads, Messenger,
    Process, Task, MsgThread,
)
from ghostos.framework.operators import OnEventOperator
from ghostos.framework.multitasks import MultiTaskBasicImpl
from ghostos.framework.taskflow import TaskflowBasicImpl
from ghostos.framework.repliers import ReplierImpl
from ghostos.framework.session import BasicSession
from ghostos.core.moss.impl import MossCompilerImpl
from ghostos.contracts.modules import Modules
from ghostos.core.messages import Stream
from ghostos.framework.mindsets import WorkspaceMindsetProvider
from ghostos.framework.configs import Configs
from ghostos.container import Container, Provider
from ghostos.entity import EntityFactory

__all__ = ['InputsPipe', 'BasicGhost']


class InputsPipe:
    def __init__(self, ghost: Ghost):
        self.ghost = ghost

    @abstractmethod
    def intercept(self, inputs: Inputs) -> Optional[Inputs]:
        pass


class BasicGhost(Ghost, ABC):
    """
    Basic ghost implementation.
    """

    inputs_pipes: List[Type[InputsPipe]] = []
    """inputs pipes that can intercept inputs"""

    providers: List[Provider] = []
    """ providers that ghost container shall register"""

    depend_contracts: ClassVar[List[Type]] = [
        Modules,
        LoggerItf,
        Storage,
        Configs,
        EventBus,
        Processes,
        Tasks,
        Threads,
        Pool,
        LLMs,
        Shutdown,
    ]

    ghost_contracts: ClassVar[List[Type]] = [
        Session,
        Shell,
        Ghost,
        Mindset,
        EntityFactory,
        MultiTask,
        Taskflow,
        Replier,
        Workspace,
        MossCompiler,
        Utils,
        Messenger,
        EntityFactory,
    ]
    """default contracts that ghost container shall validate before start."""

    def __init__(
            self, *,
            conf: GhostConf,
            container: Container,
            shell: Shell,
            workspace: Workspace,
            entity_factory: EntityFactory,
            upstream: Stream,
            process: Process,
            max_operator_runs: int,
            task: Optional[Task] = None,
            task_id: Optional[str] = None,
    ):
        # init ghost container, validate it first
        self._validate_parent_container_contracts(container)
        container = Container(parent=container)
        self._container = container
        # other properties
        self._origin_event: Optional[Event] = None
        # workspace
        self._workspace = workspace
        # config
        self._conf = conf
        self._max_operator_runs = max_operator_runs
        # init shell.
        self._shell = shell
        # entity factory
        self._entity_factory = entity_factory
        # root thought
        root_thought_meta = conf.root_thought_meta()
        root_thought = entity_factory.force_new_entity(root_thought_meta, Thought)
        self._root_thought = root_thought
        logger = container.force_fetch(LoggerItf)
        # instance session.
        self._session = self.make_session(
            upstream=upstream,
            root_thought=root_thought,
            process=process,
            task=task,
            task_id=task_id,
            logger=logger,
        )
        # prepare ghost logger
        trace = self.trace()
        ghost_logger = logger.with_trace(trace)
        self._logger = ghost_logger
        # 初始化 container 的相关绑定.
        self._bootstrap_ghost_container()
        # 检查所有必须绑定的对象.
        self._validate_default_contracts()

    def _bootstrap_ghost_container(self):
        # init shell
        # storage provider
        container = self._container
        # init mindset
        if not container.bound(Mindset):
            mindset_provider = WorkspaceMindsetProvider()
            container.register(mindset_provider)

        self._container.set(Ghost, self)
        self._container.set(Shell, self._shell)
        self._container.set(Session, self._session)
        self._container.set(LoggerItf, self._logger)
        self._container.set(Workspace, self._workspace)
        self._container.set(EntityFactory, self._entity_factory)

        # register ghost self modules.
        ghost_function_providers = {
            MultiTask: self.multitasks,
            Taskflow: self.taskflow,
            Replier: self.replier,
            MossCompiler: self.moss,
            Utils: self.utils,
        }
        for contract, maker in ghost_function_providers.items():
            _maker = maker
            self._container.register_maker(contract, _maker)

        # register session drivers:
        session_function_providers = {
            Tasks: self._session.tasks,
            Processes: self._session.processes,
            Messenger: self._session.messenger,
            Threads: self._session.threads,
            EventBus: self._session.eventbus,
        }
        for contract, maker in session_function_providers.items():
            _maker = maker
            self._container.register_maker(contract, _maker)

        # register shell drivers
        for driver in self._shell.drivers():
            _driver = driver

            def maker(c):
                return self._shell.get_driver(_driver)

            provider = provide(driver, False)(maker)
            self._container.register(provider)

        # register ghost providers
        for provider in self.providers:
            self._container.register(provider)
        self._container.bootstrap()

    def make_session(
            self,
            logger: LoggerItf,
            upstream: Stream,
            process: Process,
            root_thought: Thought,
            task: Optional[Task] = None,
            task_id: Optional[str] = None,
    ) -> Session:
        container = self.container()
        identifier = self.conf().identifier()
        processes = container.force_fetch(Processes)
        tasks = container.force_fetch(Tasks)
        threads = container.force_fetch(Threads)
        pool = container.force_fetch(Pool)
        eventbus = container.force_fetch(EventBus)
        # task and thread init.
        if task is None:
            if task_id is not None:
                task = tasks.get_task(task_id, True)
                if not task:
                    raise RuntimeError(f"Task {task_id} not found")
            else:
                task_id = process.main_task_id
                task = tasks.get_task(task_id, False)
                if not task:
                    identifier = root_thought.identifier()
                    meta = root_thought.to_entity_meta()
                    task = Task.new(
                        task_id=task_id,
                        session_id=process.session_id,
                        process_id=process.process_id,
                        name=identifier.name,
                        description=identifier.description,
                        meta=meta,
                    )
                # 生成锁.
                task.lock = tasks.refresh_task_lock(task.task_id, "")
        logger = logger.with_trace({
            "process_id": process.process_id,
            "session_id": process.session_id,
            "task_id": task.task_id,
            "thread_id": task.thread_id,
        })
        thread = threads.get_thread(task.thread_id)
        if thread is None:
            thread = MsgThread.new(None, thread_id=task.thread_id)
        return BasicSession(
            ghost_name=identifier.name,
            ghost_role=self.role(),
            upstream=upstream,
            eventbus=eventbus,
            pool=pool,
            processes=processes,
            tasks=tasks,
            threads=threads,
            logger=logger,
            process=process,
            task=task,
            thread=thread,
        )

    @abstractmethod
    def meta_prompt(self) -> str:
        pass

    def mindset(self) -> "Mindset":
        return self._container.force_fetch(Mindset)

    def modules(self) -> "Modules":
        return self._container.force_fetch(Modules)

    def workspace(self) -> Workspace:
        return self._workspace

    def configs(self) -> Configs:
        return self._container.force_fetch(Configs)

    def entity_factory(self) -> EntityFactory:
        return self._entity_factory

    def _validate_default_contracts(self):
        for contract in self.ghost_contracts:
            if not self._container.bound(contract):
                raise NotImplementedError(f"Contract {contract} not bound to ghost container")

    @classmethod
    def _validate_parent_container_contracts(cls, container: Container):
        for contract in cls.depend_contracts:
            if not container.bound(contract):
                raise NotImplementedError(f"Contract {contract} not bound to the container")

    def on_inputs(self, inputs: Inputs) -> Optional["Event"]:
        for pipe_type in self.inputs_pipes:
            pipe = pipe_type(self)
            inputs = pipe.intercept(inputs)
            if inputs is None:
                return None
        task = self.session().task()
        if task.is_new():
            event = DefaultEventType.CREATED.new(
                task_id=self.session().task().task_id,
                messages=inputs.messages,
            )
        else:
            event = DefaultEventType.INPUT.new(
                task_id=self.session().task().task_id,
                messages=inputs.messages,
            )
        return event

    def init_operator(self, event: "Event") -> Tuple["Operator", int]:
        # set origin event
        self._origin_event = event
        return OnEventOperator(event), self._max_operator_runs

    def init_event(self) -> Optional["Event"]:
        return self._origin_event

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

    def llms(self) -> LLMs:
        return self._container.force_fetch(LLMs)

    def multitasks(self) -> "MultiTask":
        return MultiTaskBasicImpl(self)

    def taskflow(self) -> "Taskflow":
        return TaskflowBasicImpl()

    def replier(self) -> "Replier":
        e = self.init_event()
        callback_task_id = e.from_task_id if e else None
        return ReplierImpl(callback_task_id)

    def moss(self) -> "MossCompiler":
        return MossCompilerImpl(container=self._container)

    def utils(self) -> "Utils":
        return Utils(self)

    def trace(self) -> Dict[str, str]:
        return self._make_trace(self._session, self._shell)

    def _make_trace(self, session: Session, shell: Shell) -> Dict:
        session_id = session.id()
        process_id = session.process().process_id
        task_id = session.task().task_id
        identifier = self.conf().identifier()
        return {
            "ghost_id": identifier.id,
            "ghost_name": identifier.name,
            "shell_id": shell.id(),
            "session_id": session_id,
            "process_id": process_id,
            "task_id": task_id,
        }

    def save(self) -> None:
        self._logger.info(f"save ghost")
        self._session.save()

    def done(self) -> None:
        self._logger.info(f"ghost is done")
        self._session.save()
        self._session.done()

    def fail(self, err: Optional[Exception]) -> None:
        self._logger.error(f"ghost run failed: {err}")

    def destroy(self) -> None:
        self._container.destroy()
        del self._container
        del self._session
        del self._logger
        del self._shell
