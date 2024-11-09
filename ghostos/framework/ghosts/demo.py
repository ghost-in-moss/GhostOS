from typing import Optional, List
from ghostos.identifier import Identifier
from ghostos.core.ghosts import GhostConf, Shell, Workspace
from ghostos.core.runtime import GoProcess, GoTaskStruct
from ghostos.contracts.modules import Modules
from ghostos.core.messages import Stream
from ghostos.framework.ghosts.basic import BasicGhost, InputsPipe
from ghostos.framework.streams import EmptyStream
from ghostos.framework.shells import EmptyShell
from ghostos.container import Container, Provider
from ghostos.entity import EntityMeta, EntityFactory
from ghostos.helpers import import_from_path
from pydantic import Field

__all__ = ['DemoGhost', 'DemoGhostConf']


class DemoGhostConf(GhostConf):
    """
    configration of simple ghost implementation
    """

    id: str = Field(description="id of the ghost")
    name: str = Field(description="name of the ghost")
    description: str = Field(default="", description="description of the ghost")

    # prompt
    meta_prompt: str = Field(description="raw meta prompt")

    # meta
    thought_meta: EntityMeta = Field(description="root thought meta entity")

    # importing
    input_pipes: List[str] = Field(default_factory=list, description="import path for input pipes")
    providers: List[str] = Field(default_factory=list, description="import path for providers")

    # system conf
    max_operators_run: int = Field(default=10, description="max operators run")

    def identifier(self) -> Identifier:
        return Identifier(
            id=self.id,
            name=self.name,
            description=self.description,
        )

    def root_thought_meta(self) -> EntityMeta:
        return self.thought_meta


class DemoGhost(BasicGhost):
    """
    simple implementation of a ghost
    """

    def __init__(
            self,
            conf: DemoGhostConf,
            container: Container,
            entity_factory: EntityFactory,
            workspace: Workspace,
            process: GoProcess,
            upstream: Optional[Stream] = None,
            shell: Optional[Shell] = None,
            task: Optional[GoTaskStruct] = None,
            task_id: Optional[str] = None,
    ):
        self._conf = conf
        shell = shell if shell is None else EmptyShell()
        upstream = upstream if upstream else EmptyStream()
        modules = container.force_fetch(Modules)

        # importing
        for provider_path in conf.providers:
            provider = import_from_path(provider_path, modules.import_module)
            if not isinstance(provider, Provider):
                raise ValueError(f"provider {provider_path} is not an instance of {Provider}")
            self.providers.append(provider)

        for input_pipe_path in conf.input_pipes:
            pipe = import_from_path(input_pipe_path, modules.import_module)
            if not issubclass(pipe, InputsPipe):
                raise ValueError(f"pipe {input_pipe_path} is not an subclass of {InputsPipe}")
            self.inputs_pipes.append(pipe)

        super().__init__(
            conf=conf,
            container=container,
            shell=shell,
            workspace=workspace,
            entity_factory=entity_factory,
            upstream=upstream,
            process=process,
            task=task,
            task_id=task_id,
            max_operator_runs=conf.max_operators_run,
        )

    def meta_prompt(self) -> str:
        return self._conf.meta_prompt

    def conf(self) -> DemoGhostConf:
        return self._conf
