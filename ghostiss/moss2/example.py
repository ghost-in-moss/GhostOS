
from ghostiss.moss2.abc import MOSS


# -- moss -- #

def __moss_prompt__() -> str:
    prompts.tree_sitter(MOSS).prompt


class MOSS:

    class Mindflow(ABC):
        pass

    def run_tool(self, arguments: dict) -> dict:
        pass

    mindflow: Mindflow




