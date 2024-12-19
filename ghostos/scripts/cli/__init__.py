from __future__ import annotations

import os.path

import click
import sys
from os.path import join, abspath
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt


@click.group()
def main():
    pass


@main.command("clear-runtime")
@click.option("--path", default="", show_default=True)
def clear_runtime(path: str):
    """
    clear workspace runtime files
    """
    from ghostos.scripts.clear_runtime import clear_runtime
    from ghostos.bootstrap import get_bootstrap_config
    conf = get_bootstrap_config()
    confirm = Prompt.ask(
        f"Would you like to proceed?\n\nWill clear all workspace runtime files at {conf.abs_runtime_dir()} [y/N]",
        choices=["y", "n"],
        default="y",
    )
    if confirm == "y":
        clear_runtime(path)
    else:
        print("Aborted")


@main.command("init")
@click.option("--path", default="", show_default=True)
def init_workspace(path: str):
    """
    init ghostos workspace
    """
    from ghostos.scripts.copy_workspace import copy_workspace
    if path:
        path = abspath(path)
    else:
        path = abspath("workspace")
    if os.path.exists(path):
        print(f"the path {path} already exists")
        exit(0)

    result = Prompt.ask(f"will create ghostos workspace at {path}. confirm?", default="yes", choices=["yes", "no"])
    if result == "yes":
        copy_workspace(path)
    else:
        print("closed")


@main.command("docs")
def open_docs():
    """See GhostOS Docs"""
    from ghostos.bootstrap import get_bootstrap_config
    conf = get_bootstrap_config()
    docs_dir = join(conf.ghostos_dir, "docs")
    console = Console()
    m = Markdown(f"""
You can open ghostos documentation:

1. https://github.com/ghost-in-moss/GhostOS/docs
2. `docsify serve  {docs_dir}` (if you installed [docsify](https://docsifyjs.org/#/))
"""
                 )
    console.print(Panel(
        m,
        title="GhostOS docs",
    ))


@main.command("help")
def ghostos_help():
    """Print this help message."""
    _get_command_line_as_string()

    assert len(sys.argv) == 2  # This is always true, but let's assert anyway.
    # Pretend user typed 'streamlit --help' instead of 'streamlit help'.
    sys.argv[1] = "--help"
    main(prog_name="main")


# copy from streamlit app, thanks
def _get_command_line_as_string() -> str | None:
    """Print this help message."""
    import sys
    import subprocess
    parent = click.get_current_context().parent
    if parent is None:
        return None

    cmd_line_as_list = [parent.command_path]
    cmd_line_as_list.extend(sys.argv[1:])
    return subprocess.list2cmdline(cmd_line_as_list)
