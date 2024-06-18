from typing import Iterator, List

import openai

from ghostiss.context import Context
from ghostiss.contracts.logger import LoggerItf
from ghostiss.core.errors import GhostissIOError
from ghostiss.core.llms import LLMDriver, LLMApi, ModelConf, ServiceConf, OPENAI_DRIVER_NAME
from ghostiss.core.llms import Chat, LlmMsg
from ghostiss.core.llms import Embedding, Embeddings


class OpenAIAdapter(LLMApi):
    """
    adapter class wrap openai api to ghostiss.core.kernel.llms.LLMApi
    """

    def __init__(
            self,
            service_conf: ServiceConf,
            model_conf: ModelConf,
            logger: LoggerItf,
    ):
        self._service = service_conf
        self._model = model_conf
        self._logger = logger
        self._openai = openai.OpenAI(
            api_key=service_conf.token,
            base_url=service_conf.base_url,
            # todo: 未来再做更多细节.
            max_retries=0,
        )

    def with_service(self, conf: ServiceConf) -> "LLMApi":
        return OpenAIAdapter(conf, self._model, self._logger)

    def with_model(self, model: ModelConf) -> "LLMApi":
        return OpenAIAdapter(self._service, model, self._logger)

    def with_logger(self, logger: LoggerItf) -> "LLMApi":
        return OpenAIAdapter(self._service, self._model, logger)

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

    def chat_completion(self, ctx: Context, chat: Chat) -> LlmMsg:
        self._openai.chat.completions.create(
            model=chat.model,

            function_call=chat.function_call,

        )

    def chat_completion_chunks(self, ctx: Context, chat: Chat) -> Iterator[LlmMsg]:
        pass


class OpenAIDriver(LLMDriver):
    """
    adapter
    """

    def __init__(
            self,
            logger: LoggerItf
    ):
        self._logger = logger

    def driver_name(self) -> str:
        return OPENAI_DRIVER_NAME

    def new(self, service: ServiceConf, model: ModelConf) -> LLMApi:
        logger = self._logger.with_trace({
            "llm_service": service.name,
            "llm_model": model.model,
            "llm_driver": self.driver_name(),
        })
        return OpenAIAdapter(service, model, logger)
