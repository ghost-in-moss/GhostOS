from typing import Optional
from ghostos.core.moss.aifunc import AIFunc, AIFuncResult, AIFuncCtx
from ghostos.core.moss import Moss as Parent
from pydantic import Field


class AgentFunc(AIFunc):
    """
    agent func that act like an agent
    """
    pass


class AgentFuncResult(AIFuncResult):
    """
    the result that follow the agent func instruction
    """
    result: str = Field(description="response from the agent func")
    err: Optional[str] = Field(default=None, description="error message")


class Moss(Parent):
    ai_func_ctx: AIFuncCtx
    """useful to run AIFunc"""


# <moss>


baseline_case = AgentFunc()

# </moss>
