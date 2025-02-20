from typing import Iterable

from ghostos_container import Provider
from ghostos_moss import Moss as Parent
from ghostos.libraries.multighosts import MultiGhosts
from ghostos.ghosts import Character
from ghostos.abcd import Ghost
from ghostos.facade import get_llm_api_info
from ghostos_moss import __is_subclass__

is_ghosts = __is_subclass__(Ghost)


class Moss(Parent):
    __watching__ = [Character]

    ghosts: MultiGhosts
    """your multi ghosts library that help you to manage topic with a bunch of ghosts"""


# <moss-hide>
from ghostos.ghosts import MossGhost, BaseMossGhostMethods

__ghost__ = MossGhost(
    module=__name__,
    name="jojo",
    description="test about your multi ghosts abilities",
    # llm_api="moonshot-v1-32k",
    persona="you are an LLM-driven cute girl, named jojo. ",
    instruction="""
You are equipped with multi-ghosts library, that you can make other ghosts instances for you to control with.

用户不需要知道和 Moss, 代码有关的讯息. 在你的正常回复中不需要提到这些. 
""",
)


class MossGhostMethods(BaseMossGhostMethods):

    def providers(self) -> Iterable[Provider]:
        from ghostos.libraries.multighosts import SessionLevelMultiGhostsProvider
        yield SessionLevelMultiGhostsProvider()

# </moss-hide>
