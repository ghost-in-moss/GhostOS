from abc import ABC
from typing import Iterable, Tuple, Any
from ghostos_moss.prompts import reflect_code_prompt, join_prompt_lines
from ghostos_moss.utils import add_source_indent, escape_string_quotes
import inspect

__all__ = ['Exporter', 'is_exports']


class Exporter(ABC):
    """
    class that exports function, method and class of a module.
    and moss.get_imported_attr_prompts will reflect all the attributes assign to the Exports subclass.

    How to:

    1. module `Foo` define an Exports subclass for other module to import:
    ```python
    from ghostos_moss import Exports
    class Foo:
        ...

    class Exports(AbsExports):
        Foo = Foo
    ```

    2. module `Bar` import the Exports and use it:

    ```python
    from foo import Exports

    my_foo = Exports.Foo()
    ```

    3. MossPrompter.get_imported_attr_prompts() can get the exported attributes code interfaces from it:

    ```python
    with compiler:
        runtime = compiler.compile("bar")
        assert `class Exports` in runtime.prompter().get_imported_attr_prompts()
    ```
    """

    @classmethod
    def __attrs_prompts__(cls) -> Iterable[Tuple[str, str]]:
        """
        override this method to define str prompt for attribute
        :return: Iterable[(attr_name, attr_prompt)]
        """
        return []

    @classmethod
    def __exports__(cls) -> Iterable[Tuple[str, Any]]:
        """
        iterate exports attributes
        """
        attrs = dir(cls)
        for attr in attrs:
            if attr.startswith("_"):
                continue
            value = getattr(cls, attr, None)
            if value is None:
                continue
            yield attr, value

    @classmethod
    def __class_prompt__(cls) -> str:
        if cls is Exporter:
            return ""
        source = inspect.getsource(cls)
        attr_prompts = {}
        for prop, prompt in cls.__attrs_prompts__():
            attr_prompts[prop] = prompt

        for attr, value in cls.__exports__():
            try:
                attr_interface = reflect_code_prompt(value)
            except Exception:
                continue

            if attr_interface:
                attr_prompts[attr] = attr_interface

        blocks = []
        for name, prompt in attr_prompts.items():
            value = getattr(cls, name, None)
            if value is None:
                continue
            module_info = ""
            if hasattr(value, "__module__"):
                module_info = f" module=`{value.__module__}`"

            lines = [
                f"#<attr name=`{name}`{module_info}>",
                prompt,
                f"#</attr>",
            ]
            blocks.append("\n".join(lines))
        if not blocks:
            return source
        self_name = cls.__name__
        appending = join_prompt_lines(*blocks)
        appending = escape_string_quotes(appending, '"""')
        appending = "\n".join([f'"""\n#attrs of `{self_name}` are:', appending, '"""'])
        appending = add_source_indent(appending, 4)
        return join_prompt_lines(source.rstrip(), appending)


def is_exports(obj) -> bool:
    return issubclass(obj, Exporter)


class _ExportsExample(Exporter):
    """
    example of Exports.
    the source code and
    """
    getsource = inspect.getsource
    Exports = Exporter
