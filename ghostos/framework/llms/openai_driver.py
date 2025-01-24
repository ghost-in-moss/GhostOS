from typing import List, Iterable, Union, Optional, Tuple
from openai import OpenAI, AzureOpenAI
from httpx import Client
from httpx_socks import SyncProxyTransport
from openai import NOT_GIVEN, NotGiven
from openai.types.chat import ChatCompletion, ChatCompletionReasoningEffort
from openai.types.chat.chat_completion_stream_options_param import ChatCompletionStreamOptionsParam
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat.completion_create_params import Function
from ghostos.contracts.logger import LoggerItf, get_ghostos_logger
from ghostos.helpers import timestamp_ms
from ghostos.core.messages import (
    MessageStage,
    Message, OpenAIMessageParser, DefaultOpenAIMessageParser,
    CompletionUsagePayload, Role,
)
from ghostos.core.llms import (
    LLMDriver, LLMApi, ModelConf, ServiceConf, OPENAI_DRIVER_NAME, LITELLM_DRIVER_NAME, DEEPSEEK_DRIVER_NAME,
    Prompt, PromptPayload, PromptStorage,
    Compatible,
    FunctionalToken,
)

__all__ = [
    'OpenAIDriver', 'OpenAIAdapter',
    'LitellmAdapter', 'LiteLLMDriver',
    'DeepseekDriver', 'DeepseekAdapter',
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
            api_name: str = "",
    ):
        self._api_name = api_name
        self.service = service_conf.model_copy(deep=True)
        self.model = model_conf.model_copy(deep=True)
        self._storage: PromptStorage = storage
        self._logger = logger
        http_client = None
        if service_conf.proxy:
            transport = SyncProxyTransport.from_url(service_conf.proxy)
            http_client = Client(transport=transport)
        if service_conf.azure.api_key:
            self._client = AzureOpenAI(
                azure_endpoint=service_conf.base_url,
                api_version=service_conf.azure.api_version,
                api_key=service_conf.azure.api_key,
            )
        else:
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

    @property
    def name(self) -> str:
        return self._api_name

    def get_service(self) -> ServiceConf:
        return self.service

    def get_model(self) -> ModelConf:
        return self.model

    def text_completion(self, prompt: str) -> str:
        raise NotImplemented("text_completion is deprecated, implement it later")

    def parse_message_params(self, messages: List[Message]) -> List[ChatCompletionMessageParam]:
        messages = self.parse_by_compatible_settings(messages)
        return list(self._parser.parse_message_list(messages, self.model.message_types))

    @staticmethod
    def _parse_system_to_develop(messages: List[Message]) -> List[Message]:
        changed = []
        for message in messages:
            if message.role == Role.SYSTEM:
                message = message.model_copy(update={"role": Role.DEVELOPER.value}, deep=True)
            changed.append(message)
        return changed

    def parse_by_compatible_settings(self, messages: List[Message]) -> List[Message]:
        compatible = self._get_compatible_options()

        if compatible is None:
            return messages

        # developer role test
        if compatible.use_developer_role:
            messages = self._parse_system_to_develop(messages)
        else:
            changed = []
            for message in messages:
                if message.role == Role.DEVELOPER:
                    message = message.model_copy(update={"role": Role.SYSTEM.value}, deep=True)
                changed.append(message)
            messages = changed

        # allow system messages
        if not compatible.allow_system_in_messages:
            changed = []
            count = 0
            for message in messages:
                if count > 0 and message.role == Role.SYSTEM or message.role == Role.DEVELOPER:
                    name = f"__{message.role}__"
                    message = message.model_copy(update={"role": Role.USER.value, "name": name}, deep=True)
                changed.append(message)
                count += 1
            messages = changed
            self._logger.debug("[compatible] change messages system role to user role")

        if not compatible.allow_system_message:
            changed = []
            for message in messages:
                if message.role == Role.SYSTEM or message.role == Role.DEVELOPER:
                    name = f"__{message.role}__"
                    message = message.model_copy(update={"role": Role.USER.value, "name": name}, deep=True)
                changed.append(message)
            messages = changed
            self._logger.debug("[compatible] change all messages system role to user role")

        return messages

    def _chat_completion(self, prompt: Prompt, stream: bool) -> Union[ChatCompletion, Iterable[ChatCompletionChunk]]:
        prompt = self.parse_prompt(prompt)
        self._logger.info(f"start chat completion for prompt %s", prompt.id)
        include_usage = ChatCompletionStreamOptionsParam(include_usage=True) if stream else NOT_GIVEN
        messages = prompt.get_messages()
        messages = self.parse_message_params(messages)
        if not messages:
            raise AttributeError("empty chat!!")
        try:
            prompt.run_start = timestamp_ms()
            self._logger.debug(f"start chat completion messages %s", messages)
            functions, tools = self._get_prompt_functions_and_tools(prompt)
            return self._client.chat.completions.create(
                messages=messages,
                model=self.model.model,
                function_call=prompt.get_openai_function_call(),
                functions=functions,
                tools=tools,
                max_tokens=self.model.max_tokens,
                temperature=self.model.temperature,
                n=self.model.n,
                timeout=self.model.timeout,
                stream=stream,
                stream_options=include_usage,
                **self.model.kwargs,
            )
        except Exception as e:
            self._logger.error(f"error chat completion for prompt {prompt.id}: {e}")
            raise
        finally:
            self._logger.debug(f"end chat completion for prompt {prompt.id}")
            prompt.run_end = timestamp_ms()

    def _get_prompt_functions_and_tools(
            self,
            prompt: Prompt,
    ) -> Tuple[Union[List[Function], NotGiven], Union[List[ChatCompletionToolParam], NotGiven]]:
        functions = prompt.get_openai_functions()
        tools = prompt.get_openai_tools()
        if self.model.use_tools:
            functions = NOT_GIVEN
        else:
            tools = NOT_GIVEN
        # compatible check
        if not self._get_compatible_options().support_function_call:
            functions = NOT_GIVEN
            tools = NOT_GIVEN
        return functions, tools

    def _reasoning_completion(self, prompt: Prompt) -> ChatCompletion:
        if self.model.reasoning is None:
            raise NotImplementedError(f"current model {self.model} does not support reasoning completion ")

        prompt = self.parse_prompt(prompt)
        self._logger.info(
            "start reasoning completion for prompt %s, model %s, reasoning conf %s",
            prompt.id,
            self.model.model_dump(exclude_defaults=True),
            self.model.reasoning,
        )
        # include_usage = ChatCompletionStreamOptionsParam(include_usage=True) if stream else NOT_GIVEN
        messages = prompt.get_messages()
        messages = self.parse_message_params(messages)
        if not messages:
            raise AttributeError("empty chat!!")
        try:
            prompt.run_start = timestamp_ms()
            self._logger.debug(f"start reasoning completion messages %s", messages)
            functions, tools = self._get_prompt_functions_and_tools(prompt)
            if self.model.reasoning.effort is None:
                reasoning_effort = NOT_GIVEN
            else:
                reasoning_effort = self.model.reasoning.effort

            # todo: debug
            return self._client.chat.completions.create(
                messages=messages,
                model=self.model.model,
                # add this parameters then failed:
                # todo: add reasoning will issue error now.
                # Error code: 400 - {'error': {'message': "Unknown parameter: 'reasoning_effort'.",
                # 'type': 'invalid_request_error', 'param': 'reasoning_effort', 'code': 'unknown_parameter'}
                # reasoning_effort=reasoning_effort,
                # max_tokens=prompt.model.max_tokens,
                max_completion_tokens=prompt.model.reasoning.max_completion_tokens or NOT_GIVEN,
                function_call=prompt.get_openai_function_call(),
                functions=functions,
                tools=tools,
                n=self.model.n,
                timeout=self.model.timeout,
                **self.model.kwargs,
            )
        except Exception as e:
            self._logger.error(f"error reasoning completion for prompt {prompt.id}: {e}")
            raise
        finally:
            self._logger.debug(f"end reasoning completion for prompt {prompt.id}")
            prompt.run_end = timestamp_ms()

    def _reasoning_completion_stream(self, prompt: Prompt) -> Iterable[ChatCompletionChunk]:
        if self.model.reasoning is None:
            raise NotImplementedError(f"current model {self.model} does not support reasoning completion ")

        prompt = self.parse_prompt(prompt)
        self._logger.info(
            "start reasoning completion for prompt %s, model %s, reasoning conf %s",
            prompt.id,
            self.model.model_dump(exclude_defaults=True),
            self.model.reasoning,
        )
        # include_usage = ChatCompletionStreamOptionsParam(include_usage=True) if stream else NOT_GIVEN
        messages = prompt.get_messages()
        messages = self.parse_message_params(messages)
        if not messages:
            raise AttributeError("empty chat!!")
        try:
            prompt.run_start = timestamp_ms()
            self._logger.debug(f"start reasoning completion messages %s", messages)
            functions, tools = self._get_prompt_functions_and_tools(prompt)
            if self.model.reasoning.effort is None:
                reasoning_effort = NOT_GIVEN
            else:
                reasoning_effort = self.model.reasoning.effort

            yield from self._client.chat.completions.create(
                messages=messages,
                model=self.model.model,
                # add this parameters then failed:
                # todo: add reasoning will issue error now.
                # Error code: 400 - {'error': {'message': "Unknown parameter: 'reasoning_effort'.",
                # 'type': 'invalid_request_error', 'param': 'reasoning_effort', 'code': 'unknown_parameter'}
                # reasoning_effort=reasoning_effort,
                max_tokens=prompt.model.max_tokens,
                function_call=prompt.get_openai_function_call(),
                functions=functions,
                tools=tools,
                n=self.model.n,
                timeout=self.model.timeout,
                stream=True,
                **self.model.kwargs,
            )
        except Exception as e:
            self._logger.error(f"error reasoning completion for prompt {prompt.id}: {e}")
            raise
        finally:
            self._logger.debug(f"end reasoning completion for prompt {prompt.id}")
            prompt.run_end = timestamp_ms()

    def chat_completion(self, prompt: Prompt) -> Message:
        try:
            message: ChatCompletion = self._chat_completion(prompt, stream=False)
            prompt.first_token = timestamp_ms()
            prompt.added = [message]
            pack = self._parser.from_chat_completion(message.choices[0].message)
            # add completion usage
            self.model.set_payload(pack)
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

    def reasoning_completion(self, prompt: Prompt) -> Iterable[Message]:
        try:
            cc: ChatCompletion = self._reasoning_completion(prompt)
            items = self._from_openai_chat_completion_item(cc)
            # add completion usage
            last_item = None
            for item in items:
                if not prompt.first_token:
                    prompt.first_token = timestamp_ms()
                if last_item is not None:
                    if last_item.is_complete():
                        prompt.added.append(last_item)
                    yield last_item
                last_item = item

            if last_item is not None:
                self.model.set_payload(last_item)
                if cc.usage:
                    usage = CompletionUsagePayload.from_usage(cc.usage)
                    usage.set_payload(last_item)

                if not last_item.is_complete():
                    last_item = last_item.as_tail()
                prompt.added.append(last_item)
                yield last_item
        except Exception as e:
            prompt.error = str(e)
            raise
        finally:
            self._storage.save(prompt)

    def _from_openai_chat_completion_item(self, message: ChatCompletion) -> Iterable[Message]:
        cc_item = message.choices[0].message
        return [self._parser.from_chat_completion(cc_item)]

    def _from_openai_chat_completion_chunks(self, chunks: Iterable[ChatCompletionChunk]) -> Iterable[Message]:
        yield from self._parser.from_chat_completion_chunks(chunks)

    def reasoning_completion_stream(self, prompt: Prompt) -> Iterable[Message]:
        # todo: openai is not support reasoning completion stream yet
        yield from self.reasoning_completion(prompt)

    def chat_completion_chunks(self, prompt: Prompt) -> Iterable[Message]:
        try:
            chunks: Iterable[ChatCompletionChunk] = self._chat_completion(prompt, stream=True)
            messages = self._from_openai_chat_completion_chunks(chunks)
            prompt_payload = PromptPayload.from_prompt(prompt)
            output = []
            for chunk in messages:
                if not prompt.first_token:
                    prompt.first_token = timestamp_ms()
                yield chunk
                if chunk.is_complete():
                    self.model.set_payload(chunk)
                    prompt_payload.set_payload(chunk)
                    output.append(chunk)
            prompt.added = output
        except Exception as e:
            prompt.error = str(e)
            raise
        finally:
            self._storage.save(prompt)

    def parse_prompt(self, prompt: Prompt) -> Prompt:
        prompt.model = self.model
        return prompt

    def _get_compatible_options(self) -> Compatible:
        return self.model.compatible or self.service.compatible or Compatible()


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

    def new(self, service: ServiceConf, model: ModelConf, api_name: str = "") -> LLMApi:
        get_ghostos_logger().debug(f"new llm api %s at service %s", model.model, service.name)
        return OpenAIAdapter(service, model, self._parser, self._storage, self._logger, api_name=api_name)


class LitellmAdapter(OpenAIAdapter):
    """
    adapter class wrap openai api to ghostos.blueprint.kernel.llms.LLMApi
    """

    def _chat_completion(self, chat: Prompt, stream: bool) -> ChatCompletion:
        import litellm
        messages = chat.get_messages()
        messages = self.parse_message_params(messages)
        response = litellm.completion(
            model=self.model.model,
            messages=list(messages),
            timeout=self.model.timeout,
            temperature=self.model.temperature,
            n=self.model.n,
            # not support stream yet
            stream=False,
            api_key=self.service.token,
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


# todo: move to lite_llm_driver. shall not locate here at very first.
class LiteLLMDriver(OpenAIDriver):

    def driver_name(self) -> str:
        return LITELLM_DRIVER_NAME

    def new(self, service: ServiceConf, model: ModelConf, api_name: str = "") -> LLMApi:
        return LitellmAdapter(service, model, self._parser, self._storage, self._logger, api_name=api_name)


class DeepseekAdapter(OpenAIAdapter):
    # def reasoning_completion(self, prompt: Prompt, stream: bool) -> Iterable[Message]:
    #     if not stream:
    #         yield from self._reasoning_completion_none_stream(prompt)
    #     else:
    #         yield from self._reasoning_completion_stream(prompt)
    #

    def _from_openai_chat_completion_item(self, message: ChatCompletion) -> Iterable[Message]:
        cc_item = message.choices[0].message
        if reasoning := cc_item.reasoning_content:
            reasoning_message = Message.new_tail(content=reasoning)
            reasoning_message.stage = MessageStage.REASONING.value
            yield reasoning_message

        yield self._parser.from_chat_completion(cc_item)

    def reasoning_completion_stream(self, prompt: Prompt) -> Iterable[ChatCompletionChunk]:
        try:
            chunks: Iterable[ChatCompletionChunk] = self._reasoning_completion_stream(prompt)
            messages = self._from_openai_chat_completion_chunks(chunks)
            prompt_payload = PromptPayload.from_prompt(prompt)
            output = []
            for chunk in messages:
                if not prompt.first_token:
                    prompt.first_token = timestamp_ms()
                yield chunk
                if chunk.is_complete():
                    self.model.set_payload(chunk)
                    prompt_payload.set_payload(chunk)
                    output.append(chunk)
            prompt.added = output
        except Exception as e:
            prompt.error = str(e)
            raise
        finally:
            self._storage.save(prompt)


# todo: move to deepseek driver
class DeepseekDriver(OpenAIDriver):

    def driver_name(self) -> str:
        return DEEPSEEK_DRIVER_NAME

    def new(self, service: ServiceConf, model: ModelConf, api_name: str = "") -> LLMApi:
        return DeepseekAdapter(service, model, self._parser, self._storage, self._logger, api_name=api_name)
