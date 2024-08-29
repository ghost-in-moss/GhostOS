from typing import Optional, TypeVar, Generic, Type, Iterable
from abc import ABC, abstractmethod
from ghostos.entity import Entity, EntityMeta, EntityFactory
from ghostos.core.session import Event, thread_to_chat
from ghostos.core.llms import LLMApi, prepare_chat, ChatPreparer, Chat
from ghostos.core.messages import Role
from ghostos.core.ghosts.ghost import Ghost
from ghostos.core.ghosts.operators import Operator
from ghostos.core.ghosts.actions import Action
from ghostos.abc import Identifiable, Identifier
from ghostos.helpers import uuid

__all__ = ['Thought', 'ThoughtDriver', 'LLMThoughtDriver', "Mindset"]


class Thought(Identifiable, ABC):
    """
    用代码的方式实现的思维链描述, 是 Llm-based Agent 的思维单元.
    可以用来创建并且驱动一个任务.
    Thought 有着各种实现, 包括聊天, 使用工具, 决策, 规划等等.
    因此 Thought 的实例可以视作将成熟的知识和经验封装为可复用的记忆碎片.
    只要继承自 Thought 类, 就可以驱动思维.
    """

    # tips:
    # 从工程设计的角度看, Thought 不要用继承的方式定义使用, 而应该用组合的方式.
    # 每个 Thought 都应该是完备的 BaseModel. 不要使用继承.
    # 这样可以最好地自解释.
    # 对于复杂度比较高的 Thought, 可以用函数来实现一些子封装.

    __thought_driver__: Optional[Type["ThoughtDriver"]] = None
    """
    定义 Thought 类的Driver.
    依照约定优先于配置, driver 为 None 时, 系统默认从 Thought 所属模块取 Thought.__qualname__ + 'Driver' 的类作为 Driver. 
    """

    @abstractmethod
    def identifier(self) -> Identifier:
        """
        生成一个 Identifier 的实例用来描述 Thought 的状态.
        """
        pass

    @classmethod
    def default_driver_type(cls) -> Type["ThoughtDriver"]:
        """
        根据约定, 将 Thought 类封装到 Driver 对象里.
        :return:
        """
        driver_type = cls.__thought_driver__
        if driver_type is None:
            thought_cls = cls
            name = thought_cls.__name__
            expect_name = f"{name}Driver"
            import inspect
            module = inspect.getmodule(thought_cls)
            if module is None or expect_name not in module.__dict__:
                raise NotImplementedError(f"{expect_name} does not exists in {thought_cls.__module__}")
            driver_type = module.__dict__[expect_name]
        return driver_type


T = TypeVar("T", bound=Thought)


class ThoughtDriver(Generic[T], Entity, ABC):
    """
    ThoughtEntity 是 Thought 运行时生成的实例.
    实际上就是把 Python 的 Class 拆成了 Model (数据结构) + Driver (各种 methods)
    这样 Thought 作为一个 Model, 可以直接将源码呈现给大模型, 用于各种场景的使用.

    同时也起到一个双向数据桥梁的作用:
    1. Thought => ThoughtInstance => EntityMeta
    2. EntityMeta => ThoughtInstance => Thought
    """

    def __init__(self, thought: T):
        """
        实例化 ThoughtEntity, 这个方法入参不要修改. 系统要使用这个方法实例化.
        """
        self.thought: T = thought

    @abstractmethod
    def to_entity_data(self) -> dict:
        """
        将 Thought 来生成 EntityMeta 对象.
        """
        pass

    @classmethod
    @abstractmethod
    def from_entity_meta(cls, factory: EntityFactory, meta: EntityMeta) -> "ThoughtDriver":
        """
        结合 Factory, 将一个 EntityMeta 反解成 ThoughtInstance.
        :param factory: 支持递归的生成 Thought 实例.
        :param meta: 原始数据.
        :return: 自身的实例.
        """
        pass

    @abstractmethod
    def new_task_id(self, g: Ghost) -> str:
        """
        创建一个唯一的 task id.
        在 create task 时会调用.
        """
        pass

    def on_event(self, g: Ghost, e: Event) -> Optional[Operator]:
        """
        接受 event 并作出响应.
        """
        name = e.type
        method = "on_" + name
        if hasattr(self, method):
            return getattr(self, method)(g, e)
        return None


class BasicThoughtDriver(ThoughtDriver, ABC):
    @abstractmethod
    def think(self, g: Ghost, e: Event) -> Optional[Operator]:
        """
        开始一轮思考.
        """
        pass

    def new_task_id(self, g: Ghost) -> str:
        # 如果生成的 task id 是不变的, 则在同一个 process 里是一个单例. 但要考虑互相污染的问题.
        return uuid()

    def on_created(self, g: Ghost, e: Event) -> Optional[Operator]:
        """
        基于 Thought 创建了 Task 时触发的事件.
        可以根据事件做必要的初始化.
        """
        op = self.think(g, e)
        if op is None:
            op = g.taskflow().awaits()
        return op

    def on_canceling(self, g: Ghost, e: Event) -> Optional[Operator]:
        """
        当前任务被取消时. 如果返回非 None 的动作, 会取消默认的逻辑.
        :param g:
        :param e:
        :return:
        """
        return None

    def on_input(self, g: Ghost, e: Event) -> Optional[Operator]:
        """
        接受到一个外部事件后执行的逻辑.
        """
        op = self.think(g, e)
        if op is None:
            op = g.taskflow().awaits()
        return op

    def on_observe(self, g: Ghost, e: Event) -> Optional[Operator]:
        """
        自己触发的观察动作.
        """
        op = self.think(g, e)
        if op is None:
            op = g.taskflow().awaits()
        return op

    def on_finished(self, g: Ghost, e: Event) -> Optional[Operator]:
        """
        当前 Thought 所生成的 task 结束之后, 回调自己的反思逻辑.
        """
        return None

    def on_failed(self, g: Ghost, e: Event) -> Optional[Operator]:
        """
        回调自己的反思逻辑.
        """
        return None

    def on_finish_callback(self, g: Ghost, e: Event) -> Optional[Operator]:
        """
        接受到了下游任务完成的回调.
        """
        return self.think(g, e)

    def on_failure_callback(self, g: Ghost, e: Event) -> Optional[Operator]:
        """
        接受到了下游任务失败的回调.
        """
        return self.think(g, e)

    def on_wait_callback(self, g: Ghost, e: Event) -> Optional[Operator]:
        """
        接受到了下游任务的提问, 需要回答.
        """
        return self.think(g, e)

    def on_notify_callback(self, g: Ghost, e: Event) -> Optional[Operator]:
        """
        一个下游的通知, 不需要做任何操作.
        """
        return None


class LLMThoughtDriver(BasicThoughtDriver, ABC):

    @abstractmethod
    def get_llmapi(self, g: Ghost) -> LLMApi:
        """
        get llm api from ghost

        maybe:
        llms = g.container.force_fetch(LLMs)
        return llms.get_api(api_name)
        """
        pass

    @abstractmethod
    def chat_preparers(self, g: Ghost, e: Event) -> Iterable[ChatPreparer]:
        """
        return chat preparers that filter chat messages by many rules.
        """
        pass

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
        meta_prompt = g.meta_prompt()
        shell_prompt = g.shell().shell_prompt()
        thought_instruction = self.instruction(g, e)
        content = "\n\n".join([meta_prompt, shell_prompt, thought_instruction])
        # system prompt from thought
        system_messages = [Role.SYSTEM.new(content=content)]
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
        actions = list(g.shell().actions())
        thought_actions = list(self.actions(g, e))
        if thought_actions:
            actions.extend(thought_actions)
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


class Mindset(ABC):
    """
    思维集合, 用来管理所有可以使用的 Thought 类.
    是一个可持续学习, 召回的记忆空间.
    """

    @abstractmethod
    def register_thought_type(self, cls: Type[Thought], driver: Optional[Type[ThoughtDriver]] = None) -> None:
        """
        注册一个 thought class, 还可以替换它的 driver.

        系统默认的优先级应该是:
        1. registered driver.
        2. thought's defined driver in __thought_driver__
        3. thought class's __name__ + 'Driver' in the same module.

        如果无法解析出任何 driver, 需要抛出异常.

        注册动作会默认将 ThoughtEntity 的 Identifier 做为索引, 方便根据需要反查到 Thought.
        :param cls:
        :param driver:
        :return:
        """
        pass

    def get_thought_driver(self, thought: Thought) -> ThoughtDriver:
        """
        使用 Thought 的类反查 Driver.
        """
        driver_type = self.get_thought_driver_type(type(thought))
        return driver_type(thought)

    @abstractmethod
    def get_thought_driver_type(self, thought_type: Type[Thought]) -> Type[ThoughtDriver]:
        """
        返回与 Thought 类型对应的 ThoughtDriver 类型.
        :param thought_type:
        :return:
        """
        pass

    @abstractmethod
    def thought_types(self) -> Iterable[Type[Thought]]:
        """
        遍历所有注册的 thought types.
        :return:
        """
        pass
