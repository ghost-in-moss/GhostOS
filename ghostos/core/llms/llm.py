from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Tuple, Iterable, Optional
from ghostos.core.messages import Message, Stream
from ghostos.core.llms.configs import ModelConf, ServiceConf
from ghostos.core.llms.chat import Chat

__all__ = [
    'LLMs', 'LLMApi', 'LLMDriver',
]


class LLMApi(ABC):
    """
    uniform interface for large language models in GhostOS.
    """

    @abstractmethod
    def get_service(self) -> ServiceConf:
        """
        get the service configuration of this API
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
        if not deliver.accept_chunks():
            message = self.chat_completion(chat)
            if message.is_complete():
                # add model conf as message payload
                self.get_model().set(message)
            deliver.deliver(message)
            return
        items = self.chat_completion_chunks(chat)
        # todo: payload 要计算 tokens
        for item in items:
            if item.is_complete():
                # add model conf as message payload
                self.get_model().set(item)
            deliver.deliver(item)


class LLMDriver(ABC):
    """
    LLMDriver is the adapter class to wrap the large language models API to LLMApi.
    The basic LLMDriver shall be openai driver, compatible to all the llms fit the openai message protocol.
    """

    @abstractmethod
    def driver_name(self) -> str:
        pass

    @abstractmethod
    def new(self, service: ServiceConf, model: ModelConf) -> LLMApi:
        pass


class LLMs(ABC):
    """
    The repository of LLMApis.
    """

    @abstractmethod
    def register_driver(self, driver: LLMDriver) -> None:
        """
        register a driver for a server.
        """
        pass

    @abstractmethod
    def register_service(self, service: ServiceConf) -> None:
        """
        register a service by config
        """
        pass

    @abstractmethod
    def register_model(self, name: str, model_conf: ModelConf) -> None:
        """
        register a model conf, and it's service shall already exist.
        """
        pass

    @abstractmethod
    def services(self) -> List[ServiceConf]:
        """
        iterate all configured services.
        """
        pass

    @abstractmethod
    def get_service(self, name: str) -> Optional[ServiceConf]:
        """
        get service instance by name.
        """
        pass

    @abstractmethod
    def each_api_conf(self) -> Iterable[Tuple[ServiceConf, ModelConf]]:
        """
        iterate all configured api confs.
        """
        pass

    @abstractmethod
    def new_api(self, service_conf: ServiceConf, api_conf: ModelConf) -> LLMApi:
        """
        instance a LLMApi by configs.
        """
        pass

    @abstractmethod
    def get_api(self, api_name: str) -> Optional[LLMApi]:
        """
        get a defined api by name, which shall be defined in ghostos.core.llms.configs.LLMsConfig .
        """
        pass

    def force_get_api(self, api_name: str) -> LLMApi:
        """
        sugar, raise exception when api_name is not defined.
        """
        api = self.get_api(api_name)
        if api is None:
            raise NotImplemented("LLM API {} not implemented.".format(api_name))
        return api
