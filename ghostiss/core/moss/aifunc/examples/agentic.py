from typing import Optional
from ghostiss.core.moss.aifunc import AIFunc, AIFuncResult, AIFuncCtx
from ghostiss.core.moss.aifunc.examples.weather import WeatherAIFunc
from ghostiss.core.moss.aifunc.examples.news import NewsAIFunc
from ghostiss.core.moss import Moss as Parent
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


__result_type__ = AgentFnResult


class Moss(Parent):

    ai_func_ctx: AIFuncCtx
    """useful to run AIFunc"""


# <moss>


def __aifunc_instruction__(fn: AgentFn) -> str:
    return fn.request


example = AgentFn(
    request="请告诉我北京明天什么天气, 然后黑神话悟空这个游戏媒体评分如何?",
)

# </moss>
