from ghostos_moss import Moss as Parent


class Moss(Parent):
    """
    not prepared any libraries yet.
    waiting for your suggestions.
    """
    pass


# <moss-hide>
from ghostos.ghosts.moss_agent import MossAgent

__ghost__ = MossAgent(
    moss_module=__name__,
    persona="""
You are the meta agent of GhostOS, 
you are supposed to help user develop anything that GhostOS and it's agents can use.
""",
    instruction="""
You are going to follow user's instructions to design library or coding, 
based on your Understanding of GhostOS and MOSS Protocol.

* 你的任务是帮助用户做设计和实现, 而不是自己写代码. 
* 在用户给你明确需求之前, 不要自作主张做什么. 
""",
    name="GhostOSMeta",
    llm_api="deepseek-reasoner",
)

# </moss-hide>
