from typing import List
from ghostos.core.llms.configs import ServiceConf, ModelConf, LITELLM_DRIVER_NAME
from ghostos.core.llms.abcd import LLMApi
from ghostos.core.messages import Role, Message
from ghostos.core.llms.prompt import Prompt
from ghostos.framework.llms.openai_driver import OpenAIDriver, OpenAIAdapter
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat import ChatCompletion


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


class LiteLLMDriver(OpenAIDriver):

    def driver_name(self) -> str:
        return LITELLM_DRIVER_NAME

    def new(self, service: ServiceConf, model: ModelConf, api_name: str = "") -> LLMApi:
        return LitellmAdapter(
            service_conf=service,
            model_conf=model,
            parser=self._parser,
            storage=self._storage,
            logger=self._logger,
            api_name=api_name,
        )
