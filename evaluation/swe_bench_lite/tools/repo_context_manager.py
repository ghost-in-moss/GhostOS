import os
import logging
from typing import Optional, List, Tuple, Dict
from enum import Enum
import atexit
import subprocess
from evaluation.swe_bench_lite.ai_funcs.swe_task_manager import SWEDebugTaskCtx
from ghostos.core.moss.decorators import cls_definition, cls_source_code, cls_outline


@cls_source_code()
class PrepareRepositoryResult(Enum):
    PREPARE_SUCCESS = "Prepare repository successfully"
    REPO_NOT_FOUND = "Repository not found"
    REPO_NOT_DIR = "Repository is not a directory"
    REPO_CHECKOUT_FAILED = "Failed to checkout to base commit"
    REPO_CHECKOUT_BRANCH_FAILED = "Failed to checkout to a new branch"
    REPO_BRANCH_DEL_FAILED = "Failed to delete the new branch"


@cls_outline()
class RepositoryContextManager:
    """
    This class manages the repository context for debugging.
    You should call prepare_repository_for_debug() before your business logic, and call reset_repository_after_debug() after you're ALL done.
    """
    def __init__(self, debug_task_ctx: SWEDebugTaskCtx):
        self.debug_task_ctx = debug_task_ctx
        atexit.register(self.reset_repository_after_debug)

    def prepare_repository_for_debug(self) -> PrepareRepositoryResult:
        """
        Prepare the repository for debugging (contains git operations)
        :return: the result of the preparation
        """
        target_path = os.path.join(self.debug_task_ctx.workspace_path, self.debug_task_ctx.repo)
        if not os.path.exists(target_path):
            logging.error(f"Repository not found: {target_path}")
            return PrepareRepositoryResult.REPO_NOT_FOUND
        if not os.path.isdir(target_path):
            logging.error(f"Repository is not a directory: {target_path}")
            return PrepareRepositoryResult.REPO_NOT_DIR

        os.chdir(target_path)
        logging.info(f"cd to the target repository: {target_path} succeed")

        # discard all changes
        discard_cmd = "git checkout -- ."
        if os.system(discard_cmd) != 0:
            logging.error(f"Failed to discard all changes at initialize")
            return PrepareRepositoryResult.REPO_CHECKOUT_FAILED

        # checkout to main branch
        checkout_main_cmd = "git checkout main"
        if os.system(checkout_main_cmd) != 0:
            logging.error(f"Failed to checkout to main branch")
            return PrepareRepositoryResult.REPO_CHECKOUT_FAILED

        # Check if the target branch exists
        check_branch_cmd = f"git branch --list {self.debug_task_ctx.instance_id}"
        #If the stripped output is non-empty (truthy), it means the branch exists.
        if subprocess.run(check_branch_cmd, shell=True, capture_output=True, text=True).stdout.strip(): 
            # If the branch exists, delete it
            delete_branch_cmd = f"git branch -D {self.debug_task_ctx.instance_id}"
            if os.system(delete_branch_cmd) != 0:
                logging.error(f"Failed to delete the target branch: {self.debug_task_ctx.instance_id}")
                return PrepareRepositoryResult.REPO_BRANCH_DEL_FAILED

        # checkout to a new branch
        checkout_branch_cmd = f"git checkout -b {self.debug_task_ctx.instance_id}"
        if os.system(checkout_branch_cmd) != 0:
            logging.error(f"Failed to checkout to a new branch: {self.debug_task_ctx.instance_id}")
            return PrepareRepositoryResult.REPO_CHECKOUT_BRANCH_FAILED

        # checkout to the base commit
        checkout_cmd = f"git checkout {self.debug_task_ctx.base_commit}"
        if os.system(checkout_cmd) != 0:
            logging.error(f"Failed to checkout to base commit: {self.debug_task_ctx.base_commit}")
            return PrepareRepositoryResult.REPO_CHECKOUT_FAILED

        logging.info(f"Prepare repository for debug succeed")
        return PrepareRepositoryResult.PREPARE_SUCCESS

    def reset_repository_after_debug(self) -> None:
        """
        Reset the repository after debugging
        """
        logging.info(f"^^^^^^^^^^^^^^^^^^^^^^^^Reset repository after debug^^^^^^^^^^^^^^^^^^^^^^^^")
        target_path = os.path.join(self.debug_task_ctx.workspace_path, self.debug_task_ctx.repo)
        if not os.path.exists(target_path) or not os.path.isdir(target_path):
            logging.error(f"reset_repository_after_debug Repository not found or not a directory: {target_path}")
            return

        # cd the target repository
        os.chdir(target_path)
        logging.info(f"reset_repository_after_debug cd to the target repository: {target_path} succeed")

        # discard all changes
        discard_cmd = "git checkout -- ."
        if os.system(discard_cmd) != 0:
            logging.error(f"Failed to discard all changes")
            return

        # checkout back to main
        checkout_main_cmd = "git checkout main"
        if os.system(checkout_main_cmd) != 0:
            logging.error(f"Failed to checkout back to main")
            return

        # delete the new branch
        delete_branch_cmd = f"git branch -D {self.debug_task_ctx.instance_id}"
        if os.system(delete_branch_cmd) != 0:
            logging.error(f"Failed to delete the new branch: {self.debug_task_ctx.instance_id}")
            return

        logging.info(f"Reset repository after debug succeed")
        atexit.unregister(self.reset_repository_after_debug)  # Unregister after execution

