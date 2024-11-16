import sys

from ghostos.bootstrap import expect_workspace_dir
from ghostos.contracts.logger import get_console_logger


def check_ghostos_workspace_exists() -> str:
    logger = get_console_logger()
    app_dir, ok = expect_workspace_dir()
    if not ok:
        logger.error("expect GhostOS workspace `%s` is not found. ", app_dir)
        logger.info("run `ghostos init` to create workspace")
        sys.exit(0)
    return app_dir
