import inspect
from types import FunctionType, ModuleType
from typing import Union

from ghostos_container import Container

from ghostos.libraries.project.abcd import PyDevCtx
from ghostos_common.prompter import PromptObjectModel
from ghostos_common.helpers import get_code_interface_str, import_from_path, generate_import_path


class PyDevCtxData(PromptObjectModel, PyDevCtx):

    def read_interface(self, target: Union[str, FunctionType, ModuleType, type], *, watching: bool = False) -> str:
        try:
            if isinstance(target, str):
                import_path = target
                target = import_from_path(target)
            else:
                import_path = generate_import_path(target)
            source = inspect.getsource(target)
            interface = get_code_interface_str(source)

            if watching:
                try:
                    self.interfaces.index(import_path)
                except ValueError:
                    self.interfaces.append(import_path)
            return interface
        except Exception as e:
            return f"can't read interface of {target}, error: {e}"

    def read_source(self, target: Union[str, FunctionType, ModuleType, type], *, watching: bool = False) -> str:
        try:
            if isinstance(target, str):
                import_path = target
                target = import_from_path(target)
            else:
                import_path = generate_import_path(target)
            source = inspect.getsource(target)
            if watching:
                try:
                    self.sources.index(import_path)
                except ValueError:
                    self.sources.append(import_path)
            return source
        except Exception as e:
            return f"can't read interface of {target}, error: {e}"

    def full_context(self) -> str:
        context = f"""
the information from this PyDevCtx instance:

* title: `{self.title}`
* desc: `{self.desc}`
"""
        lines = [context]
        if len(self.instructions) > 0:
            lines.append(f"\ninstructions:")
            for key, instruction in self.instructions.items():
                lines.append(f"<instruction key=`{key}`>\n{instruction}\n</instruction>")
        if len(self.examples) > 0:
            lines.append(f"\nexamples:")
            for from_ in self.examples:
                source = self.read_source(from_, watching=False)
                lines.append(f"<example from=`{from_}`>\n{source}\n</example>")
        if len(self.notes) > 0:
            lines.append(f"\nnotes:")
            for key, note in self.notes.items():
                lines.append(f"<note key=`{key}`>\n{note}\n</note>")
        if len(self.interfaces) > 0:
            lines.append(f"\nwatching interfaces:")
            for interface in self.interfaces:
                interface_str = self.read_interface(interface, watching=False)
                lines.append(f"<interface from=`{interface}`>\n{interface_str}\n</interface>")
        if len(self.sources) > 0:
            lines.append(f"\nwatching sources:")
            for from_ in self.sources:
                source = self.read_source(from_, watching=False)
                lines.append(f"<source from=`{from_}`>\n{source}\n</source>")

        return "\n".join(lines)

    def self_prompt(self, container: Container) -> str:
        return self.full_context()

    def get_title(self) -> str:
        return self.title


if __name__ == "__main__":
    ctx = PyDevCtxData(
        title="hello",
        desc="world",
        instructions={"foo": "bar"},
        notes={"foo": "bar"},
        interfaces=[generate_import_path(get_code_interface_str)],
        sources=[generate_import_path(PromptObjectModel)],
        examples=[__name__],
    )
    print(ctx.full_context())
