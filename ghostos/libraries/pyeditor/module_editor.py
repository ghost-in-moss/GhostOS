from typing import Optional
from types import ModuleType
from ghostos.contracts.modules import Modules

from ghostos.libraries.pyeditor.abcd import PyModuleEditor, ModuleInfo
import inspect


class SimplePyModuleEditor(PyModuleEditor):

    def __init__(self, modulename: str, filename: str, modules: Modules) -> None:
        self.modulename = modulename
        self.filename = filename
        self._modules = modules
        self._module = modules.import_module(self.modulename)
        self._source: Optional[str] = None

    def _get_module_source(self) -> str:
        if self._source is None:
            self._source = inspect.getsource(self._module)
        return self._source

    def get_source(self, show_line_num: bool = False, start_line: int = 0, end_line: int = -1) -> str:
        source = self._get_module_source()
        lines = source.splitlines()
        outputs = []
        line_num = -1
        max_lines = len(lines)
        digit = len(str(max_lines))
        for line in lines:
            line_num += 1
            if line_num < start_line:
                continue
            if 0 < end_line < line_num:
                continue
            handled_line = line
            if show_line_num:
                prefix = str(line_num)
                prefix = " " * (digit - len(prefix)) + prefix
                handled_line = prefix + "|" + handled_line
            outputs.append(handled_line)
        return "\n".join(outputs)

    def _save_module_source(self, source: str) -> None:
        self._source = source
        with open(self.filename, "w") as f:
            f.write(source)

    def get_source_block(self, start_with: str, end_with: str) -> str:
        source = self._get_module_source()
        parts = source.rsplit(start_with, 1)
        if len(parts) == 1:
            raise AttributeError(f"Module {self.modulename} can not find start `{start_with}`")
        content = start_with + parts[1]
        parts = content.rsplit(end_with, 1)
        if len(parts) == 1:
            raise AttributeError(f"Module {self.modulename} can not find end `{end_with}`")
        block = parts[0] + end_with
        return block

    def replace(self, target_str: str, replace_str: str, count: int = -1) -> bool:
        module_source = self._get_module_source()
        if target_str not in module_source:
            return False
        source = module_source.replace(target_str, replace_str, count)
        self._save_module_source(source)
        return True

    def append(self, source: str) -> None:
        source = source.strip()
        module_source = self._get_module_source()
        saving = module_source.rstrip("\n")
        saving = saving + "\n\n" + source + "\n"
        self._save_module_source(saving)

    def insert(self, source: str, line_num: int) -> None:
        module_source = self._get_module_source()
        lines = module_source.splitlines()
        outputs = []
        idx = -1
        for line in lines:
            idx += 1
            if line_num == idx:
                outputs.append(source)
            outputs.append(line)
        replace = "\n".join(outputs)
        self._save_module_source(replace)

    def replace_attr(self, attr_name: str, replace_str: str) -> str:
        if attr_name not in self._module.__dict__:
            return f"attribute {attr_name} is not defined in this module"
        value = self._module.__dict__[attr_name]
        if not inspect.isclass(value) and not inspect.isfunction(value):
            return f"attribute {attr_name} is not class or function that can be replaced"
        source = inspect.getsource(value)
        ok = self.replace(source, replace_str, count=1)
        return source if ok else "replace failed"

    def save(self, module_info: Optional[ModuleInfo] = None) -> None:
        pass

    def get_module_info(self) -> ModuleInfo:
        pass

    def save_module_info(self, module_info: ModuleInfo) -> None:
        pass
