from typing import Optional, List, Any

from ghostos.core.aifunc import AIFuncCtx
from ghostos.core.moss import Moss as Parent
from ghostos.core.aifunc import AIFunc, AIFuncResult
from pydantic import BaseModel, Field
from evaluation.swe_bench_lite.tools.file_content_operations import FileContentOperations
from evaluation.swe_bench_lite.ai_funcs.swe_task_manager import SWEDebugTaskCtx
from evaluation.swe_bench_lite.ai_funcs.file_explorer import FileExplorerAIFunc, FileExplorerAIFuncResult
from evaluation.swe_bench_lite.base.culprit_file_part import CulpritFilePart

from ghostos.core.moss.decorators import cls_source_code


@cls_source_code()
class ExplorationProjectAIFuncResult(AIFuncResult):
    found_culprits: Optional[List[CulpritFilePart]] = Field(..., description="The final culprit file parts, it can be empty if not found")
    cost_steps: int = Field(..., description="The cost steps to find the culprit files")
    confidence_percentage_requirement: int = Field(..., description="The requirement of least confidence percentage of the culprit file part")
    confidence_percentage_of_current_plan: int = Field(..., description="The confidence percentage of the current plan")


class ExplorationProjectAIFunc(AIFunc):
    """
    write a plan (contains AI functions) to explore & exploit the target repository, to localize the issue files
    It should be a plan with loop or MCTS exploration algorithm that can be executed by AI functions
    These variables must be filled with value
    """
    max_steps: int = Field(default=20, description="the expectation max steps to localize the issue files")
    cur_step: int = Field(default=0, description="the current step of the exploration")
    thoughts: str = Field(default="", description="the brief plan of the exploration")
    debug_task_ctx: Any = Field(..., description="the debug task context")
    # parent_plan: Optional["ExplorationProjectAIFunc"] = Field(default=None, description="the parent plan of the exploration")


class Moss(Parent):

    ai_func_ctx: AIFuncCtx
    """useful to run AIFunc"""


# <moss>

def __aifunc_instruction__(fn: ExplorationProjectAIFunc) -> str:
    return (f"ExplorationProjectAIFunc input vals: max_steps: {fn.max_steps}, cur_step: {fn.cur_step}, "
            f"thoughts: {fn.thoughts}, debug_task_ctx: {fn.debug_task_ctx}. You should return an ExplorationProjectAIFuncResult object。"
            f"Before you return the culprit file parts, you should use the read_file method or FileExplorerAIFunc, you can also using multi-run or MCTS to explore the key directory. ")

# </moss>
