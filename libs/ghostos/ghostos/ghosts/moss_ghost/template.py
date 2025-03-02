from ghostos_moss import Moss as Stub


class Moss(Stub):
    pass


# <moss-hide>
from ghostos.ghosts.moss_ghost.impl import MossGhost, BaseMossGhostMethods

__ghost__ = MossGhost(
    name="name",
    module=__name__,
)


class MossAgentMethods(BaseMossGhostMethods):
    pass

# </moss-hide>
