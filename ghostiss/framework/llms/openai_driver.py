from typing import List, Iterable, Union, Optional

from openai import OpenAI
from httpx import Client
from httpx_socks import SyncProxyTransport
from openai import NOT_GIVEN
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion_stream_options_param import ChatCompletionStreamOptionsParam
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

from ghostiss.blueprint.errors import GhostissIOError
from ghostiss.blueprint.messages import Message, OpenAIParser, DefaultOpenAIParser
from ghostiss.blueprint.kernel.llms import LLMs, LLMDriver, LLMApi, ModelConf, ServiceConf, OPENAI_DRIVER_NAME
from ghostiss.blueprint.kernel.llms import Chat
from ghostiss.blueprint.kernel.llms import Embedding, Embeddings
from ghostiss.container import Bootstrapper, Container

__all__ = ['OpenAIDriver', 'OpenAIAdapter', 'OpenAIDriverBootstrapper']


class OpenAIAdapter(LLMApi):
    """
    adapter class wrap openai api to ghostiss.blueprint.kernel.llms.LLMApi
    """

    def __init__(
            self,
            service_conf: ServiceConf,
            model_conf: ModelConf,
            parser: OpenAIParser,
    ):
        self._service = service_conf
        self._model = model_conf
        http_client = None
        if service_conf.proxy:
            transport = SyncProxyTransport.from_url(service_conf.proxy)
            http_client = Client(transport=transport)
        self._client = OpenAI(
            api_key=service_conf.token,
            base_url=service_conf.base_url,
            # todo: 未来再做更多细节.
            max_retries=0,
            http_client=http_client,
        )
        self._parser = parser

    def get_service(self) -> ServiceConf:
        return self._service

    def get_model(self) -> ModelConf:
        return self._model

    def text_completion(self, prompt: str) -> str:
        raise NotImplemented("text_completion is deprecated, implement it later")

    def get_embeddings(self, texts: List[str]) -> Embeddings:
        try:
            model = self._model.model
            resp = self._client.embeddings.create(
                input=texts,
                model=model,
                # todo: 未来再做更多细节.
            )
            result = []
            for i, text in enumerate(texts):
                embedding = resp.embeddings[i]
                result.append(Embedding(
                    text=text,
                    embedding=embedding
                ))
            return Embeddings(result=result)

        except Exception as e:
            # todo: log
            raise GhostissIOError("failed to get text embedding", e)

    def _chat_completion(self, chat: Chat, stream: bool) -> Union[ChatCompletion, Iterable[ChatCompletionChunk]]:
        # todo: try catch
        include_usage = ChatCompletionStreamOptionsParam(include_usage=True) if stream else NOT_GIVEN
        messages = self._parser.parse_message_list(chat.messages)
        return self._client.chat.completions.create(
            messages=messages,
            model=self._model.model,
            function_call=chat.get_openai_function_call(),
            functions=chat.get_openai_functions(),
            max_tokens=self._model.max_tokens,
            temperature=self._model.temperature,
            n=self._model.n,
            timeout=self._model.timeout,
            stream=stream,
            stream_options=include_usage,
            **self._model.kwargs,
        )

    def chat_completion(self, chat: Chat) -> Message:
        message: ChatCompletion = self._chat_completion(chat, stream=False)
        return self._parser.from_chat_completion(message.choices[0].message)

    def chat_completion_chunks(self, chat: Chat) -> Iterable[Message]:
        messages: Iterable[ChatCompletionChunk] = self._chat_completion(chat, stream=True)
        return self._parser.from_chat_completion_chunks(messages)


class OpenAIDriver(LLMDriver):
    """
    adapter
    """

    def __init__(self, parser: Optional[OpenAIParser] = None):
        if parser is None:
            parser = DefaultOpenAIParser()
        self._parser = parser

    def driver_name(self) -> str:
        return OPENAI_DRIVER_NAME

    def new(self, service: ServiceConf, model: ModelConf) -> LLMApi:
        return OpenAIAdapter(service, model, self._parser)


class OpenAIDriverBootstrapper(Bootstrapper):

    def bootstrap(self, container: Container) -> None:
        llms = container.force_fetch(LLMs)
        llms.register_driver(OpenAIDriver())
