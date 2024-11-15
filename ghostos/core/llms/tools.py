from __future__ import annotations

from enum import Enum

from typing import Dict, Optional, Type

from pydantic import BaseModel, Field
from ghostos.identifier import Identical, Identifier
from ghostos.core.messages import Caller


# ---- tool and function ---- #

class LLMFunc(BaseModel):
    """
    a common wrapper for JSONSchema LLM tool.
    Compatible to OpenAI Tool.
    We need this because OpenAI Tool definition is too dynamic, we need strong typehints.
    """
    id: Optional[str] = Field(default=None, description="The id of the LLM tool.")
    name: str = Field(description="function name")
    description: str = Field(default="", description="function description")
    parameters: Optional[Dict] = Field(default=None, description="function parameters")

    @classmethod
    def new(cls, name: str, desc: Optional[str] = None, parameters: Optional[Dict] = None):
        if parameters is None:
            parameters = {"type": "object", "properties": {}}
        properties = parameters.get("properties", {})
        params_properties = {}
        for key in properties:
            _property = properties[key]
            if "title" in _property:
                del _property["title"]
            params_properties[key] = _property
        parameters["properties"] = params_properties
        if "title" in parameters:
            del parameters["title"]
        return cls(name=name, description=desc, parameters=parameters)

    @classmethod
    def from_model(
            cls,
            name: str,
            model: Type[BaseModel],
            description: Optional[str] = None,
    ):
        if description is None:
            description = model.__doc__
        return cls.new(name, desc=description, parameters=model.model_json_schema())


# todo: remove

class FunctionalTokenMode(str, Enum):
    XML = "xml"
    """ xml 模式, 使用 <name> </name> 包起来的是内容. """
    TOOL = "tool"
    """ tool mod, 使用 llm tool 进行封装. """
    TOKEN = "token"
    """ token mod. use single token to parse content. """


class FunctionalToken(Identical, BaseModel):
    """
    functional token means to provide function ability to LLM not by JsonSchema, but by token.
    LLM generates special tokens (such as XML marks) to indicate further tokens are the content of the function.
    LLMDriver shall define which way to prompt the functional token usage such as xml.
    """

    token: str = Field(description="token that start the function content output")
    end_token: str = Field(default="", description="end token that close the function content output")
    name: str = Field(description="name of the function")
    description: str = Field(default="", description="description of the function")
    visible: bool = Field(default=False, description="if the functional token and the parameters are visible to user")
    parameters: Optional[Dict] = Field(default=None, description="functional token parameters")

    def new_caller(self, arguments: str) -> "Caller":
        """
        generate new caller by functional token, usually used in tests.
        """
        return Caller(
            name=self.name,
            arguments=arguments,
            functional_token=True,
        )

    def __identifier__(self) -> Identifier:
        """
        identifier of the functional token.
        """
        return Identifier(
            name=self.name,
            description=self.description,
        )

    def as_tool(self) -> LLMFunc:
        """
        all functional token are compatible to a llm tool.
        """
        return LLMFunc.new(name=self.name, desc=self.description, parameters=self.parameters)