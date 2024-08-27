from typing import Optional
from ghostos.core.moss.aifunc import AIFunc, AIFuncResult, AIFuncCtx
from ghostos.core.moss import Moss as Parent
from pydantic import Field


class AgentFunc(AIFunc):
    """
    agent func that act like an agent
    """
    instruction: str = Field(description="raw instruction for the agent func")


class AgentFuncResult(AIFuncResult):
    """
    the result that follow the agent func instruction
    """
    result: str = Field(description="response from the agent func")
    err: Optional[str] = Field(default=None, description="error message")


__result_type__ = AgentFuncResult


class Moss(Parent):
    ai_func_ctx: AIFuncCtx
    """useful to run AIFunc"""


# <moss>


def __aifunc_instruction__(fn: AgentFunc) -> str:
    return fn.instruction


baseline_case = AgentFunc(
    instruction="please tell me 1.1234 * 2.325 equals?"
)

# </moss>
