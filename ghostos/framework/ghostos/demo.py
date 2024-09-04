from typing import Optional, ClassVar, Dict, List

from ghostos.container import Provider
from ghostos.core.ghosts import Ghost, GhostConf, Workspace, Shell
from ghostos.core.messages import Stream
from ghostos.core.session import Process, Task
from ghostos.contracts.logger import LoggerItf
from ghostos.contracts.configs import Configs, YamlConfig

from ghostos.entity import EntityMeta
from ghostos.framework.shells import EmptyShell
from ghostos.framework.ghostos.basic import BasicGhostOS
from ghostos.framework.ghosts import SimpleGhostConf, SimpleGhost
from pydantic import Field


class DemoGhostConfig(YamlConfig):
    relative_path: ClassVar[str] = "ghosts.yml"
    ghosts: Dict[str, EntityMeta] = Field(default_factory=dict, description="ghost conf entity metas, key is ghost id")


class DemoGhostOS(BasicGhostOS):

    def _on_initialized(self):
        configs = self.container().force_fetch(Configs)
        ghosts_conf = configs.get(DemoGhostConfig)
        self._ghosts_conf = ghosts_conf

    def make_ghost(
            self, *,
            upstream: Stream,
            process: Process,
            task: Optional[Task] = None,
            task_id: Optional[str] = None,
    ) -> Ghost:
        conf = self._entity_factory.force_new_entity(process.ghost_meta, GhostConf)
        return self._make_ghost_instance(conf, upstream, process, task, task_id)

    def _make_ghost_instance(
            self,
            conf: GhostConf,
            upstream: Stream,
            process: Process,
            task: Optional[Task] = None,
            task_id: Optional[str] = None,
    ) -> Ghost:
        if isinstance(conf, SimpleGhostConf):
            return SimpleGhost(
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
        if ghost_id in self._ghosts_conf:
            return self._ghosts_conf[ghost_id]
        return None
