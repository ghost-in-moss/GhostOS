from ghostos.core.ghosts import ModelThought, Ghost
from ghostos.core.llms import LLMApi
from ghostos.core.moss import PyContext, MossCompiler
from ghostos.core.runtime import Event, Session, GoThreadInfo
from ghostos.thoughts.moss_thought import BasicMossThoughtDriver, LLMThoughtDriver
from ghostos.thoughts import file_editor_moss
from ghostos.libraries.file_editor import FileEditorImpl, FileEditor
from pydantic import Field
from ghostos.helpers import md5
from ghostos.container import provide

__all__ = ['FileEditorThought', 'new_file_editor_thought']


class FileEditorThought(ModelThought):
    """
    Useful to read, understand and modify a file with any request.
    """
    filepath: str = Field(description="absolute filepath the thought shall edit on")
    debug: bool = Field(default=False, description="if debug mode, generate relative thread file for debugging")
    llm_api_name: str = Field(default="", description="llm model name, if you don't know what you want, keep empty")


def new_file_editor_thought(
        filepath: str,
        llm_api_name: str = "",
        debug: bool = True,
) -> FileEditorThought:
    """
    instance a pymodule_editor thought.
    :param filepath: absolute filepath the thought shall edit on
    :param llm_api_name:
    :param debug: if debug mode is true, moss code will send to user
    """
    return FileEditorThought(
        filepath=filepath,
        llm_api_name=llm_api_name,
        debug=debug,
    )


DEFAULT_FILE_EDITOR_INSTRUCTION = """
# Instruction

Your task is helping user to read / understand / edit a file. 
The target file you are handling is `{filepath}`, the content with line num are: 

```
{file_content}
```
Notice the line num and `|` before each line are not the content of the file, just for you to read. 

With FileEditor that MOSS provided you can read / change it. 
FileEditor provides multiple methods to update the content of the file, 
you need to write your content as a string, and use the methods to replace / insert / append the file.
Remember to print the result when you call some method of FileEditor, check the printed result if anything went wrong.
"""


class FileEditorThoughtDriver(BasicMossThoughtDriver, LLMThoughtDriver[FileEditorThought]):

    def init_pycontext(self) -> PyContext:
        return PyContext(
            module=file_editor_moss.__name__,
        )

    def is_moss_code_delivery(self) -> bool:
        return self.thought.debug

    def new_task_id(self, g: Ghost) -> str:
        process_id = g.session().update_prompt().process_id
        task_id = f"process_{process_id}_task_{self.thought.filepath}"
        # task_id in a same process will always be the same
        return md5(task_id)

    def file_editor(self) -> FileEditorImpl:
        return FileEditorImpl(self.thought.filepath)

    def prepare_moss_compiler(self, g: Ghost, compiler: MossCompiler) -> MossCompiler:
        # inject dynamic generated file editor instance to moss.
        compiler.register(provide(FileEditor)(lambda c: self.file_editor()))
        return compiler

    def prepare_thread(self, session: Session, thread: GoThreadInfo) -> GoThreadInfo:
        if self.thought.debug:
            filepath = self.thought.filepath
            saving_path = filepath + ".thread.yml"
            thread.save_file = saving_path
        return thread

    def get_llmapi(self, g: Ghost) -> LLMApi:
        return g.llms().get_api(self.thought.llm_api_name)

    def instruction(self, g: Ghost, e: Event) -> str:
        content = self.file_editor().read(show_line_num=True)
        return DEFAULT_FILE_EDITOR_INSTRUCTION.format(
            filepath=self.thought.filepath,
            file_content=content,
        )
