from __future__ import annotations

import os

from typing import List, Dict, Optional, Any, ClassVar
from pydantic import BaseModel, Field
from ghostos.core.messages import Payload

__all__ = [
    'ModelConf', 'ServiceConf', 'LLMsConfig',
    'OPENAI_DRIVER_NAME', 'LITELLM_DRIVER_NAME',
]

OPENAI_DRIVER_NAME = "openai_driver"
"""default llm driver name for OpenAI llm message protocol """

LITELLM_DRIVER_NAME = "lite_llm_Driver"


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
    message_types: Optional[List[str]] = Field(None, description="model allow message types")


class ServiceConf(BaseModel):
    """
    The service configuration of a llm.
    """
    name: str = Field(description="Service name")
    driver: str = Field(
        default=OPENAI_DRIVER_NAME,
        description="the adapter driver name of this service. ",
    )

    base_url: str = Field(description="llm service provider")
    token: str = Field(default="", description="token")
    proxy: Optional[str] = Field(default=None, description="proxy")

    def load(self, environ: Optional[Dict] = None) -> None:
        self.token = self._load_env(self.token, environ=environ)
        if self.proxy is not None:
            self.proxy = self._load_env(self.proxy, environ=environ)

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
        description="define llm services, such as openai or moonshot",
    )
    default: str = Field(description="one of the models key")
    models: Dict[str, ModelConf] = Field(
        default_factory=dict,
        description="define llm apis, the key is llm_api_name and value is model config of it.",
    )
