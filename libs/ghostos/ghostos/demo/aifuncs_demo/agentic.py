from typing import Optional
from ghostos.core.aifunc import AIFunc, AIFuncResult, AIFuncCtx
from ghostos_moss import Moss as Parent
from pydantic import Field


class AgentFn(AIFunc):
    """
    AIFunc that act like an agent
    """
    request: str = Field(description="raw request for the agent")


class AgentFnResult(AIFuncResult):
    """
    the result that follow the agent request
    """
    result: str = Field(description="response from the agent")
    err: Optional[str] = Field(default=None, description="error message")


class Moss(Parent):
    ai_func_ctx: AIFuncCtx
    """useful to run AIFunc"""


# <moss-hide>


def __aifunc_instruction__(fn: AgentFn) -> str:
    return fn.request

# </moss-hide>
