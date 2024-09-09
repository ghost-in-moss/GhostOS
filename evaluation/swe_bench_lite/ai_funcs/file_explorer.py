from typing import Optional, List, Any

from ghostos.core.moss.aifunc import AIFuncCtx
from ghostos.core.moss import Moss as Parent
from ghostos.core.moss.aifunc import AIFunc, AIFuncResult
from pydantic import BaseModel, Field
from evaluation.swe_bench_lite.tools.file_content_operations import FileContentOperations
from evaluation.swe_bench_lite.ai_funcs.swe_task_manager import SWEDebugTaskCtx
from evaluation.swe_bench_lite.base.culprit_file_part import CulpritFilePart

from ghostos.core.moss.decorators import cls_source_code


@cls_source_code()
class FileExplorerAIFuncResult(AIFuncResult):
    found_culprits: Optional[List[CulpritFilePart]] = Field(..., description="The final culprit file parts, it can be empty if not found")
    confidence_percentage: Optional[int] = Field(..., description="The confidence percentage of the found_culprits is the true culprit")
    file_outline: Optional[str] = Field(default="", description="the important key information or clue, or summarize of the file")


class FileExplorerAIFunc(AIFunc):
    """
    explore & exploit the target file by reading and reasoning the file content
    """
    cur_object: str = Field(default="", description="current object to explore")

    debug_task_ctx: Any = Field(..., description="the debug task context")
    # parent_plan: Optional["ExplorationProjectAIFunc"] = Field(default=None, description="the parent plan of the exploration")

    file_content: str = Field(description="the content of the file")


class Moss(Parent):

    ai_func_ctx: AIFuncCtx
    """useful to run AIFunc"""

# <moss>

def __aifunc_instruction__(fn: FileExplorerAIFunc) -> str:
    return (f"Your current task is {fn.cur_object}, you should use the read_file method at first, culprit parts might exist in this then thought step by step to find clues about the issue. content of file: {fn.file_content}")

# </moss>
