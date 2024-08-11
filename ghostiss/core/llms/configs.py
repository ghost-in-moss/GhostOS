from __future__ import annotations

import os

from typing import List, Dict, Optional, Any, ClassVar

from pydantic import BaseModel, Field
from ghostiss.core.messages import Payload

__all__ = [
    'ModelConf', 'ServiceConf', 'LLMsConfig', 'OPENAI_DRIVER_NAME',
]

OPENAI_DRIVER_NAME = "ghostiss.llms.openai_driver"


class ModelConf(Payload):
    """
    模型的配置. 同时可以直接加入到消息体里.
    """
    key: ClassVar[str] = "model_conf"

    model: str = Field(description="llm model name that service provided")
    service: str = Field(description="llm service name")
    temperature: float = Field(default=0.7, description="temperature")
    n: int = Field(default=1, description="number of iterations")
    max_tokens: int = Field(default=2000, description="max tokens")
    timeout: float = Field(default=20, description="timeout")
    request_timeout: float = Field(default=40, description="request timeout")
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="kwargs")


class EmbedConf(BaseModel):
    service: str = Field(description="service name, share with llm model conf")
    model: str = Field(description="the model name that provide embeddings")


class ServiceConf(BaseModel):
    """
    服务的配置.
    """
    name: str = Field(description="Service name")
    driver: str = Field(default=OPENAI_DRIVER_NAME, description="driver name")
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
    所有的配置项.
    一种可选的方式.
    """
    services: List[ServiceConf] = Field(
        default_factory=list,
        description="定义各种 llm services, 比如 openai 或者 moonshot",
    )
    default: ModelConf = Field(
        description="定义默认的 llm api.",
    )
    models: Dict[str, ModelConf] = Field(
        default_factory=dict,
        description="定义多个 llm api, key 就是 api name. "
    )
    embed_models: Dict[str, EmbedConf] = Field(
        default_factory=dict,
        description="定义多个 embed api, key 就是 api name. "
    )
