from __future__ import annotations

import enum
from abc import ABC, abstractmethod

from typing import List, Tuple, Iterator, Dict, Optional, Any, Union
from pydantic import BaseModel, Field
from ghostiss.context import Context
from ghostiss.contracts.logger import LoggerItf
from ghostiss import helpers
from openai.types.chat import (
    completion_create_params,
    chat_completion_user_message_param,
    chat_completion_assistant_message_param,
    chat_completion_system_message_param,
)

"""
Dev logs: 

创建一个大模型的 API 设计. 基于 openai 的 API.
主要目的是让大模型的 API 调用本身可选择.  

"""

OPENAI_DRIVER_NAME = "ghostiss.llms.openai_driver"


# ---- config ---- #


class ModelConf(BaseModel):
    model: str = Field(description="llm model name that service provided")
    service: str = Field(description="llm service name")
    temperature: float = Field(default=0.7, description="temperature")
    n: int = Field(default=1, description="number of iterations")
    max_tokens: int = Field(default=512, description="max tokens")
    timeout: float = Field(default=20, description="timeout")
    request_timeout: float = Field(default=40, description="request timeout")


class ServiceConf(BaseModel):
    name: str = Field(description="Service name")
    driver: str = Field(default=OPENAI_DRIVER_NAME, description="driver name")
    base_url: str = Field(default="https://api.moonshot.cn/v1", description="llm service provider")
    token_key: str = Field(default="MOONSHOT_API_KEY", description="use token key to get token from env")
    token: str = Field(default="", description="token")
    # todo: 更多配置项以后再搞.


class LLMsConfig(BaseModel):
    services: List[ServiceConf] = Field(default_factory=list)
    models: Dict[str, ModelConf] = Field(default_factory=dict)


# ---- tool and function ---- #

class Function(BaseModel):
    name: str = Field(description="function name")
    desc: str = Field(default="", description="function description")
    parameters: Optional[Dict] = Field(default=None, description="function parameters")

    def to_openai(self) -> completion_create_params.Function:
        return completion_create_params.Function(**self.model_dump())


# ---- chat messages ---- #

class ChatRole(enum.Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"

    def new(self, content: str, name: Optional[str] = None, func_call: Optional[Dict] = None) -> LlmMsg:
        return LlmMsg(role=self.value, content=content, name=name, function_call=func_call)


class LlmKind(str, enum.Enum):
    TEXT = "text"
    TEXTS = "texts"
    IMAGE = "image"

OPENAI_CONTENT_TYPES = Union[
    str,

]

class LlmMsg(BaseModel):
    """
    OpenAI 接口的消息.
    """

    role: str = Field(enum={"system", "user", "assistant", "function"})
    content: str = ""
    kind: str = Field(enum={"text", "function", "image"})
    name: Optional[str] = None
    payload: Optional[Dict[str, Any]] = Field(default=None, description="对齐 openai 特殊类型. ")

    def say(self) -> LlmMsg:
        return LlmMsg(content=self.content, name=self.name, role=self.role, function_call=self.function_call)

    def get_openai_content(self) -> Union[str, ]:
        if self.kind == LlmKind.TEXT:
            pass
        elif self.kind == LlmKind.TEXTS:
            pass
        else:
            return self.content

    def to_openai(self) -> completion_create_params.ChatCompletionMessageParam:
        if self.role == ChatRole.USER:
            return chat_completion_user_message_param.ChatCompletionUserMessageParam(
                content=self.content, name=self.name, role="user",
            )
        elif self.role == ChatRole.SYSTEM:
            return chat_completion_system_message_param.ChatCompletionSystemMessageParam(
                content=self.content, name=self.name, role="system",
            )

    def to_message(self) -> Dict:
        data = self.model_dump(include={"role", "content", "name", "function_call"})
        # remove none values.
        result = helpers.dict_without_none(data)
        return result


# ---- api objects ---- #

class Chat(BaseModel):
    id: str = Field(default_factory=helpers.uuid, description="trace id")
    model: ModelConf = Field(description="llm model")
    service: Optional[ServiceConf] = Field(description="llm service")
    context: List[LlmMsg] = Field(default_factory=list)
    functions: List[Function] = Field(default_factory=list)
    function_call: str = Field(default="auto"),
    stop: Optional[List[str]] = Field(default=None)


# todo: 未来再做这些意义不大的.
# class Cast(BaseModel):
#     model: str = Field(description="llm model")
#     prompt_tokens: int = Field(description="prompt tokens")
#     total_tokens: int = Field(description="total tokens")
#     duration: float = Field(description="time duration")


class Embedding(BaseModel):
    content: str = Field(description="origin content")
    service: str = Field(description="llm service")
    model: str = Field(description="llm model")
    embedding: List[float] = Field(description="embedding")


class Embeddings(BaseModel):
    result: List[Embedding] = Field(default_factory=list)
    # todo: 未来再管这些.
    # cast: Cast = Field(description="cast")


class LLMApi(ABC):

    @abstractmethod
    def with_service(self, conf: ServiceConf) -> "LLMApi":
        pass

    @abstractmethod
    def with_model(self, api_conf: ModelConf) -> "LLMApi":
        """
        get new api with the given api_conf and return new LLMAPI
        """
        pass

    @abstractmethod
    def with_logger(self, logger: LoggerItf) -> "LLMApi":
        pass

    @abstractmethod
    def text_completion(self, ctx: Context, prompt: str) -> str:
        """
        deprecated text completion
        """
        pass

    @abstractmethod
    def get_embeddings(self, ctx: Context, text: List[str]) -> Embeddings:
        pass

    @abstractmethod
    def chat_completion(
            self,
            ctx: Context,
            chat: Chat,
    ) -> LlmMsg:
        pass

    @abstractmethod
    def chat_completion_chunks(
            self,
            ctx: Context,
            chat: Chat,
    ) -> Iterator[LlmMsg]:
        """
        todo: 暂时先这么定义了.
        """
        pass


class LLMDriver(ABC):

    @abstractmethod
    def driver_name(self) -> str:
        pass

    @abstractmethod
    def new(self, service: ServiceConf, model: ModelConf) -> LLMApi:
        pass


class LLMs(ABC):

    @abstractmethod
    def register_driver(self, driver: LLMDriver) -> None:
        pass

    @abstractmethod
    def register_service(self, service: ServiceConf) -> None:
        pass

    @abstractmethod
    def register_model(self, name: str, model_conf: ModelConf) -> None:
        pass

    @abstractmethod
    def services(self) -> List[ServiceConf]:
        pass

    @abstractmethod
    def each_api_conf(self) -> Iterator[Tuple[ServiceConf, ModelConf]]:
        pass

    @abstractmethod
    def new_api(self, service_conf: ServiceConf, api_conf: ModelConf) -> LLMApi:
        pass

    @abstractmethod
    def get_api(self, api_name: str, trace: Optional[Dict] = None) -> Optional[LLMApi]:
        pass

    def force_get_api(self, api_name: str, trace: Optional[Dict] = None) -> LLMApi:
        """
        sugar
        """
        api = self.get_api(api_name, trace)
        if api is None:
            raise NotImplemented("LLM API {} not implemented.".format(api_name))
        return api
