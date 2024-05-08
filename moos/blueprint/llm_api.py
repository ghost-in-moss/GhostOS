from __future__ import annotations

import enum
from abc import ABC, abstractmethod

from moos import helpers
from typing import List, Tuple, Iterator, ClassVar, Dict, Optional
from pydantic import BaseModel, Field

"""
Dev logs: 

创建一个大模型的 API 设计. 基于 openai 的 API.
主要目的是让大模型的 API 调用本身可选择.  

"""


class ServiceConf(BaseModel):
    name: str = Field(description="Service name")
    base_url: str = Field(default="https://api.moonshot.cn/v1", description="llm service provider")
    api_key: str = Field(default="$MOONSHOT_API_KEY", description="api access key")


class APIConf(BaseModel):
    name: str = Field(description="api name")
    model: str = Field(description="llm model name that service provided")
    temperature: float = Field(default=0.7, description="temperature")
    n: int = Field(default=1, description="number of iterations")
    max_tokens: int = Field(default=512, description="max tokens")
    timeout: float = Field(default=20, description="timeout")
    request_timeout: float = Field(default=40, description="request timeout")


class Function(ABC, BaseModel):
    """
    openai function
    """
    func_name: ClassVar[str]
    func_desc: ClassVar[str]


class ChatRole(enum.Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"

    def new(self, content: str, name: str | None = None) -> ChatMsg:
        return ChatMsg(role=self.value, content=content, name=name)


class ChatMsg(BaseModel):
    """
    OpenAI 接口的消息.
    """

    role: str = Field(enum={"system", "user", "assistant", "function"})
    content: str = ""
    name: str | None = None
    function_call: Dict | None = None

    def say(self) -> ChatMsg:
        return ChatMsg(content=self.content, name=self.name, role=self.role, function_call=self.function_call)

    def to_message(self) -> Dict:
        data = self.model_dump(include={"role", "content", "name", "function_call"})
        result = helpers.dict_without_none(data)
        return result


class LLMAPI(ABC):

    @abstractmethod
    def with_service_conf(self, service_conf: ServiceConf) -> "LLMAPI":
        """
        get new api with the given service_conf and return new LLMAPI
        """
        pass

    @abstractmethod
    def with_api_conf(self, api_conf: APIConf) -> "LLMAPI":
        """
        get new api with the given api_conf and return new LLMAPI
        """
        pass

    @abstractmethod
    def text_completion(self, prompt: str, config_name: str = "") -> str:
        """
        同步接口. 未来还需要实现异步接口.
        """
        pass

    @abstractmethod
    def text_embedding(self, text: str, config_name: str = "") -> List[float]:
        pass

    @abstractmethod
    def chat_completion(
            self,
            chat_context: List[ChatMsg],
            functions: List[Function] | None = None,
            function_call: str = "",
            stop: List[str] | None = None,
    ) -> ChatMsg:
        pass

    @abstractmethod
    def async_chat_completion(
            self,
            chat_context: List[ChatMsg],
            functions: List[Function] | None = None,
            function_call: str = "",
            stop: List[str] | None = None,
    ) -> Iterator[ChatMsg]:
        """
        todo: 暂时先这么定义了.
        """
        pass


class LLMRepository(ABC):

    @abstractmethod
    def register_service(self, service_conf: ServiceConf) -> LLMRepository:
        pass

    @abstractmethod
    def register_model(self, api_conf: APIConf) -> LLMRepository:
        pass

    @abstractmethod
    def services(self) -> List[ServiceConf]:
        pass

    @abstractmethod
    def each_api_conf(self) -> Iterator[Tuple[ServiceConf, APIConf]]:
        pass

    @abstractmethod
    def new_api(self, service_conf: ServiceConf, api_conf: APIConf, trace: Optional[Dict] = None) -> LLMAPI:
        pass

    @abstractmethod
    def get_api(self, api_name: str, fail_if_none: bool = False, trace: Optional[Dict] = None) -> LLMAPI | None:
        pass
