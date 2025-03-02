from ghostos.abcd import Ghost
from ghostos.abcd.utils import get_module_magic_shell_providers
from ghostos.scripts.cli.utils import (
    find_ghost_by_file_or_module,
)
from ghostos.bootstrap import get_ghostos
from ghostos.prototypes.console import ConsoleApp
from ghostos_common.entity import get_entity


def run_console_app(file_or_module: str):
    ghost_info, module, filename, is_temp = find_ghost_by_file_or_module(file_or_module)
    providers = get_module_magic_shell_providers(module)
    ghostos = get_ghostos()
    ghost = get_entity(ghost_info.ghost, Ghost)
    app = ConsoleApp(ghostos=ghostos, ghost=ghost, username="", providers=providers)
    app.run()
