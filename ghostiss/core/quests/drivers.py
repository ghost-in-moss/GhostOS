from typing import Tuple, List, Dict, Optional
from abc import ABC, abstractmethod
from ghostiss.container import Container
from ghostiss.core.llms import Chat, LLMApi
from ghostiss.core.quests.itf import QuestDriver, Step, QuestAction
from ghostiss.core.messages import Message, Caller
from ghostiss.core.session import MsgThread, thread_to_chat, Messenger, Threads


class LLMQuestDriver(QuestDriver, ABC):
    """
    基于大模型运行的 Quest driver
    """

    @abstractmethod
    def system_messages(self) -> List[Message]:
        """
        生成系统消息.
        """
        pass

    @abstractmethod
    def get_llm_api(self, container: Container) -> LLMApi:
        """
        获取 llm api
        """
        pass

    @abstractmethod
    def actions(self, container: Container, thread: MsgThread) -> List[QuestAction]:
        """
        生成所有的 Quest Action
        :param container:
        :param thread:
        :return:
        """
        pass

    def run(self, container: Container, messenger: Messenger, thread: MsgThread) -> Tuple[MsgThread, Step]:
        """
        默认的运行逻辑.
        :param container:
        :param messenger:
        :param thread:
        :return:
        """

        # 获取系统消息.
        systems = self.system_messages()
        # 使用默认的方法, 将 thread 转成 chat.
        chat = thread_to_chat(thread.id, systems, thread)

        actions = self.actions(container, thread)
        action_map = {}
        for action in actions:
            # 用 action 添加必要的信息给 chat.
            chat = action.update_chat(chat)
            action_map[action.identifier().name] = action

        # 获取 llm 的 api.
        llm_api = self.get_llm_api(container)
        llm_api.deliver_chat_completion(chat, messenger)
        # 仍然获取 messages 和 caller.
        messages, callers = messenger.flush()
        # 消息添加到 thread.
        thread.append(*messages)
        # 用 caller 做响应.
        return self.on_callers(container, action_map, thread, callers)

    def on_callers(
            self,
            container: Container,
            actions: Dict[str, QuestAction],
            thread: MsgThread,
            callers: List[Caller],
    ) -> Tuple[MsgThread, Optional[Step]]:
        for caller in callers:
            action = actions.get(caller.name, None)
            # todo, 再做一个异步的.
            if action is not None:
                thread, step = action.callback(thread, caller)
                if step is not None:
                    return thread, step
        return thread, None

    def on_finish(self, container: Container, thread: MsgThread) -> None:
        # 如果 threads 抽象存在, 就保存一下. 还应该做一些日志的工作.
        threads = container.get(Threads)
        if threads is not None:
            threads.save_thread(thread)
