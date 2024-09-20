from typing import Optional, List
from ghostos.core.aifunc import AIFunc, AIFuncResult, AIFuncCtx
from ghostos.core.moss import Moss as Parent
from pydantic import Field
from evaluation.swe_bench_lite.ai_funcs.swe_task_manager import SWETaskAIFunc, SWETaskAIFuncResult, SWEDebugTaskCtx
from evaluation.swe_bench_lite.ai_funcs.project_explorer import ExplorationProjectAIFunc, ExplorationProjectAIFuncResult
from evaluation.swe_bench_lite.tools.repo_context_manager import RepositoryContextManager, PrepareRepositoryResult
from evaluation.swe_bench_lite.tools.directory_explorer import DirectoryExplorer



class AgentFn(AIFunc):
    """
    AIFunc that act like an agent
    """
    request: str = Field(default="", description="raw request for the agent")


class AgentFnResult(AIFuncResult):
    """
    the result that follow the agent request
    """
    issue_files: List[str] = Field(default=[], description="the file paths that caused the issue")
    err: Optional[str] = Field(default=None, description="error message")


class Moss(Parent): 

    ai_func_ctx: AIFuncCtx
    """useful to run AIFunc"""


# <moss>


def __aifunc_instruction__(fn: AgentFn) -> str:
    return fn.request


example = AgentFn(
    request="Your task is localization issue files in a repository. "
            "First get the information of the swe bench task"
            "Then using prepare the environment to debug the repository. "
            "Then localize the file caused the issue (not mock, it might be a Localization(exploration and exploitation) AIFunc). "
            "If you realize some steps needs to utilizing AI to plan or implementation, utilize the AIFunc. "
            "Task json file path: /home/llm/Project/PythonProjects/GhostOS/evaluation/swe_bench_lite/django_15347.json"
            "workspace path: /home/llm/Project/PythonProjects/workspace/django"
            # "You can create AIFunc by definition class outside of the `def main(moss)`"
)

# </moss>
