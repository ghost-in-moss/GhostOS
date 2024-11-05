from typing import Optional, ClassVar, Dict

from ghostos.core.ghosts import Ghost, GhostConf, Workspace, Shell
from ghostos.core.messages import Stream
from ghostos.core.session import GoProcess, GoTaskStruct
from ghostos.contracts.logger import LoggerItf
from ghostos.contracts.configs import Configs, YamlConfig

from ghostos.entity import EntityMeta
from ghostos.framework.shells import EmptyShell
from ghostos.framework.ghostos.basic import BasicGhostOS
from ghostos.framework.ghosts import DemoGhostConf, DemoGhost
from pydantic import Field


class DemoGhostOSConf(YamlConfig):
    relative_path: ClassVar[str] = "ghosts.yml"
    ghosts: Dict[str, EntityMeta] = Field(default_factory=dict, description="ghost conf entity metas, key is ghost id")


class DemoGhostOS(BasicGhostOS):

    def _on_initialized(self):
        configs = self.container().force_fetch(Configs)
        ghosts_confs = configs.get(DemoGhostOSConf)
        self._ghosts_metas = ghosts_confs.ghosts

    def make_ghost(
            self, *,
            upstream: Stream,
            process: GoProcess,
            task: Optional[GoTaskStruct] = None,
            task_id: Optional[str] = None,
    ) -> Ghost:
        conf = self._entity_factory.force_new_entity(process.ghost_meta, GhostConf)
        return self._make_ghost_instance(conf, upstream, process, task, task_id)

    def register(self, ghost_conf: GhostConf) -> None:
        ghost_id = ghost_conf.identifier().id
        self._ghosts_metas[ghost_id] = ghost_conf.to_entity_meta()

    def _make_ghost_instance(
            self,
            conf: GhostConf,
            upstream: Stream,
            process: GoProcess,
            task: Optional[GoTaskStruct] = None,
            task_id: Optional[str] = None,
    ) -> Ghost:
        if isinstance(conf, DemoGhostConf):
            return DemoGhost(
                conf=conf,
                container=self.container(),
                entity_factory=self._entity_factory,
                workspace=self.container().force_fetch(Workspace),
                shell=self._make_shell(conf),
                process=process,
                upstream=upstream,
                task=task,
                task_id=task_id,
            )
        else:
            raise NotImplementedError(f"GhostOS {conf} is not supported yet.")

    def _make_shell(self, ghost_conf: GhostConf) -> Shell:
        return EmptyShell()

    def on_error(self, error: Exception) -> bool:
        logger = self.container().force_fetch(LoggerItf)
        logger.error(str(error))
        return True

    def get_ghost_meta(self, ghost_id: str) -> Optional[EntityMeta]:
        if ghost_id in self._ghosts_metas:
            return self._ghosts_metas[ghost_id]
        return None
