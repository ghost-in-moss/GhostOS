from ghostos.core.moss import Moss as Parent
from ghostos.core.ghosts import Replier


class Moss(Parent):
    replier: Replier


# <moss>  the content between <moss> mark are not visible in the prompt for LLM


# todo: can define a moss thought in a moss file
from ghostos.thoughts.moss_thought import MossThought

thought = MossThought(
    instruction="use speaker to ",
    moss_modulename=__name__,
    llm_api_name="",
)

if __name__ == "__main__":
    from ghostos.prototypes.console import new_console_app

    new_console_app(__file__, 4).run_thought(thought, debug=True)

# </moss>
