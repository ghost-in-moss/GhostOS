from typing import Optional, List, Any

from ghostos.core.aifunc import AIFunc, AIFuncResult
from pydantic import BaseModel, Field
from evaluation.swe_bench_lite.tools.file_reader import FileReader
from evaluation.swe_bench_lite.ai_funcs.swe_task import SWEDebugTaskCtx

from ghostos.core.moss.decorators import cls_source_code

@cls_source_code()
class CulpritFilePart(BaseModel):
    file_path: str = Field(..., description="The path of the culprit file")
    culprit_reason: str = Field(..., description="The reason why the part is the culprit")
    culprit_line_start: int = Field(..., description="The start line of the culprit")
    culprit_line_end: int = Field(..., description="The end line of the culprit")
    confidence_percentage: int = Field(..., description="The confidence percentage of the culprit")


@cls_source_code()
class ExplorationProjectAIFuncResult(AIFuncResult):
    found_culprits: Optional[List[CulpritFilePart]] = Field(..., description="The final culprit file parts, it can be empty if not found")
    cost_steps: int = Field(..., description="The cost steps to find the culprit files")
    confidence_percentage_requirement: int = Field(..., description="The requirement of least confidence percentage of the culprit file part")
    confidence_percentage_of_current_plan: int = Field(..., description="The confidence percentage of the current plan")


__result_type__ = ExplorationProjectAIFuncResult

file_read_func = FileReader.read_file

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

# <moss>


def __aifunc_instruction__(fn: ExplorationProjectAIFunc) -> str:
    return (f"ExplorationProjectAIFunc input vals: max_steps: {fn.max_steps}, cur_step: {fn.cur_step}, "
            f"thoughts: {fn.thoughts}, debug_task_ctx: {fn.debug_task_ctx}")

# </moss>
