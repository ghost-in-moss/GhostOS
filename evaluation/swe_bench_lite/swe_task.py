from typing import Optional, List
from ghostiss.core.moss.aifunc import AIFunc, AIFuncResult
from pydantic import BaseModel, Field
from ghostiss.core.moss import Moss
from ghostiss.core.moss.decorators import cls_source_code

import logging
import json


class UnitTestInfo(BaseModel):
    test_method_name: str = Field(..., description="The name of the test method")
    test_class_name: str = Field(..., description="The name of the test class from repository content root")


@cls_source_code()
class SWEDebugTaskCtx(BaseModel):
    workspace_path: str = Field(..., description="The path of the root workspace")
    repo: str = Field(..., description="The target repository to debug")
    instance_id: str = Field(..., description="The id of the debug task")
    base_commit: str = Field(..., description="The base commit of the repository to debug")
    issue_info: str = Field(..., description="The issue statement of the bug")
    supplementary_issue_info: str = Field(..., description="The discussion and supplementary text of the bug")
    passed_tests: List[UnitTestInfo] = Field(..., description="The list of passed unit tests before the fix")
    # environment_setup_commit: str = Field(..., description="The commit used to environment setup")


def get_swe_debug_task_ctx(task_json_path: str="/home/llm/Project/PythonProjects/ghostiss/evaluation/swe_bench_lite/django_15347.json",
                           workspace_path: str="/home/llm/Project/PythonProjects/workspace") -> SWEDebugTaskCtx:
    with open(task_json_path, 'r') as f:
        task_json = json.load(f)

    try:
        # parse the task json to get the task context
        repo_name = task_json['repo'].split('/')[-1]
        logging.info(f"get swe debug task, repo_name: {repo_name}")

        instance_id = task_json['instance_id']
        logging.info(f"get swe debug task, instance_id: {instance_id}")

        passed_tests = [UnitTestInfo(**test_info) for test_info in task_json['PASS_TO_PASS']]

        task_ctx = SWEDebugTaskCtx(
            workspace_path=workspace_path,
            repo=repo_name,
            instance_id=instance_id,
            base_commit=task_json['base_commit'],
            issue_info=task_json['problem_statement'],
            supplementary_issue_info=task_json['hints_text'],
            passed_tests=passed_tests
        )
    except Exception as e:
        logging.error(f"Failed to get task context: {e}")
        raise e

    return task_ctx


class SWETaskAIFuncResult(AIFuncResult):
    """
    news result
    """
    results: SWEDebugTaskCtx = Field(default_factory=SWEDebugTaskCtx, description="the detailed information of the swe debug task")


__result_type__ = SWETaskAIFuncResult


# <moss>

class SWETaskAIFunc(AIFunc):
    """
    get detailed information about the swe debug task
    """
    instruction: str = Field(description="the instruction of the task, to get the detailed information of the swe debug task")


def __aifunc_instruction__(fn: SWETaskAIFunc) -> str:
    return (
        "Your task is using functions given to you to get the detailed information of the swe debug task. "
    )


example = SWETaskAIFunc(instruction="Fetch the metadata of detailed swe debug task information")

# </moss>
