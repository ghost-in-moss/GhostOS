from typing import Optional
from typing_extensions import Self

from ghostos.contracts.modules import Modules, DefaultModules
from ghostos.libraries.pyeditor.abcd import PyModuleEditor
from ghostos_container import Provider, Container
from ghostos_common.prompter import POM
import inspect

__all__ = ['SimplePyModuleEditor', 'SimplePyModuleEditorProvider']


class SimplePyModuleEditor(POM, PyModuleEditor):

    def __init__(self, modulename: str, filename: str = "", modules: Optional[Modules] = None) -> None:
        self.modulename = modulename
        self._modules = modules if modules else DefaultModules()
        self._module = self._modules.import_module(self.modulename)
        if not filename:
            filename = self._module.__file__
        self.filename = filename
        self._source: Optional[str] = None

    def _get_module_source(self) -> str:
        if self._source is None:
            self._source = inspect.getsource(self._module)
        return self._source

    def new_from(self, modulename: str) -> Self:
        return SimplePyModuleEditor(modulename, modules=self._modules)

    def get_source(self, show_line_num: bool = False, start_line: int = 0, end_line: int = -1) -> str:
        source = self._get_module_source()
        lines = source.splitlines()
        outputs = []
        line_num = 0
        for line in lines:
            line_num += 1
            if line_num < start_line:
                continue
            if 0 < end_line < line_num:
                continue
            handled_line = line
            if show_line_num:
                prefix = str(line_num)
                handled_line = prefix + "|" + handled_line
            outputs.append(handled_line)
        return "\n".join(outputs)

    def _save_module_source(self, source: str) -> None:
        self._source = source
        with open(self.filename, "w") as f:
            f.write(source)
        self._modules.reload(self._module)
        self._module = self._modules.import_module(self.modulename)

    def get_source_block(self, start_with: str, end_with: str) -> str:
        source = self._get_module_source()
        parts = source.split(start_with, 1)
        if len(parts) == 1:
            raise AttributeError(f"Module {self.modulename} can not find start `{start_with}`")
        content = start_with + parts[1]
        parts = content.split(end_with, 1)
        if len(parts) == 1:
            raise AttributeError(f"Module {self.modulename} can not find end `{end_with}`")
        block = parts[0] + end_with
        return block

    def replace(self, target_str: str, replace_str: str, count: int = 1, reload: bool = False) -> bool:
        module_source = self._get_module_source()
        if target_str not in module_source:
            return False
        source = module_source.replace(target_str, replace_str, count)
        self.save(reload=reload, source=source)
        return True

    def append(self, source: str, reload: bool = False) -> None:
        source = source.strip()
        module_source = self._get_module_source()
        saving = module_source.rstrip("\n")
        saving = saving + "\n\n" + source + "\n"
        self.save(reload=reload, source=saving)

    def insert(self, source: str, line_num: int, reload: bool = False) -> None:
        module_source = self._get_module_source()
        lines = module_source.splitlines()
        lines.insert(line_num, source)
        replace = "\n".join(lines)
        self.save(reload=reload, source=replace)

    def replace_attr(self, attr_name: str, replace_str: str, reload: bool = False) -> str:
        if attr_name not in self._module.__dict__:
            return f"attribute {attr_name} is not defined in this module"
        value = self._module.__dict__[attr_name]
        if not inspect.isclass(value) and not inspect.isfunction(value):
            return f"attribute {attr_name} is not class or function that can be replaced"
        source = inspect.getsource(value)
        ok = self.replace(source, replace_str, count=1, reload=reload)
        return "ok" if ok else "replace failed"

    def save(self, reload: bool = True, source: Optional[str] = None) -> None:
        _source = self._get_module_source()
        if source is None:
            source = _source
        self._save_module_source(source)
        if reload:
            self._modules.reload(self._module)

    def self_prompt(self, container: Container) -> str:
        return f"""
This PyModuleEditor is editing module `{self.modulename}` on file `{self.filename}`.
The source code with line num prefix are: 

```text
{self.get_source(True)}
``` 

(notice the line number prefix at each line is not part of the source code, just indication for you)
"""

    def get_title(self) -> str:
        return f"ModuleEditor on `{self.modulename}`"


class SimplePyModuleEditorProvider(Provider[PyModuleEditor]):

    def __init__(self, modulename: str, filename: str = "") -> None:
        self.modulename = modulename
        self.filename = filename

    def singleton(self) -> bool:
        return False

    def factory(self, con: Container) -> Optional[PyModuleEditor]:
        modules = con.get(Modules)
        return SimplePyModuleEditor(self.modulename, self.filename, modules)
