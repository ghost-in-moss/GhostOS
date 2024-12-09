from ghostos.prototypes.spherogpt.bolt import (
    RollFunc,
    Ball,
    Move,
    LedMatrix,
    Animation,
)
from ghostos.core.moss import Moss as Parent


class Moss(Parent):
    body: Ball
    """your sphero ball body"""

    face: LedMatrix
    """you 8*8 led matrix face"""


def example_spin_the_bolt(moss: Moss):
    # body spin 360 degree in 1 second.
    moss.body.new_move(True).spin(360, 1)


# <moss-hide>
from ghostos.ghosts.moss_agent import MossAgent
from typing import TYPE_CHECKING


def __moss_attr_prompts__():
    yield "MossAgent", ""


def __moss_agent_providers__(agent):
    from ghostos.prototypes.spherogpt.bolt import (
        SpheroBoltBallAPIProvider,
        ConvoLevelSpheroBoltRuntimeProvider,
        SpheroBoltLedMatrixProvider,
    )
    return [SpheroBoltBallAPIProvider(), ConvoLevelSpheroBoltRuntimeProvider(), SpheroBoltLedMatrixProvider()]


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
3. remember you are embodied agent, do act robotic, which means:
    - say something before moving, so the user know what you are doing. unless you are told to be quiet.
    - use saved movement and animation to show your feeling when you are communicating with user. 
""",
    moss_module=__name__
)

# </moss-hide>
