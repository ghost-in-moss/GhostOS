from typing import Iterable
from ghostos.core.llms.configs import ServiceConf, ModelConf, DEEPSEEK_DRIVER_NAME
from ghostos.core.llms.abcd import LLMApi
from ghostos.core.llms.prompt import Prompt, PromptPayload
from ghostos.core.messages import Message, MessageStage
from ghostos_common.helpers.timeutils import timestamp_ms
from ghostos.framework.llms.openai_driver import OpenAIDriver, OpenAIAdapter
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat import ChatCompletion


class DeepseekAdapter(OpenAIAdapter):
    def _from_openai_chat_completion_item(self, message: ChatCompletion) -> Iterable[Message]:
        cc_item = message.choices[0].message
        if reasoning := cc_item.reasoning_content:
            reasoning_message = Message.new_tail(content=reasoning)
            reasoning_message.stage = MessageStage.REASONING.value
            yield reasoning_message

        yield self._parser.from_chat_completion(cc_item)

    def reasoning_completion_stream(self, prompt: Prompt) -> Iterable[ChatCompletionChunk]:
        try:
            prompt = self.parse_prompt(prompt)
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


class DeepseekDriver(OpenAIDriver):

    def driver_name(self) -> str:
        return DEEPSEEK_DRIVER_NAME

    def new(self, service: ServiceConf, model: ModelConf, api_name: str = "") -> LLMApi:
        return DeepseekAdapter(
            service_conf=service,
            model_conf=model,
            parser=self._parser,
            storage=self._storage,
            logger=self._logger,
            api_name=api_name,
        )
