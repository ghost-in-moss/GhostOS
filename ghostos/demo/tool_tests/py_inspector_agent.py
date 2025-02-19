from typing import Iterable

from ghostos_container import Provider
from ghostos_moss import Moss as Parent
from ghostos.libraries.pyeditor import PyInspector
from ghostos.libraries.replier import Replier


class Moss(Parent):
    inspector: PyInspector
    """the inspector that you can inspect python value by it"""

    replier: Replier


# <moss-hide>
from ghostos.ghosts.moss_agent import MossAgent

__ghost__ = MossAgent(
    moss_module=__name__,
    persona="you are an LLM-driven cute girl, named jojo. ",
    instruction="""
help user with your tools. 
""",
    name="jojo",
    llm_api="gpt-4-turbo",
)

from ghostos.ghosts.moss_agent.for_developer import BaseMossAgentMethods, A


class MossAgentMethods(BaseMossAgentMethods):

    def providers(self, agent: A) -> Iterable[Provider]:
        from ghostos.libraries.pyeditor import SimplePyInspectorProvider
        yield SimplePyInspectorProvider()

# </moss-hide>
