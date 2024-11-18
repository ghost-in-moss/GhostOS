from ghostos.abcd import Ghost
from ghostos.scripts.cli.utils import (
    check_ghostos_workspace_exists,
    parse_args_modulename_or_filename, get_or_create_module_from_name,
)
from ghostos.bootstrap import make_app_container, get_ghostos
from ghostos.prototypes.console import ConsoleApp


def get_ghost() -> Ghost:
    filename_or_modulename, args = parse_args_modulename_or_filename()
    found = get_or_create_module_from_name(filename_or_modulename, "ghostos.temp.agent")

    if found.value is not None:
        if not isinstance(found.value, Ghost):
            raise SystemExit(f"{found.value} is not a Ghost object")
        ghost = found.value
    elif "__ghost__" in found.module.__dict__:
        ghost = found.module.__dict__["__ghost__"]
        if not isinstance(ghost, Ghost):
            raise SystemExit(f"{filename_or_modulename} __ghost__ is not a Ghost object")
    else:
        raise SystemExit(f"cant find ghost instance at {filename_or_modulename}")
    return ghost


def main():
    workspace_dir = check_ghostos_workspace_exists()
    ghost = get_ghost()
    container = make_app_container(workspace_dir)
    ghostos = get_ghostos(container)
    app = ConsoleApp(ghostos=ghostos, ghost=ghost, username="")
    app.run()
