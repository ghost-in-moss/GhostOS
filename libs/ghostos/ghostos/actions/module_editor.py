from typing import Union, Optional, ClassVar

from abcd import Session, Operator
from core.llms import Prompt, LLMFunc
from core.messages import FunctionCaller
from ghostos.abcd import Action
from pydantic import BaseModel, Field
from ghostos_moss import Modules
import json


class PyModuleAppendAction(Action):
    """
    append code to a module
    """
    func_name: ClassVar[str] = "pymodule-append"
    func_desc: ClassVar[str] = "append a piece of code into the module"

    class Argument(BaseModel):
        modulename: str = Field(description="the updating modulename")
        code: str = Field(description="the appending code")
        reload: bool = Field(default=False, description="reload the code")

    def __init__(
            self,
            modules: Modules,
    ):
        self._modules = modules

    def name(self) -> str:
        return "module-append"

    def as_function(self) -> Optional[LLMFunc]:
        return LLMFunc.new(
            self.name(),
            self.func_desc,
            self.Argument.model_json_schema(),
        )

    def update_prompt(self, prompt: Prompt) -> Prompt:
        prompt.functions.append(self.as_function())
        return prompt

    def run(self, session: Session, caller: FunctionCaller) -> Union[Operator, None]:
        try:
            data = json.loads(caller.arguments)
            argument = self.Argument(**data)
            self.do_update(argument)

        except Exception as e:
            error_message = caller.new_output(f"Failed: {e}")
            session.respond([error_message])
        finally:
            return session.mindflow().think()

    def do_update(self, argument: Argument) -> None:
        self._modules.save_source(argument.modulename, argument.code, argument.reload)
