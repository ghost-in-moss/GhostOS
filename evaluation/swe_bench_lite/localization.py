from typing import Optional, List
from ghostos.core.moss.aifunc import AIFunc, AIFuncResult, AIFuncCtx
from ghostos.core.moss import Moss as Parent
from pydantic import Field
from evaluation.swe_bench_lite.swe_task import SWETaskAIFunc, SWETaskAIFuncResult, SWEDebugTaskCtx


class AgentFn(AIFunc):
    """
    AIFunc that act like an agent
    """
    request: str = Field(description="raw request for the agent")


class AgentFnResult(AIFuncResult):
    """
    the result that follow the agent request
    """
    issue_files: List[str] = Field(description="the file paths that caused the issue")
    err: Optional[str] = Field(default=None, description="error message")


__result_type__ = AgentFnResult


class Moss(Parent):

    ai_func_ctx: AIFuncCtx
    """useful to run AIFunc"""


# <moss>


def __aifunc_instruction__(fn: AgentFn) -> str:
    return fn.request


example = AgentFn(
    request="Your task is localization issue files in a repository. "
            "First get the information of the swe bench task"
            "Then using git to checkout to the appropriate commit of the task, and checkout -b to create a new branch (might be a Git AIFunc)"
            "Then localize the file caused the issue (not mock, it might be a Localization(exploration and exploitation) AIFunc). "
            "If you realize some steps needs to utilizing AI to plan or implementation, create or utilize the AIFunc. "
            "You can create AIFunc by definition class outside of the `def main(moss)`"
)

# </moss>
