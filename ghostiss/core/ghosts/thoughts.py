from typing import Optional, List, TypeVar, ClassVar, Generic, Type, Tuple
from abc import ABC, abstractmethod
from ghostiss.entity import Entity, EntityMeta, EntityFactory
from ghostiss.core.ghosts.ghost import Ghost
from ghostiss.core.session.events import Event
from ghostiss.core.ghosts.operators import Operator
from ghostiss.core.ghosts.runner import Runner
from ghostiss.abc import Identifiable, Identifier, IdentifiableClass
from ghostiss.helpers import uuid


class Thought(Identifiable, ABC):
    """
    用代码的方式实现的思维链描述, 是 Llm-based Agent 的思维单元.
    可以用来创建并且驱动一个任务.
    Thought 有着各种实现, 包括聊天, 使用工具, 决策, 规划等等.
    因此 Thought 的实例可以视作将成熟的知识和经验封装为可复用的记忆碎片.
    只要继承自 Thought 类, 就可以驱动思维.
    """

    """
    tips:
    从工程设计的角度看, Thought 不要用继承的方式定义使用, 而应该用组合的方式.
    每个 Thought 都应该是完备的 BaseModel. 不要使用继承. 
    这样可以最好地自解释.
    对于复杂度比较高的 Thought, 可以用函数来实现一些子封装. 
    """

    __thought_driver__: ClassVar[Optional[Type["ThoughtDriver"]]] = None
    """
    定义 Thought 类的Driver.
    依照约定优先于配置, driver 为 None 时, 系统默认从 Thought 所属模块取 Thought.__name__ + 'Driver' 的类作为 Driver. 
    """

    @abstractmethod
    def identifier(self) -> Identifier:
        """
        生成一个 Identifier 的实例用来描述 Thought 的实例.
        """
        pass


T = TypeVar("T", bound=Thought)


class ThoughtDriver(Generic[T], Entity, IdentifiableClass, ABC):
    """
    ThoughtDriver 是 Thought 运行时生成的实例.
    实际上就是把 Python 的 Class 拆成了 Model (数据结构) + Driver (各种 methods)
    这样 Thought 作为一个 Model, 可以直接将源码呈现给大模型, 用于各种场景的使用.

    同时也起到一个双向数据桥梁的作用:
    1. Thought => ThoughtInstance => EntityMeta
    2. EntityMeta => ThoughtInstance => Thought
    """

    def __init__(self, thought: T):
        """
        实例化 ThoughtDriver, 这个方法入参不要修改. 系统要使用这个方法实例化.
        """
        self.thought: T = thought

    @classmethod
    @abstractmethod
    def class_identifier(cls) -> Identifier:
        """
        这里是 Driver 对自身的描述.
        可以用来召回某种类型的 thought 类.
        """
        pass

    @classmethod
    @abstractmethod
    def entity_type(cls) -> str:
        """
        ThoughtDriver 可以生成 EntityMeta, 这个方法返回它固定的 entity_type
        用来反查 Driver.
        """
        pass

    @abstractmethod
    def to_entity_meta(self) -> EntityMeta:
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

    def new_task_id(self, g: Ghost) -> str:
        # 如果生成的 task id 是不变的, 则在同一个 process 里是一个单例. 但要考虑互相污染的问题.
        return uuid()

    def on_create(self, g: Ghost, e: Event) -> Optional[Operator]:
        """
        基于 Thought 创建了 Task 时触发的事件.
        可以根据事件做必要的初始化.
        """
        #  默认没有任何动作.
        return None

    def on_finished(self, g: Ghost, e: Event) -> Optional[Operator]:
        """
        当前 Thought 所生成的 task 结束之后, 会回调的事件.
        """
        # 默认没有任何动作.
        return None

    def on_input(self, g: Ghost, e: Event) -> Optional[Operator]:
        """
        接受到一个外部事件后执行的逻辑.
        """
        return self._run_event(g, e)

    @abstractmethod
    def runner(self, g: Ghost, e: Event) -> Runner:
        pass

    def _run_event(self, g: Ghost, e: Event) -> Optional[Operator]:
        runner = self.runner(g, e)
        session = g.session
        thread = session.thread()
        # thread 更新消息体.
        thread.inputs = e.messages
        messenger = g.messenger()
        # 执行 runner.
        op = runner.on_inputs(g.container, messenger, thread)
        return op

    def on_finish_callback(self, g: Ghost, e: Event) -> Optional[Operator]:
        session = g.session
        task = session.task()
        awaiting = task.awaiting_tasks()
        if e.from_task_id not in awaiting:
            # todo: log
            return None
        # 添加消息.
        messenger = g.messenger()
        thread = session.thread()
        thread.inputs = e.messages

        fulfilled = task.update_awaits(e.from_task_id)
        session.update_task(task)

        op = None
        if fulfilled:
            runner = self.runner(g, e)
            thread, op = runner.on_inputs(g.container, messenger, thread)
        session.update_thread(thread)
        return op

    def on_failure_callback(self, g: Ghost, e: Event) -> Optional[Operator]:
        return self._run_event(g, e)

    def on_wait_callback(self, g: Ghost, e: Event) -> Optional[Operator]:
        return self._run_event(g, e)


class Thoughts(ABC):
    """
    思维集合, 用来管理所有可以使用的 Thought 实例.
    是一个可持续学习, 召回的记忆空间.
    """

    @abstractmethod
    def make_thought_instance(self, meta: EntityMeta) -> Optional[ThoughtDriver]:
        """
        使用 meta 来获取一个 ThoughtDriver 实例. 其中也包含了 Thought 数据的实例.
        :param meta: thought 生成的可序列化数据.
        :return:
        """
        pass

    def force_make_thought(self, meta: EntityMeta) -> ThoughtDriver:
        """
        语法糖.
        """
        instance = self.make_thought_instance(meta)
        if instance is None:
            raise ModuleNotFoundError(f'No Thoughts found for {meta}')
        return instance

    @abstractmethod
    def instance_thought(self, thought: Thought) -> ThoughtDriver:
        """
        通过代码空间的 Thought 实例来生成一个 ThoughtDriver 的实例, 使之具备响应上下文的能力.
        :param thought:
        :return:
        """
        pass

    @abstractmethod
    def register_thought_type(self, cls: Type[Thought], driver: Optional[Type[ThoughtDriver]] = None) -> None:
        """
        注册一个 thought class, 还可以替换它的 driver.

        系统默认的优先级应该是:
        1. registered driver.
        2. thought's defined driver in __thought_driver__
        3. thought class's __name__ + 'Driver' in the same module.

        如果无法解析出任何 driver, 需要抛出异常.

        注册动作会默认将 ThoughtDriver 的 Identifier 做为索引, 方便根据需要反查到 Thought.
        :param cls:
        :param driver:
        :return:
        """
        pass

    @abstractmethod
    def get_driver(self, cls: Type[Thought]) -> ThoughtDriver:
        """
        使用 Thought 的类反查 Driver.
        :param cls:
        :return:
        """
        pass

    @abstractmethod
    def recall_thought_type(
            self,
            # path: str,
            # name: str,
            # description: str,
            recollection: str,
            limit: int, offset: int = 0,
    ) -> List[Tuple[Type[Thought], Identifier]]:
        """
        召回已经注册过的 thought 类, 和它对应 Driver 的 Identifier.
        """
        pass

    @abstractmethod
    def recall_thought_instance(self, description: str, limit: int, offset: int = 0) -> List[Thought]:
        """
        召回一个 Thought 的实例.
        :param description:
        :param limit:
        :param offset:
        :return:
        """
        pass
