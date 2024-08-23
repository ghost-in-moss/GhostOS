from typing import Optional
from ghostiss.core.moss.aifunc import AIFunc, AIFuncResult, AIFuncCtx
from ghostiss.core.moss import Moss as Parent
from pydantic import Field


class AgentFunc(AIFunc):
    """
    agent func that act like an agent
    """
    instruction: str = Field(description="raw instruction for the func")


class AgentFuncResult(AIFuncResult):
    """
    the result that follow the agent func instruction
    """
    result: str = Field(description="result of the func")
    ok: bool = Field(description="if the func is handled successfully")


__result__: Optional[AgentFuncResult] = None


class Moss(Parent):
    manager: AIFuncCtx
    """useful to run AIFunc"""


# <moss>

baseline_case = AgentFunc(
    instruction="please tell me 1.1234 * 2.325 equals?"
)


def __aifunc_instruction__(fn: AgentFunc) -> str:
    return fn.instruction

# </moss>
