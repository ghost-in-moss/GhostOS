from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Tuple, Iterable, Optional
from ghostiss.core.messages import Message, Stream
from ghostiss.core.llms.configs import ModelConf, ServiceConf
from ghostiss.core.llms.chat import Chat

__all__ = [
    'LLMs', 'LLMApi', 'LLMDriver',
]


class LLMApi(ABC):

    @abstractmethod
    def get_service(self) -> ServiceConf:
        """
        """
        pass

    @abstractmethod
    def get_model(self) -> ModelConf:
        """
        get new api with the given api_conf and return new LLMAPI
        """
        pass

    @abstractmethod
    def parse_chat(self, chat: Chat) -> Chat:
        """
        parse chat by llm api default logic. Functional tokens for example.
        this method is used to test.
        """
        pass

    @abstractmethod
    def text_completion(self, prompt: str) -> str:
        """
        deprecated text completion
        """
        pass

    @abstractmethod
    def chat_completion(self, chat: Chat) -> Message:
        pass

    @abstractmethod
    def chat_completion_chunks(self, chat: Chat) -> Iterable[Message]:
        """
        todo: 暂时先这么定义了.
        """
        pass

    def deliver_chat_completion(self, chat: Chat, deliver: Stream) -> None:
        """
        逐个发送消息的包.
        """
        items = self.chat_completion_chunks(chat)
        # todo: payload 要计算 tokens
        for item in items:
            deliver.deliver(item)


class LLMDriver(ABC):
    """
    LLM 的驱动. 比如 OpenAI 基本都使用 OpenAI 库作为驱动.
    但是其它的一些大模型, 比如文心一言, 有独立的 API 设计.
    """

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
    def get_service(self, name: str) -> Optional[ServiceConf]:
        pass

    @abstractmethod
    def each_api_conf(self) -> Iterable[Tuple[ServiceConf, ModelConf]]:
        pass

    @abstractmethod
    def new_api(self, service_conf: ServiceConf, api_conf: ModelConf) -> LLMApi:
        pass

    @abstractmethod
    def get_api(self, api_name: str) -> Optional[LLMApi]:
        pass

    def force_get_api(self, api_name: str) -> LLMApi:
        """
        sugar
        """
        api = self.get_api(api_name)
        if api is None:
            raise NotImplemented("LLM API {} not implemented.".format(api_name))
        return api
