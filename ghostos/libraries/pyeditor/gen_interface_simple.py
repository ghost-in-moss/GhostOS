from typing import Any, Optional
from typing_extensions import is_protocol, is_typeddict
from ghostos.libraries.pyeditor.abcd import PyInterfaceGenerator
from ghostos_moss.prompts import reflect_code_prompt
from ghostos_container import Container, Provider
from ghostos_common.helpers import get_code_interface
import inspect


class SimplePyInterfaceGenerator(PyInterfaceGenerator):

    def generate_interface(
            self,
            value: Any,
    ) -> str:
        prompt = reflect_code_prompt(value)
        if prompt is not None:
            return prompt
        try:
            code = inspect.getsource(value)
            return "\n\n".join(get_code_interface(code))
        except Exception as e:
            return "# parse code interface failed: {}".format(e)


class SimplePyInterfaceGeneratorProvider(Provider[PyInterfaceGenerator]):

    def singleton(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[PyInterfaceGenerator]:
        return SimplePyInterfaceGenerator()
