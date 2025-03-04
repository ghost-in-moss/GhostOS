from typing import Iterable, Dict, Any, List

from ghostos.abcd import Session, Thought
from ghostos_container import Provider
from ghostos_moss import Moss as Parent, MossRuntime
from ghostos.libraries.pyeditor import PyInspector, PyMI, PyModuleEditor
from ghostos.libraries.replier import Replier


class Moss(Parent):
    inspector: PyInspector
    """the inspector that you can inspect python value by it"""

    pymi: PyMI
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
    llm_api="deepseek-chat",
    persona="you are an LLM-driven cute girl, named jojo. ",
    instruction="""
You are able to edit python modules, helping user to edit them.
Notices: 
* 当你编辑的代码涉及你所没见过的理性时, 你需要先查看相关代码, 确保不会有类型错误. 
* 你生成的 Moss run 函数用户可以直接看到, 所以不要重复陈述这些代码. 
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

    def get_thought_chain(self, session: Session, runtime: MossRuntime) -> List[Thought]:
        # from ghostos.thoughts import SelfQuestionThought, NoticesThought
        from ghostos.core.runtime.events import EventTypes
        e = session.thread.get_current_event()
        if e.type == EventTypes.INPUT:
            return [
                #                 SelfQuestionThought(
                #                     question="""
                # 1. 本轮行动是否需要使用 moss 调用代码? (yes/no)
                # 2. 本轮行动如果需要调用代码, 是否所有涉及的类库, 变量类型已经清晰了 (yes/no).
                # 3. 如果有不清晰的地方, 是否要先查询哪些类库或变量的代码?
                # """,
                #                     llm_api_name=self.agent.llm_api,
                #                 ),
                #                 NoticesThought(
                #                     notices="如果你需要使用 moss 生成代码, 记得: 1. 不需要向用户描述这些代码, 用户可以看到. 2. 要调用 moss 工具"
                #
                #                 )
            ]
        else:
            return []

# </moss-hide>
