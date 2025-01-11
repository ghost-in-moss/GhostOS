from __future__ import annotations

import os

from typing import List, Dict, Optional, Any, ClassVar
from typing_extensions import Literal
from pydantic import BaseModel, Field
from ghostos.core.messages import Payload

# from ghostos.helpers import gettext as _

__all__ = [
    'ModelConf', 'ServiceConf', 'LLMsConfig',
    'OPENAI_DRIVER_NAME', 'LITELLM_DRIVER_NAME',
]

OPENAI_DRIVER_NAME = "openai_driver"
"""default llm driver name for OpenAI llm message protocol """

LITELLM_DRIVER_NAME = "lite_llm_driver"


class Reasonable(BaseModel):
    """
    the OpenAI reasoning configs adapter
    """
    effort: Literal["low", "medium", "high"] = Field(
        "medium",
        description="reasoning effort level",
    )


class ModelConf(Payload):
    """
    the basic configurations for a LLMS model
    todo: more fields
    """
    key: ClassVar[str] = "model_conf"

    model: str = Field(description="llm model name that service provided")
    service: str = Field(description="llm service name")
    temperature: float = Field(default=0.7, description="temperature")
    n: int = Field(default=1, description="number of iterations")
    max_tokens: int = Field(default=2000, description="max tokens")
    timeout: float = Field(default=30, description="timeout")
    request_timeout: float = Field(default=40, description="request timeout")
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="kwargs")
    use_tools: bool = Field(default=True, description="use tools")
    max_completion_tokens: Optional[int] = Field(
        None,
        description="max completion tokens",
    )
    message_types: Optional[List[str]] = Field(None, description="model allow message types")
    allow_streaming: bool = Field(True, description="if the current model allow streaming")
    reasoning: Optional[Reasonable] = Field(
        default=None,
        description="reasoning configuration",
    )

    payloads: Dict[str, Dict] = Field(
        default_factory=dict,
        description="custom payload objects. save strong typed but optional dict."
                    "see ghostos.core.messages.Payload class."
    )


class Compatible(BaseModel):
    use_developer_role: bool = Field(default=False, description="use developer role instead of system")
    allow_system_in_messages: bool = Field(default=True, description="allow system messages in history")


class Azure(BaseModel):
    api_key: str = Field(default="", description="azure api key. if start with `$`, will read environment variable of it")
    api_version: str = Field(default="", description="azure api version")


class ServiceConf(BaseModel):
    """
    The model api service configuration
    """

    name: str = Field(description="Service name")
    base_url: str = Field(description="LLM service url. if start with `$`, will read environment variable of it")
    token: str = Field(default="", description="access token. if start with `$`, will read environment variable of it")
    proxy: Optional[str] = Field(
        default=None,
        description="service proxy. if start with `$`, will read environment variable of it",
    )

    driver: str = Field(
        default=OPENAI_DRIVER_NAME,
        description="the adapter driver name of this service. change it only if you know what you are doing",
    )

    compatible: Compatible = Field(
        default_factory=Compatible,
        description="the model api compatible configuration",
    )

    azure: Azure = Field(
        default_factory=Azure,
        description="azure service configuration",
    )

    def load(self, environ: Optional[Dict] = None) -> None:
        attributes = [(self, 'base_url'), (self, 'token'), (self, 'proxy'), (self.azure, 'api_key')]
        for obj, attr in attributes:
            value = getattr(obj, attr)
            if value is not None:
                setattr(obj, attr, self._load_env(value, environ=environ))

    @staticmethod
    def _load_env(value: str, environ: Optional[Dict] = None) -> str:
        if value.startswith("$"):
            value_key = value[1:]
            if environ is None:
                environ = os.environ
            value = environ.get(value_key, "")
        return value


class LLMsConfig(BaseModel):
    """
    llms configurations for ghostos.core.llms.llm:LLMs default implementation.
    """

    services: List[ServiceConf] = Field(
        default_factory=list,
        description="The Model Services (like OpenAI, Anthropic, Moonshot) configuration.",
    )

    default: str = Field(
        description="GhostOS default model name, corporate with models config",
    )
    models: Dict[str, ModelConf] = Field(
        default_factory=dict,
        description="define LLM APIs, from model name to model configuration.",
    )
