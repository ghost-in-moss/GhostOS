from typing import Optional, List
from ghostos.core.moss.aifunc import AIFunc, AIFuncResult
from pydantic import BaseModel, Field
from ghostos.core.moss import Moss
from ghostos.core.moss.decorators import cls_source_code

import logging
import json
import re

# 定义正则表达式
pattern = r'(\w+)\s\(([\w\.]+)\)'
# 编译正则表达式
compiled_pattern = re.compile(pattern)

def extract_info(text):
    match = compiled_pattern.search(text)
    if match:
        method_name, class_path = match.groups()
        return method_name, class_path
    return None


class UnitTestInfo(BaseModel):
    test_method_name: str = Field(..., description="The name of the test method")
    test_class_name: str = Field(..., description="The name of the test class from repository content root")

SEP = "\n====================================\n"

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

    def __str__(self):
        ret = (f"SWEDebugTaskCtx(workspace_path={self.workspace_path}, repo={self.repo}, instance_id={self.instance_id}, "
               f"base_commit={self.base_commit}, passed_tests={self.passed_tests}, issue_info: {SEP}{repr(self.issue_info)} ")
        if len(self.supplementary_issue_info) > 0:
            ret += f", supplementary_issue_info: {SEP}{repr(self.supplementary_issue_info)} )"
        else:
            ret += ")"
        return ret



def _get_method_name_and_class_from_str(s: str) -> (str, str):
    info = extract_info(s)
    if info:
        return info[0], info[1]
    return "", ""

def get_swe_debug_task_ctx(task_json_path: str, workspace_path: str) -> SWEDebugTaskCtx:
    with open(task_json_path, 'r') as f:
        task_json = json.load(f)

    try:
        # parse the task json to get the task context
        repo_name = task_json['repo'].split('/')[-1]
        logging.info(f"get swe debug task, repo_name: {repo_name}")

        instance_id = task_json['instance_id']
        logging.info(f"get swe debug task, instance_id: {instance_id}")

        passed_tests = []
        for test_info in task_json['PASS_TO_PASS']:
            method_name, class_path = _get_method_name_and_class_from_str(test_info)
            if len(method_name) > 0:
                passed_tests.append(UnitTestInfo(test_method_name=method_name, test_class_name=class_path))
                logging.info(f"get swe debug task, passed_test: {method_name} in {class_path}")

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
    debug_task_ctx: SWEDebugTaskCtx = Field(..., description="the detailed information of the swe debug task")



class SWETaskAIFunc(AIFunc):
    """
    get detailed information about the swe debug task
    """
    instruction: str = Field(description="the instruction of the task, to get the detailed information of the swe debug task")
    task_json_path: str = Field(description="the path of the task json file")
    workspace_path: str = Field(description="the path of the workspace")


# <moss>

def __aifunc_instruction__(fn: SWETaskAIFunc) -> str:
    return f"instruction: {fn.instruction} task_json_path: {fn.task_json_path}, workspace_path: {fn.workspace_path}"

# </moss>

