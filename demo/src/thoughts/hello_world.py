from typing import Optional
from ghostos.core.ghosts import Operator
from ghostos.core.moss import Moss as Parent, attr
from demo.src.libraries.mocks.speak import Speak


class Moss(Parent):
    speaker: Speak


# <moss>  the content between <moss> mark are not visible in the prompt for LLM

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ghostos.core.moss import MossCompiler, MossRuntime


def __moss_compile__(compiler: "MossCompiler") -> "MossCompiler":
    from demo.src.libraries.mocks.speak import SpeakImpl
    from ghostos.core.session import Session
    # for test, inject speaker impl
    session = compiler.container().force_fetch(Session)
    compiler.injects(speaker=SpeakImpl(session))
    return compiler


# todo: can define a moss thought in a moss file
from ghostos.framework.thoughts.moss import MossThought
from ghostos.prototypes.console import run_demo_thought

thought = MossThought(
    name="helloworld_test",
    description="",
    instruction="use speaker to ",
    moss_modulename=__name__,
    llm_api_name="",
)

if __name__ == "__main__":
    run_demo_thought(thought, debug=True)

# </moss>
