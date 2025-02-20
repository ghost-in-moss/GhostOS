from typing import Iterable

from ghostos_container import Provider
from ghostos_moss import Moss as Parent
from ghostos.libraries.memo import Memo


class Moss(Parent):
    memo: Memo
    """your memo useful to record values and memories, and read them by code"""


# <moss-hide>
from ghostos.ghosts.moss_ghost import MossGhost, BaseMossGhostMethods

__ghost__ = MossGhost(
    module=__name__,
    name="memo_agent",
    llm_api="gpt-4-turbo",
    description="test about memo tool using",
)


class MossGhostMethods(BaseMossGhostMethods):

    def providers(self) -> Iterable[Provider]:
        from ghostos.libraries.memo import SessionMemoProvider
        yield SessionMemoProvider("memo")

# </moss-hide>
