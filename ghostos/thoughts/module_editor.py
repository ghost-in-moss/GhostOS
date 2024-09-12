from typing import Iterable
from ghostos.core.ghosts import ModelThought, Ghost, Action
from ghostos.core.llms import LLMApi
from ghostos.core.moss import PyContext, MossCompiler
from ghostos.core.session import Event
from ghostos.thoughts.basic import LLMThoughtDriver
from ghostos.thoughts.moss import BasicMossThoughtDriver
from ghostos.libraries.py_editor import PythonEditorImpl, ModuleEditor
from pydantic import Field
from ghostos.helpers import md5

DEFAULT_PY_MODULE_EDITOR_INSTRUCTION = """
# Instruction

Your task is helping user to read / understand / edit a python module file. 
The target module you are handling is {modulename}, the source code with line num at end of each line are: 

```python
{target_source}
```

With ModuleEditor you can read / change it. 
Remember to print the result when you call some method of ModuleEditor, check the printed result if anything goes wrong.

"""


class PyModuleEditorThought(ModelThought):
    name: str = Field(default="PyModuleEditor")
    description: str = Field(default="can read, understand and edit python module")
    target_module: str = Field(description="target modulename")
    llm_api_name: str = Field(default="", description="specific llm api name")


def new_pymodule_editor_thought(target_module: str, llm_api_name: str = "") -> PyModuleEditorThought:
    """
    instance a
    :param target_module:
    :param llm_api_name:
    :return:
    """
    return PyModuleEditorThought(
        target_module=target_module,
        llm_api_name=llm_api_name,
    )


class PyModuleEditorThoughtDriver(BasicMossThoughtDriver, LLMThoughtDriver[PyModuleEditorThought]):
    _module_editor = None

    def get_llmapi(self, g: Ghost) -> LLMApi:
        return g.llms().get_api(self.thought.llm_api_name)

    def new_task_id(self, g: Ghost) -> str:
        process_id = g.session().process().process_id
        task_id = f"process_{process_id}_task_{self.thought.target_module}"
        # task_id in a same process will always be the same
        return md5(task_id)

    def instruction(self, g: Ghost, e: Event) -> str:
        editor = self.module_editor()
        return DEFAULT_PY_MODULE_EDITOR_INSTRUCTION.format(
            modulename=self.thought.target_module,
            target_source=editor.read_source(show_line_num=True),
        )

    def prepare_moss_compiler(self, g: Ghost) -> MossCompiler:
        compiler = super().prepare_moss_compiler(g)
        module_editor = self.module_editor()
        compiler.injects(editor=module_editor)
        return compiler

    def module_editor(self) -> ModuleEditor:
        if self._module_editor is None:
            py_editor = PythonEditorImpl()
            module_editor = py_editor.module(self.thought.target_module)
            self._module_editor = module_editor
        return self._module_editor

    def init_pycontext(self) -> PyContext:
        return PyContext(
            module="ghostos.thoughts.module_editor_tools",
        )
