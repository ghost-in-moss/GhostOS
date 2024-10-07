from os.path import dirname, join
import sys

__all__ = [
    'app_dir', 'workspace_dir',
    'logging_conf_path', 'logger_name',
]

app_dir = dirname(__file__)
"""application root path"""

workspace_dir = join(app_dir, 'workspace')
"""workspace root path"""

logging_conf_path = join(workspace_dir, 'configs/logging.yml')
"""logging configuration file"""

logger_name = "debug"
"""default logger name for GhostOS"""

sys.path.append(join(app_dir, 'src'))
"""add application source code to PYTHONPATH"""
