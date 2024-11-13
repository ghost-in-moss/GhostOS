from typing import Optional, Dict

from ghostos.core.abcd.concepts import GhostOS, Shell
from ghostos.core.runtime import GoProcesses, GoProcess
from ghostos.container import Container, Provider
from ghostos.contracts.configs import Configs, YamlConfig
from pydantic import BaseModel, Field
from .shell_impl import ShellImpl, ShellConf


class GhostOSConfig(YamlConfig):
    relative_path = "ghostos.yml"
    shells: Dict[str, ShellConf] = Field(
        description="the shell configurations",
    )


class GhostOSImpl(GhostOS):

    def __init__(
            self,
            container: Container,
    ):
        self._container = container
        self._processes = container.force_fetch(GoProcesses)
        self._configs = container.force_fetch(Configs)
        self._ghostos_config = self._configs.get(GhostOSConfig)

    def container(self) -> Container:
        return self._container

    def create_shell(
            self,
            name: str,
            shell_id: str,
            process_id: Optional[str] = None,
            *providers: Provider,
    ) -> Shell:
        if name not in self._ghostos_config.shells:
            raise NotImplementedError(f"Shell `{name}` not implemented")
        shell_conf = self._ghostos_config.shells[name]
        process = self._processes.get_process(shell_id)
        if process is None:
            process = GoProcess.new(shell_id=shell_id, process_id=process_id)
        elif process_id is not None and process.process_id != process_id:
            process = GoProcess.new(shell_id=shell_id, process_id=process_id)
        self._processes.save_process(process)

        # prepare container
        container = Container(parent=self._container)
        return ShellImpl(
            config=shell_conf,
            container=container,
            process=process,
            *providers,
        )
