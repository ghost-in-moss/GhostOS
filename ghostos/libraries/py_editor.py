import inspect
from typing import Optional
from types import ModuleType
from abc import ABC, abstractmethod

__all__ = ['PythonEditor', 'ModuleEditor', 'PythonEditorImpl', 'ModuleEditorImpl']


class PythonEditor(ABC):
    """
    python editor that can edit python module's code
    """

    @abstractmethod
    def module(self, module: str) -> "ModuleEditor":
        """
        use module name to new an ModuleEditor instance.
        :param module: module name such as foo.bar.baz
        :exception: ModuleNotFoundError
        """
        pass


class ModuleEditor(ABC):
    """
    module editor that instance from a target module.
    can edit the target module's contents.
    """

    @abstractmethod
    def filepath(self) -> str:
        """
        :return: filepath of the target module
        """
        pass

    @abstractmethod
    def modulename(self) -> str:
        """
        :return: module name of the module that this editor is editing
        """
        pass

    @abstractmethod
    def read_source(
            self,
            show_line_num: bool = True,
            start_line: int = 0,
            end_line: int = -1,
    ) -> str:
        """
        read source code from this module
        :param show_line_num: show line number at the end of each line such as # 44
        :param start_line: start line number
        :param end_line: end line number, if < 0, means end line number
        :return: source code
        """
        pass

    @abstractmethod
    def read_source_of_imported(
            self,
            attr_name: str,
            detail: bool = False,
    ) -> str:
        """
        read a imported attribute's source code.
        :param attr_name: the attribute's name of the target in this module
        :param detail: if True, show source code; if False, show signature only
        :return: full source code, or a simple string describe it.
        """
        pass

    @abstractmethod
    def replace(
            self,
            target_str: str,
            replace_str: str,
            count: int = -1
    ) -> bool:
        """
        replace the source code of this module by replace a specific string
        :param target_str: target string in the source code
        :param replace_str: replacement
        :param count: if -1, replace all occurrences of replace_str, else only replace occurrences count times.
        :return: if not ok, means target string is missing
        """
        pass

    @abstractmethod
    def replace_block(
            self,
            start_line: int,
            end_line: int,
            replace_str: str,
    ) -> str:
        """
        replace a block of source code
        :param start_line: the start line number of the block.
        :param end_line: the end line number of the block, included.
        :param replace_str: replacement
        :return: the replaced source code, if empty, means target block is missing
        """
        pass

    @abstractmethod
    def replace_attr(
            self,
            attr_name: str,
            replace_str: str,
    ) -> str:
        """
        replace a module attribute's source code.
        the target attribute shall be a class or a function.
        :param attr_name: name of the target attribute of this module. It MUST be defined in this module, not imported.
        :param replace_str: new source code
        :return: the replaced source code. if empty, means target attribute is missing
        """
        pass

    @abstractmethod
    def append(self, source: str) -> None:
        """
        append source code to this module.
        :param source: the source code of class / function / assignment
        """
        pass

    @abstractmethod
    def insert(self, source: str, line_num: int) -> None:
        """
        insert source code to this module at line number.
        remember following the python code format pattern.
        :param source: the inserting code, such like from ... import ... or others.
        :param line_num: the start line of the insertion
        """
        pass


class ModuleEditorImpl(ModuleEditor):

    def __init__(self, module: ModuleType, filename: str, source_code: Optional[str] = None):
        self._module = module
        self._module_file = filename
        self._module_source: Optional[str] = source_code

    def filepath(self) -> str:
        return self._module_file

    def modulename(self) -> str:
        return self._module.__name__

    def _get_module_source(self) -> str:
        if self._module_source is None:
            self._module_source = inspect.getsource(self._module)
        return self._module_source

    def _save_module_source(self, source: str) -> None:
        self._module_source = source
        new_module = ModuleType(self._module.__name__)
        new_module.__dict__['__file__'] = self._module_file
        exec(source, new_module.__dict__)
        self._module = new_module
        with open(self._module_file, "w") as f:
            f.write(source)

    def read_source(self, show_line_num: bool = True, start_line: int = 0, end_line: int = -1) -> str:
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

    def read_source_of_imported(self, attr_name: str, detail: bool = False) -> str:
        if attr_name not in self._module.__dict__:
            return f"attribute {attr_name} is not defined in this module"
        value = self._module.__dict__[attr_name]
        if not inspect.isclass(value) and not inspect.isfunction(value):
            return f"attribute {attr_name} is not a function or class, can't get source, just print it"
        if getattr(value, "__module__") == self.modulename():
            return f"attribute {attr_name} is not imported, but local defined"
        return inspect.getsource(value)

    def replace(self, target_str: str, replace_str: str, count=-1) -> bool:
        if target_str not in self._module_source:
            return False
        source = self._module_source.replace(target_str, replace_str, count)
        self._save_module_source(source)
        return True

    def replace_block(self, start_line: int, end_line: int, replace_str: str) -> str:
        block = self.read_source(show_line_num=False, start_line=start_line, end_line=end_line)
        if not block:
            return ""
        ok = self.replace(block, replace_str)
        return block if ok else ""

    def replace_attr(self, attr_name: str, replace_str: str) -> str:
        if attr_name not in self._module.__dict__:
            return f"attribute {attr_name} is not defined in this module"
        value = self._module.__dict__[attr_name]
        if not inspect.isclass(value) and not inspect.isfunction(value):
            return f"attribute {attr_name} is not class or function that can be replaced"
        source = inspect.getsource(value)
        ok = self.replace(source, replace_str, count=1)
        return source if ok else "replace failed"

    def append(self, source: str) -> None:
        source = source.strip()
        saving = self._module_source.rstrip("\n")
        saving = saving + "\n\n" + source + "\n"
        self._save_module_source(saving)

    def insert(self, source: str, line_num: int) -> None:
        lines = self._module_source.splitlines()
        outputs = []
        idx = -1
        for line in lines:
            idx += 1
            if line_num == idx:
                outputs.append(source)
            outputs.append(line)
        replace = "\n".join(outputs)
        self._save_module_source(replace)


class PythonEditorImpl(PythonEditor):

    def module(self, module: str) -> "ModuleEditor":
        from importlib import import_module
        target = import_module(module)
        filename = target.__file__
        with open(filename, "r") as f:
            source = f.read()
            temp_module = ModuleType(target.__name__)
            temp_module.__dict__['__file__'] = filename
            exec(source, temp_module.__dict__)
            return ModuleEditorImpl(temp_module, target.__file__, source)
