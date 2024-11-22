from ghostos.abcd import Ghost
from ghostos.scripts.cli.utils import (
    check_ghostos_workspace_exists,
    get_ghost_by_cli_argv,
)
from ghostos.bootstrap import make_app_container, get_ghostos
from ghostos.prototypes.console import ConsoleApp
from ghostos.entity import get_entity


def main():
    workspace_dir = check_ghostos_workspace_exists()
    ghost_info, modulename, filename, is_temp = get_ghost_by_cli_argv()
    container = make_app_container(workspace_dir)
    ghostos = get_ghostos(container)
    ghost = get_entity(ghost_info.ghost, Ghost)
    app = ConsoleApp(ghostos=ghostos, ghost=ghost, username="")
    app.run()
