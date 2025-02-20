from abc import ABC, abstractmethod
from typing import Optional, Tuple, List, Iterable
from ghostos.abcd.concepts import Session, Operator, Action, Thought
from ghostos.core.llms import Prompt, ModelConf, ServiceConf, LLMs, LLMApi
from ghostos.core.messages import Message

__all__ = ['ActionThought', 'ChainOfThoughts', 'OpThought', 'Thought']


# --- some basic thoughts --- #

class OpThought(Thought[Operator]):

    @abstractmethod
    def think(self, session: Session, prompt: Prompt) -> Tuple[Prompt, Optional[Operator]]:
        pass


class ChainOfThoughts(OpThought):
    def __init__(
            self,
            *,
            final: OpThought,
            chain: List[OpThought],
    ):
        self.chain = chain
        self.final = final

    def think(self, session: Session, prompt: Prompt) -> Tuple[Prompt, Optional[Operator]]:
        for node in self.chain:
            prompt, op = node.think(session, prompt)
            if op is not None:
                return prompt, op

        return self.final.think(session, prompt)


class MemoryThought(OpThought, ABC):
    """
    add memory before inputs.
    """

    @abstractmethod
    def memory(self, session: Session) -> List[Message]:
        pass

    def think(self, session: Session, prompt: Prompt) -> Tuple[Prompt, Optional[Operator]]:
        memory = self.memory(session)
        prompt.history.extend(memory)
        return prompt, None


class ActionThought(OpThought):
    """
    basic llm thought
    """

    def __init__(
            self,
            llm_api: str = "",
            actions: Optional[Iterable[Action]] = None,
            message_stage: str = "",
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
        self.actions = {}
        if actions:
            self.actions = {action.name(): action for action in actions}

    def think(self, session: Session, prompt: Prompt) -> Tuple[Prompt, Optional[Operator]]:
        _prompt = prompt.get_new_copy()
        for action in self.actions.values():
            _prompt = action.update_prompt(prompt)
        llm_api = self.get_llm_api(session)

        streaming = session.allow_streaming()
        session.logger.debug("start llm thinking on prompt %s", prompt.id)
        items = llm_api.deliver_chat_completion(_prompt, streaming)
        messages, callers = session.respond(items, self.message_stage)
        session.logger.debug("end llm thinking receive callers: %s", callers)

        # extends result into the origin prompt
        prompt.added.extend(messages)
        session.logger.debug("llm thinking on prompt %s is done", prompt.id)

        if callers:
            op = session.handle_callers(callers, False)
            return prompt, op
        return prompt, None

    def get_llm_api(self, session: Session) -> LLMApi:
        llms = session.container.force_fetch(LLMs)
        if self.model:
            llm_api = llms.new_api(self.service, self.model)
        else:
            llm_api = llms.get_api(self.llm_api)
        return llm_api
