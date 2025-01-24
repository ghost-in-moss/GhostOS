from ghostos.core.moss import Moss as Parent
from ghostos.libraries.terminal import Terminal


class Moss(Parent):
    terminal: Terminal
    """ your terminal to exec command at the operating system you are located."""


# <moss-hide>
from ghostos.ghosts.moss_agent import MossAgent

__ghost__ = MossAgent(
    moss_module=__name__,
    persona="""
你是一个精通 Ubuntu 系统的 Agent. 
""",
    instructions="""
你的主要任务是协助用户理解并且操作当前系统. 
""",
    name="Ubuntu Agent",
    llm_api="deepseek-chat",
)


def __shell_providers__():
    from ghostos.libraries.terminal import UbuntuTerminalProvider
    yield UbuntuTerminalProvider(safe_mode=True)

# </moss-hide>
