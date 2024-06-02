from __future__ import annotations

import enum
from abc import ABC, abstractmethod

from typing import List, Tuple, Iterator, ClassVar, Dict, Optional, TypeVar, Generic
from pydantic import BaseModel, Field
from ghostiss.context import Context
from ghostiss.messages import Message, Messenger, Attachment

"""
Dev logs: 

创建一个大模型的 API 设计. 基于 openai 的 API.
主要目的是让大模型的 API 调用本身可选择.  

"""


class ServiceConf(BaseModel):
    name: str = Field(description="Service name")
    base_url: str = Field(default="https://api.moonshot.cn/v1", description="llm service provider")
    api_key: str = Field(default="$MOONSHOT_API_KEY", description="api access key")


class ModelConf(BaseModel):
    service: str = Field(description="api service")
    model: str = Field(description="llm model name that service provided")
    temperature: float = Field(default=0.7, description="temperature")
    n: int = Field(default=1, description="number of iterations")
    max_tokens: int = Field(default=512, description="max tokens")
    timeout: float = Field(default=20, description="timeout")
    request_timeout: float = Field(default=40, description="request timeout")


class Tool(ABC, BaseModel):
    """
    openai function
    """
    tool_name: ClassVar[str]
    tool_desc: ClassVar[str]

    def as_function(self) -> Function:
        return Function(name=self.tool_name, desc=self.tool_desc, schema=self.model_json_schema())


class Function(BaseModel):
    name: str = Field(default="", description="Reaction name")
    desc: str = Field(default="", description="Reaction description")
    schema: Dict = Field(default={}, description="Reaction schema")


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


class ChatContext(BaseModel):
    # trace_id: str = Field(description="trace id")
    model: ModelConf = Field(description="llm model")
    service: Optional[ServiceConf] = Field(description="llm service")
    context: List[ChatMsg] = Field(default_factory=list)
    functions: Tool = Field(default_factory=list)
    function_call: str = Field(default="auto"),
    stop: Optional[List[str]] = Field(default=None)


class Run(BaseModel):
    """
    尝试运行一次线程.
    """
    model: ModelConf = Field(description="api configuration")
    service: Optional[ServiceConf] = Field(default=None, description="service configuration")

    instructions: str = Field(default="", description="system prompt")
    messages: List[Message] = Field(default_factory=list, description="可以指定不同的上下文来运行.")
    function_call: str = Field(default="auto"),
    functions: List[Function] = Field(default_factory=list)
    output_attachments: List[Attachment] = Field(default_factory=list)


class LLM(ABC):

    @abstractmethod
    def with_service_conf(self, service_conf: ServiceConf) -> "LLM":
        """
        get new api with the given service_conf and return new LLMAPI
        """
        pass

    @abstractmethod
    def with_api_conf(self, api_conf: ModelConf) -> "LLM":
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
            ctx: Context,
            chat_context: ChatContext,
    ) -> List[ChatMsg]:
        pass

    @abstractmethod
    def chat_completion_chunks(
            self,
            ctx: Context,
            chat_context: ChatContext,
    ) -> Iterator[ChatMsg]:
        """
        todo: 暂时先这么定义了.
        """
        pass


class LLMs(ABC):

    @abstractmethod
    def register_service(self, service_conf: ServiceConf) -> LLMs:
        pass

    @abstractmethod
    def register_api(self, name: str, model_conf: ModelConf) -> LLMs:
        pass

    @abstractmethod
    def services(self) -> List[ServiceConf]:
        pass

    @abstractmethod
    def each_api_conf(self) -> Iterator[Tuple[ServiceConf, ModelConf]]:
        pass

    @abstractmethod
    def new_api(self, service_conf: ServiceConf, api_conf: ModelConf) -> LLM:
        pass

    @abstractmethod
    def get_api(self, api_name: str, fail_if_none: bool = False, trace: Optional[Dict] = None) -> LLM | None:
        pass

    @abstractmethod
    def run(self, ctx: Context, run: Run, messenger: Messenger) -> None:
        """
        基于 chat completion 运行一个 run, 运行结果转换成 Message 然后通过 messenger 来发送.
        """
        pass

    @abstractmethod
    def run_to_chat(self, run: Run) -> ChatContext:
        pass
