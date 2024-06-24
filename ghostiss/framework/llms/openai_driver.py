from typing import List, Iterator, Union

from openai import OpenAI
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion_stream_options_param import ChatCompletionStreamOptionsParam
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

from ghostiss.context import Context
from ghostiss.contracts.logger import LoggerItf
from ghostiss.blueprint.errors import GhostissIOError
from ghostiss.blueprint.messages import Message, AssistantMsg
from ghostiss.blueprint.kernel.llms import LLMDriver, LLMApi, ModelConf, ServiceConf, OPENAI_DRIVER_NAME
from ghostiss.blueprint.kernel.llms import Chat
from ghostiss.blueprint.kernel.llms import Embedding, Embeddings
from ghostiss.helpers import uuid

__all__ = ['OpenAIDriver', 'OpenAIAdapter']


class OpenAIAdapter(LLMApi):
    """
    adapter class wrap openai api to ghostiss.blueprint.kernel.llms.LLMApi
    """

    def __init__(
            self,
            service_conf: ServiceConf,
            model_conf: ModelConf,
    ):
        self._service = service_conf
        self._model = model_conf
        self._openai = OpenAI(
            api_key=service_conf.token,
            base_url=service_conf.base_url,
            # todo: 未来再做更多细节.
            max_retries=0,
        )

    def with_service(self, conf: ServiceConf) -> "LLMApi":
        return OpenAIAdapter(conf, self._model)

    def with_model(self, model: ModelConf) -> "LLMApi":
        return OpenAIAdapter(self._service, model)

    def text_completion(self, ctx: Context, prompt: str) -> str:
        raise NotImplemented("text_completion is deprecated, implement it later")

    def get_embeddings(self, ctx: Context, texts: List[str]) -> Embeddings:
        with ctx:
            return self._text_embedding(texts)

    def _text_embedding(self, texts: List[str]) -> Embeddings:
        try:
            model = self._model.model
            resp = self._openai.embeddings.create(
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

    def _chat_completion(self, chat: Chat, stream: bool) -> Union[ChatCompletion, Iterator[ChatCompletionChunk]]:
        include_usage = ChatCompletionStreamOptionsParam(include_usage=True if stream else False)
        return self._openai.chat.completions.create(
            # messages=messages,
            # messages=[],
            messages=chat.get_openai_messages(),
            model=self._model.model,
            function_call=chat.get_openai_function_call(),
            functions=chat.get_openai_functions(),
            max_tokens=self._model.max_tokens,
            parallel_tool_calls=False,
            temperature=self._model.temperature,
            n=self._model.n,
            timeout=self._model.timeout,
            stream=stream,
            stream_options=include_usage,
            **self._model.kwargs,
        )

    def chat_completion(self, chat: Chat) -> Message:
        message: ChatCompletion = self._chat_completion(chat, stream=False)
        values = message.choices[0].message.model_dump()
        values["msg_id"] = uuid()
        return AssistantMsg(**values)

    def chat_completion_chunks(self, chat: Chat) -> Iterator[Message]:
        messages: Iterator[ChatCompletionChunk] = self._chat_completion(chat, stream=True)
        first = AssistantMsg(msg_id=uuid())
        for item in messages:
            if first:
                yield first
                first = None
            yield AssistantMsg(**item.choices[0].delta.model_dump())


class OpenAIDriver(LLMDriver):
    """
    adapter
    """

    def driver_name(self) -> str:
        return OPENAI_DRIVER_NAME

    def new(self, service: ServiceConf, model: ModelConf) -> LLMApi:
        return OpenAIAdapter(service, model)
