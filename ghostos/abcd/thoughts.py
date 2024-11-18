from typing import Optional, Generic, TypeVar, Tuple, List
from abc import ABC, abstractmethod
from ghostos.abcd.concepts import Session, Operator, Action
from ghostos.core.llms import Prompt, ModelConf, ServiceConf, PromptPipe, LLMs, LLMApi

T = TypeVar("T")


class Thought(Generic[T], ABC):
    """
    LLM wrapper
    """

    @abstractmethod
    def think(self, session: Session, prompt: Prompt) -> Tuple[Prompt, Optional[T]]:
        pass


class ChainOfThoughts(Thought[Operator]):
    def __init__(
            self,
            final: Thought[Operator],
            nodes: List[Thought[Operator]],
    ):
        self.nodes = nodes
        self.final = final

    def think(self, session: Session, prompt: Prompt) -> Tuple[Prompt, Optional[T]]:
        for node in self.nodes:
            prompt, op = node.think(session, prompt)
            if op is not None:
                return prompt, op

        return self.final.think(session, prompt)


class LLMThought(Thought[Operator]):
    """
    basic llm thought
    """

    def __init__(
            self,
            llm_api: str = "",
            message_stage: str = "",
            *actions: Action,
            model: Optional[ModelConf] = None,
            service: Optional[ServiceConf] = None,
    ):
        """

        :param llm_api: The LLM API to use, see LLMsConfig
        :param message_stage:
        :param actions:
        :param model: the llm model to use, if given, overrides llm_api
        :param service: the llm service to use, if given, override ModelConf service field
        """
        self.llm_api = llm_api
        self.message_stage = message_stage
        self.model = model
        self.service = service
        self.actions = {action.name(): action for action in actions}

    def think(self, session: Session, prompt: Prompt) -> Tuple[Prompt, Optional[Operator]]:
        for action in self.actions.values():
            if isinstance(action, PromptPipe):
                prompt = action.update_prompt(prompt)
        llm_api = self.get_llm_api(session)

        streaming = not session.upstream.completes_only()
        session.logger.info(f"start llm thinking on prompt {prompt.id}")
        items = llm_api.deliver_chat_completion(prompt, streaming)
        messages, callers = session.respond(items, self.message_stage)
        prompt.added.extend(messages)
        session.logger.info(f"llm thinking on prompt {prompt.id} is done")

        for caller in callers:
            if caller.name in self.actions:
                action = self.actions[caller.name]
                op = action.run(session, caller)
                if op is not None:
                    return prompt, op
        return prompt, None

    def get_llm_api(self, session: Session) -> LLMApi:
        llms = session.container.force_fetch(LLMs)
        if self.model:
            llm_api = llms.new_api(self.service, self.model)
        else:
            llm_api = llms.get_api(self.llm_api)
        return llm_api
