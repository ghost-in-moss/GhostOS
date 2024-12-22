from typing import Optional, Generic, Iterable
from abc import ABC, abstractmethod
from ghostos.core.runtime import Event, thread_to_prompt
from ghostos.core.ghosts import Ghost, Operator, Action
from ghostos.core.llms import LLMApi, PromptPipe, Prompt, run_prompt_pipeline
from ghostos.core.messages import Role
from ghostos.core.ghosts.thoughts import T, BasicThoughtDriver
from ghostos.framework.chatpreparers import OtherAgentOrTaskPipe


class LLMThoughtDriver(Generic[T], BasicThoughtDriver[T], ABC):

    @abstractmethod
    def get_llmapi(self, g: Ghost) -> LLMApi:
        """
        get llm api from ghost

        maybe:
        llms = g.container.force_fetch(LLMs)
        return llms.get_api(api_name)
        """
        pass

    def chat_preparers(self, g: Ghost, e: Event) -> Iterable[PromptPipe]:
        """
        return chat preparers that filter chat messages by many rules.
        """
        assistant_name = g.identifier().name
        yield OtherAgentOrTaskPipe(
            assistant_name=assistant_name,
            task_id=g.session().get_task.task_id,
        )

    @abstractmethod
    def actions(self, g: Ghost, e: Event) -> Iterable[Action]:
        """
        return actions that predefined in the thought driver.
        """
        pass

    @abstractmethod
    def instruction(self, g: Ghost, e: Event) -> str:
        """
        return thought instruction.
        """
        pass

    def initialize_chat(self, g: Ghost, e: Event) -> Prompt:
        session = g.session()
        thread = session.get_thread()
        system_prompt = g.system_prompt()
        thought_instruction = self.instruction(g, e)
        content = "\n\n".join([system_prompt, thought_instruction])
        # system prompt from thought
        system_messages = [Role.SYSTEM.new(content=content.strip())]
        chat = thread_to_prompt(e.event_id, system_messages, thread)
        return chat

    def think(self, g: Ghost, e: Event) -> Optional[Operator]:
        session = g.session()
        container = g.container()
        logger = g.logger()

        # initialize chat
        chat = self.initialize_chat(g, e)

        # prepare chat, filter messages.
        preparers = self.chat_preparers(g, e)
        chat = run_prompt_pipeline(chat, preparers)

        # prepare actions
        actions = list(self.actions(g, e))
        action_map = {action.__identifier__().name: action for action in actions}

        # prepare chat by actions
        for action in actions:
            chat = action.update_prompt(chat)

        # prepare llm api
        llm_api = self.get_llmapi(g)

        # run llms
        logger.debug("start llm thinking")  # todo: logger
        # prepare messenger
        messenger = session.messenger(functional_tokens=chat.functional_tokens)
        llm_api.deliver_chat_completion(chat, messenger)
        messages, callers = messenger.flush()
        # set chat system prompt to thread
        session.get_thread().system_prompt = chat.system_prompt()

        # callback actions
        for caller in callers:
            if caller.name in action_map:
                logger.debug(f"llm response caller `{caller.name}` match action")
                action = action_map[caller.name]
                op = action.act(container, session, caller)
                if op is not None:
                    return op
        return None
