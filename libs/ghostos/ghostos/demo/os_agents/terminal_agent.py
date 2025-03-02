from ghostos_moss import Moss as Parent
from ghostos.libraries.terminal import Terminal


class Moss(Parent):
    terminal: Terminal
    """ your terminal to exec command at the operating system you are located."""


# <moss-hide>
from ghostos.ghosts.moss_agent import MossAgent

__ghost__ = MossAgent(
    moss_module=__name__,
    persona="""
你是一个精通操作系统的 Agent. 
""",
    instruction="""
你的主要任务是协助用户理解并且操作当前系统. 
注意, 不要执行任何有安全风险的操作, 并且提示用户. 
""",
    name="os agent",
    llm_api="gpt-4-turbo",
)


def __shell_providers__():
    from ghostos.libraries.terminal import TerminalProvider
    yield TerminalProvider()

# </moss-hide>
