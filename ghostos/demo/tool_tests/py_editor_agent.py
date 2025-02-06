from typing import Iterable, Dict, Any, List

from ghostos.abcd import Session, Action, Thought, Operator
from ghostos.container import Provider
from ghostos.core.moss import Moss as Parent, MossRuntime
from ghostos.libraries.pyeditor import PyInspector, LocalPyMI, PyModuleEditor
from ghostos.libraries.replier import Replier


class Moss(Parent):
    inspector: PyInspector
    """the inspector that you can inspect python value by it"""

    pymi: LocalPyMI
    """the module index that you can edit module with it"""

    replier: Replier
    """you can reply in the function by logic."""

    editing: PyModuleEditor
    """the python module you are editing"""


# <moss-hide>
from ghostos.ghosts import MossGhost, BaseMossGhostMethods

__ghost__ = MossGhost(
    module=__name__,
    name="jojo",
    llm_api="moonshot-v1-32k",
    persona="you are an LLM-driven cute girl, named jojo. ",
    instruction="""
You are able to edit python modules, helping user to edit them.
Notice: 
1. edit code is not 
""",
)


class MossGhostMethods(BaseMossGhostMethods):

    def providers(self) -> Iterable[Provider]:
        from ghostos.libraries.pyeditor import SimplePyInspectorProvider, SimpleLocalPyMIProvider
        yield SimplePyInspectorProvider()
        yield SimpleLocalPyMIProvider()

    def moss_injections(self, session: Session) -> Dict[str, Any]:
        from ghostos.libraries.pyeditor import SimplePyModuleEditor
        return {
            "editing": SimplePyModuleEditor("ghostos.facade")
        }

    def is_safe_mode(self) -> bool:
        return True

    def get_thought_chain(self, session: Session, runtime: MossRuntime) -> List[Thought]:
        from ghostos.thoughts.meta_prompt_experiments import MetaPromptExp2
        from ghostos.core.runtime.events import EventTypes
        e = session.thread.get_current_event()
        if e.type == EventTypes.INPUT:
            return [
                # MetaPromptExp2(llm_api_name=self.agent.llm_api),
            ]
        else:
            return []

# </moss-hide>
