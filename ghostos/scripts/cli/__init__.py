from __future__ import annotations

import os.path

import click
import sys
from os import getcwd
from os.path import join, abspath
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt


@click.group()
def main():
    pass


@main.command("thread")
@click.argument("thread_id")
def show_thread_info(thread_id: str):
    """
    show thread info in streamlit app, with thread id or thread filename
    """
    from ghostos.scripts.cli.run_streamlit_thread import start_ghostos_thread_info
    start_ghostos_thread_info(thread_id)


@main.command("web")
@click.argument("python_file_or_module")
@click.option("--src", "-s", default=".", show_default=True,
              help="load the directory to python path, make sure can import relative packages")
def start_streamlit_web(python_file_or_module: str, src: str):
    """
    turn a python file or module into a streamlit web agent
    """
    from ghostos.scripts.cli.run_streamlit_app import start_streamlit_app_by_ghost_info
    from ghostos.scripts.cli.utils import find_ghost_by_file_or_module
    import sys
    from os.path import abspath
    if src:
        # add source path to system so to import the source code.
        sys.path.append(abspath(src))

    ghost_info, module, filename, is_temp = find_ghost_by_file_or_module(python_file_or_module)
    start_streamlit_app_by_ghost_info(ghost_info, module.__name__, filename, is_temp)


@main.command("console")
@click.argument("python_file_or_module")
def start_console_app(python_file_or_module: str):
    """
    turn a python file or module into a console agent
    """
    from ghostos.scripts.cli.run_console import run_console_app
    run_console_app(python_file_or_module)


@main.command("config")
def start_web_config():
    """
    config the ghostos in streamlit web app
    """
    from ghostos.scripts.cli.run_streamlit_app import start_streamlit_prototype_cli
    from ghostos.bootstrap import get_bootstrap_config
    start_streamlit_prototype_cli(
        "run_configs.py",
        "",
        get_bootstrap_config().abs_workspace_dir(),
    )


@main.command("clear-runtime")
@click.option("--path", default="", show_default=True)
def clear_runtime(path: str):
    """
    clear workspace runtime files
    """
    from ghostos.scripts.clear import clear_runtime
    from ghostos.bootstrap import get_bootstrap_config
    conf = get_bootstrap_config()
    confirm = Prompt.ask(
        f"Will clear all workspace runtime files at {conf.abs_runtime_dir()}\n\nWould you like to proceed? [y/N]",
        choices=["y", "n"],
        default="y",
    )
    if confirm == "y":
        clear_runtime(path)
    else:
        print("Aborted")


@main.command("init")
@click.option("--path", default="", show_default=True)
def init_app(path: str):
    """
    init ghostos workspace
    """
    from ghostos.scripts.copy_workspace import copy_workspace
    from ghostos.bootstrap import expect_workspace_dir, app_stub_dir, get_bootstrap_config
    console = Console()
    console.print(Panel(
        Markdown("""
`GhostOS` need an `app` directory as workspace. 

The Workspace meant to save local files such as configs, logs, cache files.
"""),
        title="Initialize GhostOS",
    ))

    conf = get_bootstrap_config(local=False)
    cwd = getcwd()
    result = Prompt.ask(
        f"\n>> will init ghostos workspace at `{cwd}`. input directory name:",
        default="ghostos_ws",
    )
    source_dir = app_stub_dir()
    real_workspace_dir = abspath(result)
    console.print("start to init ghostos workspace")
    copy_workspace(source_dir, real_workspace_dir)
    console.print("ghostos workspace copied")
    conf.workspace_dir = result
    saved_file = conf.save(cwd)
    console.print(f"save .ghostos.yml to {saved_file}")
    console.print(Panel(Markdown(f"""
Done create workspace!

`GhostOS` use OpenAI model service and `gpt-4o` model as default LLM model.
It need environment variable `OPENAI_API_KEY` to call the service.

You can provide your OpenAI API key by:

```bash
export OPENAI_API_KEY=<KEY>
```

Or:
1. copy `{conf.env_example_file()}` to `{conf.env_file()}, and offer the necessary env configuration. (Optional)
2. run `ghostos config` to configure them manually. (Optional)

Finally you can run `ghostos web ghostos.demo.agents.jojo` to test if everything is working. 
""")))


@main.command("docs")
def open_docs():
    """See GhostOS Docs"""
    from ghostos.bootstrap import get_bootstrap_config
    conf = get_bootstrap_config()
    console = Console()
    m = Markdown(f"""
You can open ghostos documentation:

* zh-cn: https://github.com/ghost-in-moss/GhostOS/docs/zh-cn/README.md
* en: https://github.com/ghost-in-moss/GhostOS/docs/en/README.md

or `git clone https://github.com/ghost-in-moss/GhostOS` then `docsify serve`
"""
                 )
    console.print(Panel(
        m,
        title="GhostOS docs",
    ))


# @main.command("py-interface")
# @click.argument("import_path")
# @click.option("--force", is_flag=True, flag_value=True, help="Force generate")
# @click.option("--model", default="", show_default=True, help="the llm api name")
# def gen_py_interface(
#         import_path: str,
#         force: bool = False,
#         model: str = "",
# ):
#     """
#     generate python interface by large language model from a python function or class import path
#     """
#     from ghostos.libraries.pyeditor import PyInterfaceGenerator
#     from ghostos.bootstrap import get_container
#     container = get_container()
#     pig = container.force_fetch(PyInterfaceGenerator)
#     generated = pig.generate_interface(import_path, cache=not force, llm_api=model)
#     console = Console()
#     console.print(Markdown(f"""
# ```python
# {generated}
# ```
# """))

# todo: 迁移到子文件.
@main.command("moss")
@click.argument('python_file_or_module')
@click.option("--tokens", "-t", default=False, is_flag=True, help="Show tokens count")
def dump_moss_context(python_file_or_module: str, tokens: bool):
    """
    dump moss context from a python file or module
    """
    from ghostos.bootstrap import get_container
    from ghostos.core.moss import MossCompiler, PyContext
    from ghostos.helpers import yaml_pretty_dump

    container = get_container()
    compiler = container.force_fetch(MossCompiler)

    filename = os.path.abspath(python_file_or_module)
    if os.path.exists(filename):
        with open(filename, "r") as f:
            code = f.read()
            pycontext = PyContext(code=code)
            compiled = compiler.join_context(pycontext).compile("__target__")

    else:
        # consider it a module
        compiled = compiler.compile(python_file_or_module)

    with compiled:
        modulename = compiled.module().__name__
        filename = compiled.module().__file__
        prompter = compiled.prompter()
        code = prompter.get_source_code()
        imported_prompt = prompter.get_imported_attrs_prompt()
        magic_prompt = prompter.get_magic_prompt()
        pycontext = compiled.dump_pycontext()
        console = Console()
        console.print(
            Panel(
                Markdown(
                    f"""
`{modulename}` (`{filename}`):
```python
{code}
```
""",
                ),
                title="Source Code",
            )
        )
        console.print(
            Panel(
                Markdown(
                    f"""
```python
{imported_prompt}
```
"""
                ),
                title="Imported Attrs Prompt",
            ),
        )
        console.print(
            Panel(
                Markdown(
                    f"""
```text
{magic_prompt}
```
""",
                ),
                title="magic prompt",
            )
        )
        console.print(
            Panel(
                Markdown(
                    f"""
```yaml
{yaml_pretty_dump(pycontext.model_dump(exclude_defaults=True))}
```
""",
                ),
                title="pycontext",
            )
        )

        if tokens:
            from tiktoken import get_encoding
            enc = get_encoding("gpt2")
            code_tokens_count = len(enc.encode(code))
            imported_prompt_tokens_count = len(enc.encode(imported_prompt))
            console.print(f"code tokens:{code_tokens_count}, imported tokens:{imported_prompt_tokens_count}")


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

#
# if __name__ == '__main__':
#     # 方便通过IDE调试
#     from ghostos.scripts.cli.run_streamlit_app import start_ghost_app
#     from ghostos.scripts.cli.utils import find_ghost_by_file_or_module
#
#     python_file_or_module = "ghostos.demo.ghost_func_example"
#     ghost_info, module, filename, is_temp = find_ghost_by_file_or_module(python_file_or_module)
#     start_ghost_app(ghost_info, module.__name__, filename, is_temp)
