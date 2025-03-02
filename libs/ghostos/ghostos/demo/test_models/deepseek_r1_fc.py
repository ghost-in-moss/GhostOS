from ghostos.ghosts.moss_ghost import MossGhost
from ghostos_moss import Moss as Parent
from ghostos.libraries.replier import Replier


class Moss(Parent):
    replier: Replier


def plus(a: int, b: int) -> int:
    return a + b


# <moss-hide>
# the __ghost__ magic attr define a ghost instance
# so the script `ghostos web` or `ghostos console` can detect it
# and run agent application with this ghost.
__ghost__ = MossGhost(
    id=__name__,
    name="jojo",
    module=__name__,
    description="a chatbot for baseline test",
    persona="you are an LLM-driven cute girl, named jojo",
    instruction="remember talk to user with user's language. 如果用户说中文, 你的思考和回复都应该用中文. ",
    llm_api="deepseek-reasoner",
)
# </moss-hide>
