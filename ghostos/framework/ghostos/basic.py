from typing import Optional, List
from abc import ABC, abstractmethod
from os.path import join, dirname
import yaml
from logging.config import dictConfig
from ghostos.container import Container
from ghostos.core.ghostos import AbsGhostOS
from ghostos.core.ghosts import Ghost
from ghostos.core.messages import Stream
from ghostos.core.session import Process, Task
from ghostos.contracts.shutdown import ShutdownProvider
from ghostos.contracts.modules import Modules, DefaultModulesProvider
from ghostos.framework.storage import FileStorageProvider
from ghostos.framework.logger import NamedLoggerProvider
from ghostos.framework.workspaces import BasicWorkspaceProvider
from ghostos.framework.configs import WorkspaceConfigsProvider
from ghostos.framework.threads import WorkspaceThreadsProvider
from ghostos.framework.processes import WorkspaceProcessesProvider
from ghostos.framework.tasks import WorkspaceTasksProvider
from ghostos.framework.llms import ConfigBasedLLMsProvider
from ghostos.framework.eventbuses import MemEventBusImplProvider
from ghostos.contracts.pool import DefaultPoolProvider
from ghostos.entity import EntityFactory, EntityFactoryImpl
from ghostos.container import Provider, Bootstrapper

project_dir = dirname(dirname(dirname(__file__)))
demo_dir = join(project_dir, "demo")
logging_conf_path = join(demo_dir, "configs/logging.yml")

__all__ = ['BasicGhostOS']


class BasicGhostOS(AbsGhostOS, ABC):

    def __init__(
            self, *,
            root_dir: str = demo_dir,
            logger_conf_path: str = logging_conf_path,
            logger_name: str = "debug",
            config_path: str = "configs",
            runtime_path: str = "runtime",
            source_path: str = "src",
            processes_path: str = "processes",
            tasks_path: str = "tasks",
            threads_path: str = "threads",
            llm_config_path: str = "llms_conf.yml",
            container: Optional[Container] = None,
            providers: Optional[List[Provider]] = None,
            bootstrapper: Optional[List[Bootstrapper]] = None,
    ):
        self._root_dir = root_dir
        self._processes_path = processes_path
        self._tasks_path = tasks_path
        self._threads_path = threads_path
        self._llm_config_path = llm_config_path
        self._config_path = config_path
        self._runtime_path = runtime_path
        self._source_path = source_path

        # container
        self._container = container if container else Container()
        self._prepare_logger(logger_conf_path, logger_name)
        self._prepare_container(providers, bootstrapper)

        modules = self._container.force_fetch(Modules)
        # register entity factory
        self._entity_factory = EntityFactoryImpl(modules.import_module)
        self._container.set(EntityFactory, self._entity_factory)
        self._container.bootstrap()
        self._on_initialized()

    @abstractmethod
    def _on_initialized(self):
        """
        callback on initialized the ghost os
        """
        pass

    @abstractmethod
    def make_ghost(
            self, *,
            upstream: Stream,
            process: Process,
            task: Optional[Task] = None,
            task_id: Optional[str] = None,
    ) -> Ghost:
        pass

    @abstractmethod
    def on_error(self, error: Exception) -> bool:
        pass

    def _default_providers(self) -> List[Provider]:
        return [
            FileStorageProvider(self._root_dir),
            BasicWorkspaceProvider(
                workspace_dir="",
                configs_path=self._config_path,
                runtime_path=self._runtime_path,
            ),
            DefaultModulesProvider(),
            WorkspaceConfigsProvider(),
            WorkspaceProcessesProvider(self._processes_path),
            WorkspaceTasksProvider(self._tasks_path),
            WorkspaceThreadsProvider(self._threads_path),
            DefaultPoolProvider(100),
            ConfigBasedLLMsProvider(self._llm_config_path),
            MemEventBusImplProvider(),
            ShutdownProvider(),
        ]

    def _prepare_container(
            self,
            providers: Optional[List[Provider]] = None,
            bootstrapper: Optional[List[Bootstrapper]] = None,
    ):
        if providers:
            for provider in providers:
                self._container.register(provider)
        if bootstrapper:
            for b in bootstrapper:
                self._container.add_bootstrapper(b)
        # register default providers.
        for provider in self._default_providers():
            contract = provider.contract()
            # 只有未绑定的, 才会使用默认的去绑定.
            if not self._container.bound(contract):
                self._container.register(provider)

    def _prepare_logger(self, logger_conf_path: str, logger_name: str):
        with open(logger_conf_path, "rb") as f:
            content = f.read()
            data = yaml.safe_load(content)
            dictConfig(data)
        self._container.register(NamedLoggerProvider(logger_name))

    def container(self) -> Container:
        return self._container

    def destroy(self) -> None:
        self._container.destroy()
        del self._container
