import inspect
from typing import Optional, TypeVar, Generic, Type, Iterable
from abc import ABC, abstractmethod
from ghostos.entity import Entity, ModelEntity
from ghostos.core.session import Event, MsgThread, Session
from ghostos.core.ghosts.ghost import Ghost
from ghostos.core.ghosts.operators import Operator
from ghostos.abc import Identifiable, Identifier, PromptAbleClass
from ghostos.helpers import uuid, generate_import_path
from pydantic import Field

__all__ = ['Thought', 'ModelThought', 'ThoughtDriver', 'BasicThoughtDriver', "Mindset", "get_thought_driver_type", 'T']


class Thought(Identifiable, Entity, ABC):
    """
    The Thought class serves as a fundamental component of AI,
    adept at initiating a stateful task to address specific inquiries.
    It is a thinking unit of the Agent that can handle a specific type of task.
    """

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
    def __class_prompt__(cls) -> str:
        if cls is Thought:
            return '''
class Thought(ABC):
    """
    The Thought class serves as a fundamental component of AI, 
    adept at initiating a stateful task to address specific inquiries.
    """
    pass
'''
        return inspect.getsource(cls)


class ModelThought(Thought, ModelEntity, PromptAbleClass, ABC):
    """
    The abstract model of the thought based by pydantic.BaseModel.
    """

    def identifier(self) -> Identifier:
        cls = self.__class__
        import_path = generate_import_path(cls)
        return Identifier(
            name=import_path,
            description=str(cls.__doc__),
        )

    @classmethod
    def __class_prompt__(cls) -> str:
        if cls is ModelThought:
            return '''
class ThoughtModel(Thought, BaseModel, ABC):
    """
    The abstract type of Thought that based on pydantic.BaseModel. 
    """
    name: str = Field(description="name of the thought")
    description: str = Field(description="description of the thought")
'''
        return inspect.getsource(cls)


def get_thought_driver_type(cls: Type[Thought]) -> Type["ThoughtDriver"]:
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


class ThoughtDriver(Generic[T], ABC):
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


class BasicThoughtDriver(Generic[T], ThoughtDriver[T], ABC):
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
        session = g.session()
        thread = session.thread()
        self.prepare_thread(session, thread)
        session.update_thread(thread, False)

        return self.think(g, e)

    @staticmethod
    def prepare_thread(session: Session, thread: MsgThread) -> MsgThread:
        """
        prepare thread usually defining thread id and thread.save_file for debug reason
        """
        process_id = session.process().process_id
        task = session.task()
        thread.save_file = f"process_{process_id}/task_{task.name}_thread_{thread.id}.yml"
        return thread

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
