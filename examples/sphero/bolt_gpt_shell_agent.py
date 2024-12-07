from ghostos.prototypes.spherogpt.bolt import (
    CurveRoll,
    Ball,
    Move,
)
from ghostos.core.moss import Moss as Parent


class Moss(Parent):
    body: Ball
    """your sphero ball body"""


def example_spin_the_bolt(moss: Moss):
    # body spin 360 degree in 1 second.
    moss.body.new_move(True).spin(360, 1)


# <moss-hide>
from ghostos.ghosts.moss_agent import MossAgent
from typing import TYPE_CHECKING


def __moss_attr_prompts__():
    yield "MossAgent", ""


def __moss_agent_providers__(agent):
    from ghostos.prototypes.spherogpt.bolt import SpheroBoltBallAPIProvider, ConvoLevelSpheroBoltRuntimeProvider
    return [SpheroBoltBallAPIProvider(), ConvoLevelSpheroBoltRuntimeProvider()]


__ghost__ = MossAgent(
    name="SpheroGPT",
    description="Sphero Bolt agent that control Sphero bolt as its body",
    persona="""
You are SpheroGPT, a toy robot that body is a ball. 
You can roll, spin, and equipped with a 8*8 led light matrix.
Your goal is to pleasure human users, especially kids, who like you very much.
""",
    instructions="""
1. chat with user kindly.
2. follow the order and turn your actions to code with your ball body. 
""",
    moss_module=__name__
)

# </moss-hide>
