from typing import Optional, Generic, Iterable
from abc import ABC, abstractmethod
from ghostos.core.session import Event, thread_to_chat
from ghostos.core.ghosts import Ghost, Operator, Action
from ghostos.core.llms import LLMApi, ChatPreparer, Chat, prepare_chat
from ghostos.core.messages import Role
from ghostos.core.ghosts.thoughts import T, BasicThoughtDriver
from ghostos.framework.chatpreparers import OtherAgentOrTaskPreparer


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

    def chat_preparers(self, g: Ghost, e: Event) -> Iterable[ChatPreparer]:
        """
        return chat preparers that filter chat messages by many rules.
        """
        assistant_name = g.conf().identifier().name
        yield OtherAgentOrTaskPreparer(
            assistant_name=assistant_name,
            task_id=g.session().task().task_id,
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

    def initialize_chat(self, g: Ghost, e: Event) -> Chat:
        session = g.session()
        thread = session.thread()
        system_prompt = g.system_prompt()
        thought_instruction = self.instruction(g, e)
        content = "\n\n".join([system_prompt, thought_instruction])
        # system prompt from thought
        system_messages = [Role.SYSTEM.new(content=content.strip())]
        chat = thread_to_chat(e.id, system_messages, thread)
        return chat

    def think(self, g: Ghost, e: Event) -> Optional[Operator]:
        session = g.session()
        container = g.container()
        logger = g.logger()

        # initialize chat
        chat = self.initialize_chat(g, e)

        # prepare chat, filter messages.
        preparers = self.chat_preparers(g, e)
        chat = prepare_chat(chat, preparers)

        # prepare actions
        actions = list(self.actions(g, e))
        action_map = {action.identifier().name: action for action in actions}

        # prepare chat by actions
        for action in actions:
            chat = action.prepare_chat(chat)

        # prepare llm api
        llm_api = self.get_llmapi(g)

        # prepare messenger
        messenger = session.messenger()

        # run llms
        logger.info(f"start llm thinking")  # todo: logger
        llm_api.deliver_chat_completion(chat, messenger)
        messages, callers = messenger.flush()

        # callback actions
        for caller in callers:
            if caller.name in action_map:
                logger.info(f"llm response caller `{caller.name}` match action")
                action = action_map[caller.name]
                op = action.act(container, session, caller)
                if op is not None:
                    return op
        return None
