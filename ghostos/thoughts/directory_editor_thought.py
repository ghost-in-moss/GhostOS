from typing import TYPE_CHECKING
from ghostos.thoughts.magic_moss_thought import MagicMossThought
from ghostos.core.ghosts import Replier, MultiTask, NewTask
from ghostos.core.moss import Moss as Parent
from ghostos.libraries.file_editor import DirectoryEditor, FileEditor
from ghostos.thoughts.file_editor_thought import FileEditorThought
from pydantic import Field


class DirectoryEditorThought(MagicMossThought):
    """
    Useful to manage all files in a directory
    """
    directory: str = Field(description="absolute path to the directory to be edited")
    debug: bool = Field(default=False, description="turn debugging on")
    llm_api_name: str = Field(default="", description="name of the llm api")


class Moss(Parent):
    """
    you are equipped with some tools helping you to manage the current directory.
    and the FileEditorThought are helpful to manage a single file.
    """

    replier: Replier

    multitask: MultiTask
    """useful to handle multiple tasks, such as manage several files by FileEditorThought."""

    dir_editor: DirectoryEditor
    """ 
    the editor of the current directory.
    you can read or edit the files by FileEditorThought.
    so don't make up anything, based on what you informed.
    """


# <moss-hide>
# the codes between the moss xml marks are not visible to LLM

from ghostos.libraries.file_editor import DirectoryEditorImpl

# using TYPE_CHECKING to avoid reflect invalid importing to prompt.
if TYPE_CHECKING:
    from ghostos.core.ghosts import Ghost
    from ghostos.core.runtime import Event, Session, GoThreadInfo
    from ghostos.core.llms import LLMApi
    from ghostos.core.moss import MossCompiler


def __moss_attr_prompts__():
    """
    hide some attr prompts
    """
    return [
        ("MagicMossThought", ""),
        ("Field", ""),
        ("DirectoryEditorImpl", ""),
    ]


def __directory_editor_instance__(thought: DirectoryEditorThought) -> DirectoryEditorImpl:
    return DirectoryEditorImpl(
        thought.directory,
        ['__pycache__', '*.pyc', '*.pyo', 'venv', '.idea', r'^\.', '*.thread.yml'],
    )


def __magic_moss_thought_llmapi__(thought: DirectoryEditorThought, g: "Ghost") -> "LLMApi":
    """
    optional magic function that define the thought's llmapi
    """
    return g.llms().get_api(thought.llm_api_name)


def __magic_moss_thought_compiling__(
        thought: DirectoryEditorThought,
        g: "Ghost",
        compiler: "MossCompiler",
) -> "MossCompiler":
    """
    optional magic function that prepare a moss compiler by inject / bind / register implementations.
    :param thought:
    :param g:
    :param compiler:
    :return:
    """
    editor = __directory_editor_instance__(thought)
    # 绑定当前的实现.
    compiler.bind(DirectoryEditor, editor)
    return compiler


def __magic_moss_thought_instruction__(thought: DirectoryEditorThought, g: "Ghost", e: "Event") -> str:
    """
    generate instruction, this method is not optional
    :param thought:
    :param g:
    :param e:
    :return: instruction to the llm
    """
    editor = __directory_editor_instance__(thought)
    depth = 2
    directory_info = editor.list(depth=depth)
    temp = """
# Instruction 

Your task are handling files in the current directory.
Current directory is `{current_dir}`, recursive depth is `{depth}`.
The files and subdirectories are listed below:

```
{list_info}
```

You shall use dir_editor and FileEditorThought to fulfill the user's request. 

**Notices**
* the best way to handle single file is to use FileEditThought which will see the detail of the file.
* once you list absolute filepaths, do not join it with some directory prefix.
* do not imagine the content of the files.
"""
    instruction = temp.format(
        current_dir=thought.directory,
        depth=depth,
        list_info="\n".join(directory_info),
    )
    return instruction


def __magic_moss_thought_thread__(thought: DirectoryEditorThought, session: "Session", thread: "GoThreadInfo") -> "GoThreadInfo":
    """
    optional magic function that prepare the thread info, such as modify thread.save_file
    """
    if thought.debug:
        from os.path import join
        thread.save_file = join(thought.directory, ".directory_editor_thought.thread.yml")
    return thread

# </moss-hide>
