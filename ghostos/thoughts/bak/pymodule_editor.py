import inspect
from typing import Dict, Optional
from ghostos.core.ghosts import ModelThought, Ghost
from ghostos.core.llms import LLMApi
from ghostos.core.moss import PyContext, MossCompiler
from ghostos.core.runtime import Event, Session, GoThreadInfo
from ghostos.thoughts.basic import LLMThoughtDriver
from ghostos.thoughts.moss_thought import BasicMossThoughtDriver
from ghostos.thoughts import pymodule_editor_moss
from ghostos.libraries.py_editor import PythonEditorImpl, ModuleEditor
from pydantic import Field
from ghostos.helpers import md5, import_from_path

DEFAULT_PY_MODULE_EDITOR_INSTRUCTION = """
# Instruction

Your task is helping user to read / understand / edit a python module file. 
The target module you are handling is `{modulename}`, the source code with line num are: 

```python
{target_source}
```

With ModuleEditor that MOSS provided you can read / change it. 
Remember to print the result when you call some method of ModuleEditor, check the printed result if anything goes wrong.

You can update `{modulename}` 's code, use the ModuleEditor that MOSS provided to you. 
ModuleEditor provides multiple methods to update the source code, you need to write your code as a string, and use the methods.
"""


class PyModuleEditorThought(ModelThought):
    """
    Useful to edit a python module file.
    """
    target_module: str = Field(description="target modulename")
    referencing: Dict = Field(
        default_factory=dict,
        description="references for python editor, key is import path, value is the prompt about it"
    )
    llm_api_name: str = Field(default="", description="specific llm api name")
    debug: bool = Field(default=False, description="debug mode, if true, moss code will send to user")


def new_pymodule_editor_thought(
        target_module: str,
        llm_api_name: str = "",
        referencing: Optional[Dict] = None,
        debug: bool = True,
) -> PyModuleEditorThought:
    """
    instance a pymodule_editor thought.
    :param target_module:
    :param llm_api_name:
    :param debug: if debug mode is true, moss code will send to user
    :param referencing:
    """
    referencing = referencing or {}
    return PyModuleEditorThought(
        target_module=target_module,
        llm_api_name=llm_api_name,
        debug=debug,
        referencing=referencing,
    )


class PyModuleEditorThoughtDriver(BasicMossThoughtDriver, LLMThoughtDriver[PyModuleEditorThought]):
    _module_editor = None

    def get_llmapi(self, g: Ghost) -> LLMApi:
        return g.llms().get_api(self.thought.llm_api_name)

    def new_task_id(self, g: Ghost) -> str:
        process_id = g.session().update_prompt().process_id
        task_id = f"process_{process_id}_task_{self.thought.target_module}"
        # task_id in a same process will always be the same
        return md5(task_id)

    def prepare_thread(self, session: Session, thread: GoThreadInfo) -> GoThreadInfo:
        """
        save the thread where I'm convenient to see it
        :param session:
        :param thread:
        :return:
        """
        editor = self.module_editor()
        filepath = editor.filepath()
        if filepath.endswith(".py"):
            thread_path = filepath[:-3] + ".thread.yml"
        else:
            thread_path = filepath + ".thread.yml"
        thread.save_file = thread_path
        return thread

    def instruction(self, g: Ghost, e: Event) -> str:
        editor = self.module_editor()
        target_source = editor.read_source(show_line_num=True)
        splits = target_source.split("\nif __name__ == ")
        target_source = splits[0]
        content = DEFAULT_PY_MODULE_EDITOR_INSTRUCTION.format(
            modulename=self.thought.target_module,
            target_source=target_source,
        )
        if self.thought.referencing:
            referencing = "\n\n# referencing\n\nThere are some references for you:"
            for import_path, prompt in self.thought.referencing.conversation_item_states():
                target = import_from_path(import_path)
                source = inspect.getsource(target)
                referencing += f"""
                
## {import_path}

the code is:
```python
{source}
```

{prompt}
"""
            content += referencing
        return content

    def prepare_moss_compiler(self, g: Ghost, compiler: MossCompiler) -> MossCompiler:
        module_editor = self.module_editor()
        compiler.injects(editor=module_editor)
        return compiler

    def module_editor(self) -> ModuleEditor:
        if self._module_editor is None:
            py_editor = PythonEditorImpl()
            module_editor = py_editor.module(self.thought.target_module)
            self._module_editor = module_editor
        return self._module_editor

    def is_moss_code_delivery(self) -> bool:
        return self.thought.debug

    def init_pycontext(self) -> PyContext:
        return PyContext(
            module=pymodule_editor_moss.__name__,
        )
