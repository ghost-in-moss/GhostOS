from typing import Generic, TypeVar, Any, Optional, Type, ClassVar, Tuple, Dict
import json
from abc import ABC, abstractmethod
from ghostiss.container import Container
from ghostiss.core.llms import Chat, LLMTool, ChatUpdater
from ghostiss.core.moss.decorators import cls_definition, cls_source_code
from ghostiss.core.session import MsgThread, Messenger
from ghostiss.core.messages import Caller, Message, Role
from ghostiss.abc import Identifiable
from pydantic import BaseModel

__all__ = [
    'Step', 'Quest', 'QuestDriver',
    'QuestContext', 'QuestLib',
    'QuestAction', 'QuestToolAction',
]


@cls_definition()
class Step(ABC):

    @abstractmethod
    def next(
            self,
            context: "QuestContext",
            driver: "QuestDriver",
            thread: MsgThread,
    ) -> Tuple[MsgThread, Optional["Step"]]:
        pass


@cls_definition()
class Quest(ABC):
    __result_type__: ClassVar[Type]
    __quest_driver__: ClassVar[Optional[Type["QuestDriver"]]] = None


Q = TypeVar('Q', bound=Quest)


class QuestAction(Identifiable, ChatUpdater, ABC):
    """
    能够在 Quest 里直接使用的工具.
    """

    @abstractmethod
    def update_chat(self, chat: Chat) -> Chat:
        """
        更新 chat 信息.
        :param chat:
        :return:
        """
        pass

    @abstractmethod
    def callback(self, thread: MsgThread, caller: Caller) -> Tuple[MsgThread, Optional[Step]]:
        """
        响应 chat callback.
        """
        pass


class QuestToolAction(QuestAction, ABC):
    """
    更加传统的 Quest 工具.
    通过 BaseModel 生成 json schema, 然后让 llm 调用 tool 的方式生成消息.
    """

    @classmethod
    @abstractmethod
    def args_model(cls) -> Type[BaseModel]:
        pass

    @abstractmethod
    def handle(self, arguments: BaseModel) -> Any:
        pass

    def update_chat(self, chat: Chat) -> Chat:
        chat.functions.append(self.as_llm_tool())
        return chat

    def callback(self, thread: MsgThread, caller: Caller) -> Tuple[MsgThread, Optional[Step]]:
        model = self.args_model()
        data = json.loads(caller.arguments)
        args = model(**data)
        result = self.handle(args)
        if isinstance(result, Step):
            step: Step = result
            return thread, step
        elif isinstance(result, Message):
            thread.append(result)
            return thread, None
        else:
            message = Role.TOOL.new(content=str(result)) if caller.id else Role.FUNCTION.new(content=str(result))
            thread.append(message)
            return thread, None

    def as_llm_tool(self) -> LLMTool:
        identifier = self.identifier()
        model = self.args_model()
        return LLMTool.new(
            name=identifier.name,
            desc=identifier.description,
            parameters=model.model_json_schema(),
        )


class QuestDriver(Generic[Q], ABC):
    """
    Quest 的驱动类库.
    和 Quest 类有对应关系.
    默认 Quest 类目录下, Quest.__name__ + 'Driver' 就是 quest driver.
    这是为了分离 Quest 的数据结构, 和它的方法. 数据结构可以自解释, 方法不需要对外呈现.
    """

    def __init__(self, quest: Q):
        self.quest: Q = quest

    @abstractmethod
    def init(self) -> MsgThread:
        pass

    @abstractmethod
    def run(self, container: Container, messenger: Messenger, thread: MsgThread) -> Tuple[MsgThread, Step]:
        """
        运行这个 Chat, 获取状态变更.
        :param container: ioc container that provide libraries
        :param messenger:
        :param thread: thread
        :return: (updated chat, next step)
        """
        pass

    @abstractmethod
    def on_finish(self, container: Container, thread: MsgThread) -> None:
        """
        一切运行结束的时候, 保存 chat 数据.
        :param container:
        :param thread:
        :return:
        """
        pass


@cls_source_code()
class QuestLib(ABC):
    """
    可以给大模型使用的类库, 直接操作子 task.
    todo: 将 doc 替换成 大模型想看的 doc.
    """

    @abstractmethod
    def run(self, key: str, quest: Quest) -> Any:
        """
        运行一个 Quest, 将结果保存到 key 里, 同时返回它.
        :param key:
        :param quest:
        :return:
        """
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        从保存的值中返回一个 key.
        :param key:
        :return:
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any):
        """
        将任意值设置到上下文里, 可以通过 get 获取.
        :param key:
        :param value:
        :return:
        """
        pass

    @abstractmethod
    def observe(self, **kwargs) -> Step:
        """
        观察多个值的结果, 引发下一轮思考.
        :param kwargs:
        :return:
        """
        pass

    @abstractmethod
    def finish(self, result: Any) -> Step:
        """
        结束运行, 返回 result.
        :param result:
        :return:
        """
        pass


class QuestContext(QuestLib, ABC):
    """
    真实的 Quest Context, 虽然继承自 QuestLib, 但不给大模型感知以下方法.
    必要的话, 可以包一层 Adapter.
    """

    @abstractmethod
    def container(self) -> Container:
        pass

    @abstractmethod
    def execute(self, quest: Quest) -> Any:
        """
        执行 quest.
        :param quest:
        :return:
        """
        pass

    @abstractmethod
    def messenger(self) -> Messenger:
        pass

    @abstractmethod
    def sub_context(self) -> "QuestContext":
        pass

    @abstractmethod
    def set_result(self, result: Any) -> None:
        pass

    @abstractmethod
    def values(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def destroy(self) -> None:
        pass
