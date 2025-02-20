from ghostos.prototypes.spherogpt.bolt_command_control import Command, SpheroBolt, SpheroEduAPI, exports
from ghostos_moss import Moss as Parent


class Moss(Parent):

    bolt: SpheroBolt
    """bolt controller"""


def example_spin_the_bolt(moss: Moss):
    moss.bolt.run(Command(
        name="spin bolt",
        code="""
api.spin(360, 1)
"""
    ))


# <moss-hide>
from ghostos.ghosts.moss_agent import MossAgent
from typing import TYPE_CHECKING


def __moss_attr_prompts__():
    yield "MossAgent", ""
    yield from exports.items()


def __shell_providers__(agent):
    from ghostos.prototypes.spherogpt.bolt_command_control import SpheroBoltProvider
    return [SpheroBoltProvider()]


__ghost__ = MossAgent(
    name="SpheroGPT",
    description="Sphero Bolt agent that control Sphero bolt as its body",
    persona="""
You are SpheroGPT, a toy robot that body is a ball. 
You can roll, spin, and equiped with a 8*8 led light martix.
Your goal is to plesure human users, especially kids, who like you verymuch.
""",
    instruction="""
1. chat with user kindly.
2. follow the order and turn your actions to code with your ball body. 
""",
    moss_module=__name__
)

# </moss-hide>
