from typing import List, Iterable, Union, Optional

from openai import OpenAI
from httpx import Client
from httpx_socks import SyncProxyTransport
from openai import NOT_GIVEN
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion_stream_options_param import ChatCompletionStreamOptionsParam
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

from ghostos.core.messages import (
    Message, OpenAIMessageParser, DefaultOpenAIMessageParser,
    CompletionUsagePayload, Role,
)
from ghostos.core.llms import (
    LLMs, LLMDriver, LLMApi, ModelConf, ServiceConf, OPENAI_DRIVER_NAME, LITELLM_DRIVER_NAME,
    Prompt, PromptPayload, PromptStorage,
    FunctionalToken,
)
from ghostos.container import Bootstrapper, Container

import litellm

__all__ = [
    'OpenAIDriver', 'OpenAIAdapter', 'OpenAIDriverBootstrapper',
    'LitellmAdapter', 'LiteLLMDriver',
]


class FunctionalTokenPrompt(str):

    def format_tokens(self, tokens: Iterable[FunctionalToken]) -> str:
        lines = []
        for token in tokens:
            start = token.token
            end = token.end_token if token.end_token else ""
            description_lines = token.description.splitlines()
            description = "\n".join(['> ' + desc for desc in description_lines])
            lines.append(f"`{start}{end}`:\n\n{description}")
        return self.format(tokens="\n".join(lines))


DEFAULT_FUNCTIONAL_TOKEN_PROMPT = """
# Functional Token
You are equipped with `functional tokens` parser to understand your outputs.

A functional token is a set of special tokens that corresponds to a system callback function. 
When a functional token is present in your response, the subsequent output is treated as input parameters for this 
callback function. 
You shall embrace the parameter tokens by xml pattern. For example:
* functional token is start with `<moss>` and end with `</moss>`
* parameter tokens are `print("hello world")`
* the whole output should be: `say something if necessary...<moss>print("hello world")</moss>`

Below is a list of the functional tokens available for your use:

{tokens}

**Notices**

0. Your output without functional tokens will send directly.
1. If the functional tokens is invisible to the user. Do not mention their existence.
2. Use them only when necessary.
3. You can only use each functional token at most once during outputting.
"""


class OpenAIAdapter(LLMApi):
    """
    adapter class wrap openai api to ghostos.blueprint.kernel.llms.LLMApi
    """

    def __init__(
            self,
            service_conf: ServiceConf,
            model_conf: ModelConf,
            parser: OpenAIMessageParser,
            storage: PromptStorage,
            # deprecated:
            functional_token_prompt: Optional[str] = None,
    ):
        self._service = service_conf
        self._model = model_conf
        self._storage: PromptStorage = storage
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

    def parse_message_params(self, messages: List[Message]) -> List[ChatCompletionMessageParam]:
        return list(self._parser.parse_message_list(messages))

    def _chat_completion(self, chat: Prompt, stream: bool) -> Union[ChatCompletion, Iterable[ChatCompletionChunk]]:
        chat = self.parse_chat(chat)
        include_usage = ChatCompletionStreamOptionsParam(include_usage=True) if stream else NOT_GIVEN
        messages = chat.get_messages()
        messages = self.parse_message_params(messages)
        if not messages:
            raise AttributeError("empty chat!!")
        return self._client.chat.completions.create(
            messages=messages,
            model=self._model.model,
            function_call=chat.get_openai_function_call(),
            functions=chat.get_openai_functions(),
            tools=chat.get_openai_tools(),
            max_tokens=self._model.max_tokens,
            temperature=self._model.temperature,
            n=self._model.n,
            timeout=self._model.timeout,
            stream=stream,
            stream_options=include_usage,
            **self._model.kwargs,
        )

    def chat_completion(self, chat: Prompt) -> Message:
        try:
            message: ChatCompletion = self._chat_completion(chat, stream=False)
            chat.output = [message]
            pack = self._parser.from_chat_completion(message.choices[0].message)
            # add completion usage
            self._model.set(pack)
            if message.usage:
                usage = CompletionUsagePayload.from_usage(message.usage)
                usage.set(pack)

            if not pack.is_complete():
                pack.chunk = False
            return pack
        except Exception as e:
            chat.error = str(e)
            raise
        finally:
            self._storage.save(chat)

    def chat_completion_chunks(self, chat: Prompt) -> Iterable[Message]:
        try:
            chunks: Iterable[ChatCompletionChunk] = self._chat_completion(chat, stream=True)
            messages = self._parser.from_chat_completion_chunks(chunks)
            prompt_payload = PromptPayload.from_prompt(chat)
            output = []
            for chunk in messages:
                yield chunk
                if chunk.is_complete():
                    self._model.set(chunk)
                    prompt_payload.set(chunk)
                    output.append(chunk)
            chat.output = output
        except Exception as e:
            chat.error = str(e)
        finally:
            self._storage.save(chat)

    def parse_chat(self, chat: Prompt) -> Prompt:
        # if not chat.functional_tokens:
        #     return chat
        # prompt = FunctionalTokenPrompt(self._functional_token_prompt)
        # content = prompt.format_tokens(chat.functional_tokens)
        # message = MessageType.DEFAULT.new_system(content=content)
        # chat.system.append(message)
        return chat


class OpenAIDriver(LLMDriver):
    """
    adapter
    """

    def __init__(self, storage: PromptStorage, parser: Optional[OpenAIMessageParser] = None):
        if parser is None:
            parser = DefaultOpenAIMessageParser(None, None)
        self._parser = parser
        self._storage = storage

    def driver_name(self) -> str:
        return OPENAI_DRIVER_NAME

    def new(self, service: ServiceConf, model: ModelConf) -> LLMApi:
        return OpenAIAdapter(service, model, self._parser, self._storage)


class LitellmAdapter(OpenAIAdapter):
    """
    adapter class wrap openai api to ghostos.blueprint.kernel.llms.LLMApi
    """

    def _chat_completion(self, chat: Prompt, stream: bool) -> ChatCompletion:
        messages = chat.get_messages()
        messages = self.parse_message_params(messages)
        response = litellm.completion(
            model=self._model.model,
            messages=list(messages),
            timeout=self._model.timeout,
            temperature=self._model.temperature,
            n=self._model.n,
            # not support stream yet
            stream=False,
            api_key=self._service.token,
        )
        return response.choices[0].message

    def parse_message_params(self, messages: List[Message]) -> List[ChatCompletionMessageParam]:
        parsed = super().parse_message_params(messages)
        outputs = []
        count = 0
        for message in parsed:
            # filter all the system message to __system__ user message.
            if count > 0 and "role" in message and message["role"] == Role.SYSTEM.value:
                message["role"] = Role.USER.value
                message["name"] = "__system__"
            outputs.append(message)
            count += 1
        return outputs


class LiteLLMDriver(OpenAIDriver):

    def driver_name(self) -> str:
        return LITELLM_DRIVER_NAME

    def new(self, service: ServiceConf, model: ModelConf) -> LLMApi:
        return LitellmAdapter(service, model, self._parser, self._storage)


class OpenAIDriverBootstrapper(Bootstrapper):

    def bootstrap(self, container: Container) -> None:
        llms = container.force_fetch(LLMs)
        storage = container.force_fetch(PromptStorage)
        openai_driver = OpenAIDriver(storage)
        lite_llm_driver = LiteLLMDriver(storage)
        llms.register_driver(openai_driver)
        llms.register_driver(lite_llm_driver)
