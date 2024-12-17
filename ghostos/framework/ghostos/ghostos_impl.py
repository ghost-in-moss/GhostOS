from typing import Optional, Dict, List

from ghostos.abcd import GhostOS, Shell
from ghostos.core.runtime import GoProcesses, GoProcess, GoThreads, GoTasks, EventBus
from ghostos.container import Container, Provider, Contracts, INSTANCE
from ghostos.contracts.configs import Configs, YamlConfig
from ghostos.contracts.modules import Modules
from ghostos.contracts.variables import Variables
from ghostos.contracts.workspace import Workspace
from ghostos.contracts.logger import LoggerItf, get_ghostos_logger
from pydantic import Field
from .shell_impl import ShellImpl, ShellConf

__all__ = ['GhostOS', "GhostOSImpl", "GhostOSConfig", "GhostOSProvider"]


class GhostOSConfig(YamlConfig):
    relative_path = "ghostos_conf.yml"
    shells: Dict[str, ShellConf] = Field(
        description="the shell configurations",
    )


class GhostOSImpl(GhostOS):
    contracts: Contracts = Contracts([
        GoProcesses,
        GoTasks,
        GoThreads,
        EventBus,
        LoggerItf,
        Configs,
        Modules,
        Variables,
        Workspace,
    ])

    def __init__(
            self,
            container: Container,
    ):
        self.contracts.validate(container)
        self._container = container
        self._processes = container.force_fetch(GoProcesses)
        self._configs = container.force_fetch(Configs)
        self._ghostos_config = self._configs.get(GhostOSConfig)

    @property
    def logger(self) -> LoggerItf:
        return get_ghostos_logger()

    def container(self) -> Container:
        return self._container

    def create_shell(
            self,
            name: str,
            *,
            shell_id: str = "",
            providers: Optional[List[Provider]] = None,
            process_id: Optional[str] = None,
    ) -> Shell:
        if name not in self._ghostos_config.shells:
            shell_conf = ShellConf()
        else:
            shell_conf = self._ghostos_config.shells[name]
        if not shell_id:
            shell_id = name
        process = self._processes.get_process(shell_id)
        if process is None:
            process = GoProcess.new(shell_id=shell_id, process_id=process_id)
            self.logger.debug(f"Created shell `{shell_id}` process `{process_id}`")
        elif process_id is not None and process.process_id != process_id:
            process = GoProcess.new(shell_id=shell_id, process_id=process_id)
            self.logger.debug(f"Created shell `{shell_id}` new process `{process_id}`")
        else:
            self.logger.debug(f"get shell `{shell_id}` new process `{process.process_id}`")
        self._processes.save_process(process)

        # prepare container
        providers = providers or []
        return ShellImpl(
            config=shell_conf,
            container=self._container,
            process=process,
            providers=providers,
        )


class GhostOSProvider(Provider[GhostOS]):
    def singleton(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[INSTANCE]:
        return GhostOSImpl(con)
