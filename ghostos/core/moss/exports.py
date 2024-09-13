from typing import Any, Dict, Iterable, Tuple, Optional, Callable, List
from ghostos.core.moss.utils import make_class_prompt, get_callable_definition
import inspect

__all__ = ['Exporter']


class Exporter(object):
    """
    Exporter is useful to export multiple objects with prompts from a module
    The Subject module can import a exporter instance from a object module,
    the prompt generate from the exporter like this:

    > from foo.bar import baz
    >
    > # value of baz.a
    > class A:
    >     ...
    > # value of baz.b
    > def B():
    >     ...

    Exporter is harmless then the moss decorators.
    """

    def __init__(self, **kwargs):
        self._prompts: Dict[str, str] = {}
        # with kwargs values
        for name, value in kwargs.items():
            if isinstance(value, Exporter):
                self.with_exporter(name, value)
            elif inspect.isclass(value):
                self.with_class(value, name=name)
            elif inspect.isfunction(value):
                self.with_func(value, name=name)
            else:
                self.with_raw(name, value, "")

    def prompts(self) -> Iterable[Tuple[str, str]]:
        """
        iterate the attr's prompt of the Exporter
        :return: A generator that yields tuples of attr name and prompt value in the Exporter.
        """
        return self._prompts.items()

    def gene_prompt(self, self_name: str) -> str:
        """
        this method is used in other module.
        generate prompt for the Exporter with a attribute name in other module.
        :param self_name: attribute name of the Exporter in other module.
        :return: full prompt
        """
        lines = []
        for attr, prompt in self.prompts():
            comment = f"# value of {self_name}.{attr}"
            lines.append(f"{comment}:\n{prompt}")
        return "\n\n".join(lines)

    def with_raw(self, name: str, value: Any, prompt: str) -> "Exporter":
        """
        add a attribute to the Exporter with a specific prompt.
        :param name: attribute name in the Exporter
        :param value: real value
        :param prompt: predefined prompt
        :return: self, chain calling.
        """
        if name in self.__dict__:
            raise NameError(f"'{name}' already exists in Exporter")
        self.__dict__[name] = value
        if not prompt:
            prompt = f"# {value}"
        self._prompts[name] = prompt
        return self

    def with_class(self, cls: type, *, abc: Optional[type] = None, name: Optional[str] = None) -> "Exporter":
        """
        add a class attribute to the Exporter. prompt will be the class source code.
        :param cls: the class type
        :param abc: if given, the prompt is the abc class's source code
        :param name: if not given, the attribute name will be the class name
        :return: self, chain calling.
        """
        if abc is not None:
            prompt = inspect.getsource(abc)
        else:
            prompt = inspect.getsource(cls)
        if name is None:
            name = cls.__name__
        return self.with_raw(name, cls, prompt)

    def with_interface(
            self,
            cls: type,
            members: Optional[List[str]] = None,
            *,
            doc: Optional[str] = None,
            name: Optional[str] = None,
    ) -> "Exporter":
        """
        add a class attribute to the Exporter.
        prompt will be interface pattern, which means class definition plus public method definitions.

        :param cls: the value class
        :param members: method name that should be added. if none, all public methods will be added.
        :param doc: if given, replace the class docstring in the prompt
        :param name: if not given, using class name as attribute name
        """
        if name is None:
            name = cls.__name__
        source = inspect.getsource(cls)
        prompt = make_class_prompt(source=source, name=name, attrs=members, doc=doc)
        return self.with_raw(name, cls, prompt)

    def with_func(self, func: Callable, *, doc: Optional[str] = None, name: Optional[str] = None) -> "Exporter":
        """
        add a function attribute to the Exporter. prompt will be the function definition and doc.
        :param func:
        :param doc: if given, the function's doc in the prompt will be replaced by the argument.
        :param name: if not given, the attribute name will be the function name
        """
        prompt = get_callable_definition(func, doc=doc)
        if name is None:
            name = func.__name__
        return self.with_raw(name, func, prompt)

    def with_exporter(self, name: str, value: "Exporter") -> "Exporter":
        """
        add another exporter to the Exporter.
        prompt of each attribute in the value will be handled like:
        self_name.self_attr_name.value_attr_name => prompt
        """
        for attr, prompt in value.prompts():
            real_name = f"{name}.{attr}"
            self._prompts[real_name] = prompt
        self.__dict__[name] = value
        return self


# --- tests --- #

class Foo:

    def foo(self):
        return 123


class Bar(Foo):
    pass


tester = (Exporter(Any=Any, Dict=Dict)
          .with_interface(Exporter, ['with_func'], name="exp1")
          .with_class(Foo, name="foo")
          .with_class(Bar, abc=Foo)
          .with_func(make_class_prompt)
          .with_func(make_class_prompt, name="make_cls_pr", doc="hello"))


def test_each_value_of_tester():
    values = {
        "Any": Any,
        "Dict": Dict,
        "exp1": Exporter,
        "foo": Foo,
        "make_class_prompt": make_class_prompt,
        "make_cls_pr": make_class_prompt,
    }
    for attr, value in values.items():
        assert getattr(tester, attr) is value


def test_gen_prompt():
    print(tester.gene_prompt("tester"))
