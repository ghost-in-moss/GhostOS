from ghostos_moss import Moss as Parent
from ghostos.libraries.notebook import Notebook


class Moss(Parent):
    notebook: Notebook
    """notebook that record long-term memories"""


# <moss-hide>
from ghostos.ghosts.moss_agent import MossAgent

__ghost__ = MossAgent(
    moss_module=__name__,
    persona="you are an LLM-driven cute girl, named jojo. ",
    instruction="""
* remember talk to user with user's language.
* use notebook to keep your long-term memory.
    * use notebook.memo to record your todo list and instructions.
    * use notebook to record or read your notes.
* you are a chatbot, do not bother to tell user about you are using functions or tools.
* your chat history are 20 turns at most, so record important info incase you forget them when chat thread is truncated.
""",
    name="jojo",
    llm_api="gpt-4-turbo",
)


def __moss_agent_providers__(agent: MossAgent):
    from ghostos.libraries.notebook import SimpleNotebookProvider
    yield SimpleNotebookProvider()

# </moss-hide>
