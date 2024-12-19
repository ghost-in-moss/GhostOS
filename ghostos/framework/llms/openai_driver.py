from typing import List, Iterable, Union, Optional
from openai import OpenAI
from httpx import Client
from httpx_socks import SyncProxyTransport
from openai import NOT_GIVEN
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion_stream_options_param import ChatCompletionStreamOptionsParam
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from ghostos.contracts.logger import LoggerItf, get_ghostos_logger
from ghostos.helpers import timestamp
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

__all__ = [
    'OpenAIDriver', 'OpenAIAdapter',
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
            logger: LoggerItf,
            # deprecated:
            functional_token_prompt: Optional[str] = None,
    ):
        self._service = service_conf
        self._model = model_conf
        self._storage: PromptStorage = storage
        self._logger = logger
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
        return list(self._parser.parse_message_list(messages, self._model.message_types))

    def _chat_completion(self, prompt: Prompt, stream: bool) -> Union[ChatCompletion, Iterable[ChatCompletionChunk]]:
        prompt = self.parse_prompt(prompt)
        self._logger.info(f"start chat completion for prompt %s", prompt.id)
        include_usage = ChatCompletionStreamOptionsParam(include_usage=True) if stream else NOT_GIVEN
        messages = prompt.get_messages()
        messages = self.parse_message_params(messages)
        if not messages:
            raise AttributeError("empty chat!!")
        try:
            prompt.run_start = timestamp()
            self._logger.debug(f"start chat completion messages %s", messages)
            functions = prompt.get_openai_functions()
            tools = prompt.get_openai_tools()
            if self._model.use_tools:
                functions = NOT_GIVEN
            else:
                tools = NOT_GIVEN
            return self._client.chat.completions.create(
                messages=messages,
                model=self._model.model,
                function_call=prompt.get_openai_function_call(),
                functions=functions,
                tools=tools,
                max_tokens=self._model.max_tokens,
                temperature=self._model.temperature,
                n=self._model.n,
                timeout=self._model.timeout,
                stream=stream,
                stream_options=include_usage,
                **self._model.kwargs,
            )
        except Exception as e:
            self._logger.error(f"error chat completion for prompt {prompt.id}: {e}")
            raise
        finally:
            self._logger.debug(f"end chat completion for prompt {prompt.id}")
            prompt.run_end = timestamp()

    def chat_completion(self, prompt: Prompt) -> Message:
        try:
            message: ChatCompletion = self._chat_completion(prompt, stream=False)
            prompt.added = [message]
            pack = self._parser.from_chat_completion(message.choices[0].message)
            # add completion usage
            self._model.set_payload(pack)
            if message.usage:
                usage = CompletionUsagePayload.from_usage(message.usage)
                usage.set_payload(pack)

            if not pack.is_complete():
                pack.chunk = False
            return pack
        except Exception as e:
            prompt.error = str(e)
            raise
        finally:
            self._storage.save(prompt)

    def chat_completion_chunks(self, prompt: Prompt) -> Iterable[Message]:
        try:
            chunks: Iterable[ChatCompletionChunk] = self._chat_completion(prompt, stream=True)
            messages = self._parser.from_chat_completion_chunks(chunks)
            prompt_payload = PromptPayload.from_prompt(prompt)
            output = []
            for chunk in messages:
                yield chunk
                if chunk.is_complete():
                    self._model.set_payload(chunk)
                    prompt_payload.set_payload(chunk)
                    output.append(chunk)
            prompt.added = output
        except Exception as e:
            prompt.error = str(e)
            raise
        finally:
            self._storage.save(prompt)

    def parse_prompt(self, prompt: Prompt) -> Prompt:
        prompt.model = self._model
        return prompt


class OpenAIDriver(LLMDriver):
    """
    adapter
    """

    def __init__(self, storage: PromptStorage, logger: LoggerItf, parser: Optional[OpenAIMessageParser] = None):
        if parser is None:
            parser = DefaultOpenAIMessageParser(None, None)
        self._logger = logger
        self._parser = parser
        self._storage = storage

    def driver_name(self) -> str:
        return OPENAI_DRIVER_NAME

    def new(self, service: ServiceConf, model: ModelConf) -> LLMApi:
        get_ghostos_logger().debug(f"new llm api %s at service %s", model.model, service.name)
        return OpenAIAdapter(service, model, self._parser, self._storage, self._logger)


class LitellmAdapter(OpenAIAdapter):
    """
    adapter class wrap openai api to ghostos.blueprint.kernel.llms.LLMApi
    """

    def _chat_completion(self, chat: Prompt, stream: bool) -> ChatCompletion:
        import litellm
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
        return LitellmAdapter(service, model, self._parser, self._storage, self._logger)
