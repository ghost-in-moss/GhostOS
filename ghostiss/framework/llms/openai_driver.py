from typing import List, Iterable, Union, Optional

from openai import OpenAI
from httpx import Client
from httpx_socks import SyncProxyTransport
from openai import NOT_GIVEN
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion_stream_options_param import ChatCompletionStreamOptionsParam
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

from ghostiss.core.errors import GhostissIOError
from ghostiss.core.messages import Message, OpenAIMessageParser, DefaultOpenAIMessageParser, DefaultMessageTypes
from ghostiss.core.llms import (
    LLMs, LLMDriver, LLMApi, ModelConf, ServiceConf, OPENAI_DRIVER_NAME,
    Chat,
    Embedding, Embeddings,
    FunctionalToken,
)
from ghostiss.container import Bootstrapper, Container

__all__ = ['OpenAIDriver', 'OpenAIAdapter', 'OpenAIDriverBootstrapper']


class FunctionalTokenPrompt(str):

    def format_tokens(self, tokens: Iterable[FunctionalToken]) -> str:
        lines = []
        for token in tokens:
            lines.append(f"`{token.token}`: \n\n {token.description}")
        return self.format(tokens="\n".join(lines))


DEFAULT_FUNCTIONAL_TOKEN_PROMPT = """
# Functional Token
You are equipped with `functional tokens` parser when you are outputing.

A functional token is a set of special tokens that corresponds to a system callback function. 
When a functional token is present in your response, the subsequent output is treated as input parameters for this 
callback function until another functional token is encountered. 

Below is a list of the functional tokens available for your use:

{tokens}

**Notices**

0. Your output without functional tokens will send directly.
1. The existence of functional tokens is unknown to the user. Do not mention their existence.
2. Use them only when necessary.
3. You can only use one functional token at a time.
"""


class OpenAIAdapter(LLMApi):
    """
    adapter class wrap openai api to ghostiss.blueprint.kernel.llms.LLMApi
    """

    def __init__(
            self,
            service_conf: ServiceConf,
            model_conf: ModelConf,
            parser: OpenAIMessageParser,
            functional_token_prompt: Optional[str] = None,
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
        if not functional_token_prompt:
            functional_token_prompt = DEFAULT_FUNCTIONAL_TOKEN_PROMPT
        self._functional_token_prompt = functional_token_prompt

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
        messages = chat.get_messages()
        messages = self._parser.parse_message_list(messages)
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
        chat = self.parse_chat(chat)
        message: ChatCompletion = self._chat_completion(chat, stream=False)
        return self._parser.from_chat_completion(message.choices[0].message)

    def chat_completion_chunks(self, chat: Chat) -> Iterable[Message]:
        chat = self.parse_chat(chat)
        chunks: Iterable[ChatCompletionChunk] = self._chat_completion(chat, stream=True)
        messages = self._parser.from_chat_completion_chunks(chunks)
        first = True
        for chunk in messages:
            if first:
                self._model.set(chunk)
                first = False
            yield chunk

    def parse_chat(self, chat: Chat) -> Chat:
        if not chat.functional_tokens:
            return chat
        prompt = FunctionalTokenPrompt(self._functional_token_prompt)
        content = prompt.format_tokens(chat.functional_tokens)
        if len(chat.system) == 0:
            chat.system = [DefaultMessageTypes.DEFAULT.new_system(content=content)]
        else:
            chat.system[-1].content += "\n\n" + content
        return chat


class OpenAIDriver(LLMDriver):
    """
    adapter
    """

    def __init__(self, parser: Optional[OpenAIMessageParser] = None):
        if parser is None:
            parser = DefaultOpenAIMessageParser()
        self._parser = parser

    def driver_name(self) -> str:
        return OPENAI_DRIVER_NAME

    def new(self, service: ServiceConf, model: ModelConf) -> LLMApi:
        return OpenAIAdapter(service, model, self._parser)


class OpenAIDriverBootstrapper(Bootstrapper):

    def bootstrap(self, container: Container) -> None:
        llms = container.force_fetch(LLMs)
        llms.register_driver(OpenAIDriver())
