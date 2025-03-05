from abc import ABC
from typing import Iterable

from ghostos_container import Provider

from ghostos.libraries.project import contracts
from ghostos.libraries.terminal import Terminal
from ghostos_moss import Moss as Parent


class Moss(Parent, ABC):
    """
    管理一个项目的工具界面.
    """
    __watching__ = [contracts]

    project: contracts.ProjectManager
    """ manage the project"""

    terminal: Terminal
    """interact with terminal"""


# <moss-hide>
from ghostos.ghosts.moss_ghost import MossGhost, BaseMossGhostMethods

__ghost__ = MossGhost(
    name="project-manager",
    module=__name__,
)


class MossGhostMethods(BaseMossGhostMethods):

    def providers(self) -> Iterable[Provider]:
        from ghostos.libraries.project import ProjectManagerProvider
        from ghostos.libraries.terminal import TerminalProvider
        yield ProjectManagerProvider()
        yield TerminalProvider()

# </moss-hide>
