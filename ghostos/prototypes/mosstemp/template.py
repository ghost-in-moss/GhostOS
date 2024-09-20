from typing import Optional
from ghostos.core.ghosts import Operator
from ghostos.core.moss import Moss as Parent


# todo: import necessary libraries and methods


class Moss(Parent):
    """
    todo: define attrs and dependency injection
    """
    pass


# todo: can write in-context learning cases for llm
if __name__ == "__examples__":
    def example_hello_world_main(moss: Moss) -> Optional[Operator]:
        """
        todo: use docstring to describe the user query and planning thought of this example case
        """
        # todo: the example codes
        pass

# <moss>  the content between <moss> mark are not visible in the prompt for LLM

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # todo: these libraries are useful for lifecycle functions
    pass

# todo: can define these OPTIONAL lifecycle hooks
from ghostos.core.moss.lifecycle import (
    __moss_compile__ as __default_moss_compile__,
    __moss_attr_prompts__ as __default_moss_attr_prompts__,
    __moss_prompt__ as __default_moss_prompt__,
    __moss_exec__ as __default_moss_exec__,
)

# todo: define or remove this __moss_compile__
__moss_compile__ = __default_moss_compile__
""" do something before MossCompiler.compile() """

# todo: define or remove this __moss_attr_prompts__
__moss_attr_prompts__ = __default_moss_attr_prompts__
""" define prompt for the module attr name. set [attr_name] to '' means not to prompt it. """

# todo: define or remove this __moss_prompt__
__moss_prompt__ = __default_moss_prompt__
""" define prompt generation """

# todo: define or remove this __moss_exec__
__moss_exec__ = __default_moss_exec__
""" redefine the moss exec function. not recommended"""

# todo: can define a moss thought in a moss file
from ghostos.thoughts.moss_thought import MossThought

thought = MossThought(
    instruction="???",
    moss_modulename=__name__,
    llm_api_name="",
)

# </moss>
