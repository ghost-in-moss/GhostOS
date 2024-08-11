from typing import Optional, List, TypeVar, ClassVar, Generic, Type
from abc import ABC, abstractmethod
from ghostiss.contracts.modules import Modules
from ghostiss.entity import Entity, ModelEntity, EntityMeta
from ghostiss.core.ghosts.ghost import Ghost
from ghostiss.core.session.events import Event
from ghostiss.core.ghosts.operators import Operator
from ghostiss.core.ghosts.runner import Runner
from ghostiss.abc import Identifiable, Descriptive, Identifier, IdentifiableClass
from ghostiss.helpers import uuid, generate_import_path, import_from_path, Importer
from ghostiss.core.moss.decorators import cls_definition

ThoughtDoc = """
用代码的方式实现的思维函数, 用来驱动一个思维链完整特定的任务. 
继承自 pydantic.BaseModel
"""


@cls_definition(doc=ThoughtDoc)
class Thought(ModelEntity, ABC):
    """
    用代码的方式实现的思维链描述, 是 Llm-based Agent 的思维单元.
    可以用来创建并且驱动一个任务.
    Thought 有着各种实现, 包括聊天, 使用工具, 决策, 规划等等.
    因此 Thought 的实例可以视作将成熟的知识和经验封装为可复用的记忆碎片.
    只要继承自 Thought 类, 就可以驱动思维.

    从工程设计的角度看, Thought 不要用继承的方式定义使用, 而应该用组合的方式.
    每个 Thought 都应该是完备的 BaseModel, 没有方法.
    这样可以最好地自解释.
    """

    __thought_driver__: ClassVar[Optional[Type["ThoughtDriver"]]] = None
    """
    定义 Thought 类的Driver.
    依照约定优先于配置, driver 为 None 时, 系统默认从 Thought 所属模块取 Thought.__name__ + 'Driver' 的类作为 Driver. 
    """


T = TypeVar("T", bound=Thought)


class ThoughtDriver(Generic[T], ABC):
    """
    ThoughtDriver 是 Thought 运行时使用的方法.
    实际上就是把 Python 的 Class 拆成了 Model (数据结构) + Driver (各种 methods)
    这样 Thought 作为一个 Model, 可以直接将源码呈现给大模型, 用于各种场景的使用.
    """

    def __init__(self, thought: T):
        """
        实例化 ThoughtDriver, 这个方法入参不要修改. 系统要使用这个方法实例化.
        """
        self.thought: T = thought

    @abstractmethod
    def new_task_id(self, process_id: str) -> str:
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


#
# # todo: remove later.
# class BasicThoughtDriver(Thought, Identifiable, Descriptive, ABC):
#
#     def new_task_id(self, g: Ghost) -> str:
#         # 如果生成的 task id 是不变的, 则在同一个 process 里是一个单例. 但要考虑互相污染的问题.
#         return uuid()
#
#     def on_create(self, g: Ghost, e: Event) -> Optional[Operator]:
#         """
#         基于 Thought 创建一个 Task 时触发的事件.
#         可以根据事件做必要的初始化.
#         """
#         #  默认没有任何动作.
#         return None
#
#     def on_finished(self, g: Ghost, e: Event) -> Optional[Operator]:
#         """
#         当前 Thought 所生成的 task 结束之后, 会回调的事件.
#         """
#         # 默认没有任何动作.
#         return None
#
#     def on_input(self, g: Ghost, e: Event) -> Optional[Operator]:
#         """
#         接受到一个外部事件后执行的逻辑.
#         """
#         return self._run_event(g, e)
#
#     @abstractmethod
#     def runner(self, g: Ghost, e: Event) -> Runner:
#         pass
#
#     def _run_event(self, g: Ghost, e: Event) -> Optional[Operator]:
#         runner = self.runner(g, e)
#         session = g.session
#         thread = session.thread()
#         # thread 更新消息体.
#         thread.inputs = e.messages
#         messenger = g.messenger()
#         # 执行 runner.
#         op = runner.run(g.container, messenger, thread)
#         return op
#
#     def on_finish_callback(self, g: Ghost, e: Event) -> Optional[Operator]:
#         session = g.session
#         task = session.task()
#         awaiting = task.awaiting_tasks()
#         if e.from_task_id not in awaiting:
#             # todo: log
#             return None
#         # 添加消息.
#         messenger = g.messenger()
#         thread = session.thread()
#         thread.inputs = e.messages
#
#         fulfilled = task.update_awaits(e.from_task_id)
#         session.update_task(task)
#
#         op = None
#         if fulfilled:
#             runner = self.runner(g, e)
#             thread, op = runner.run(g.container, messenger, thread)
#         session.update_thread(thread)
#         return op
#
#     def on_failure_callback(self, g: Ghost, e: Event) -> Optional[Operator]:
#         return self._run_event(g, e)
#
#     def on_wait_callback(self, g: Ghost, e: Event) -> Optional[Operator]:
#         return self._run_event(g, e)


class Mindset(ABC):
    """
    思维集合, 用来管理所有可以使用的 Thought 实例.
    是一个可持续学习, 召回的记忆空间.
    """

    @abstractmethod
    def make_thought(self, meta: EntityMeta) -> Optional[Thought]:
        """
        使用 meta 来获取一个 Thought 实例.
        :param meta: thought 生成的可序列化数据.
        :return:
        """
        pass

    def force_make_thought(self, meta: EntityMeta) -> Thought:
        """
        语法糖.
        """
        thought = self.make_thought(meta)
        if thought is None:
            raise ModuleNotFoundError(f'No Thoughts found for {meta}')
        return thought

    @abstractmethod
    def register_thought(self, cls: Type[Thought]) -> None:
        """
        注册一个 Thought 实例.
        :param cls:
        """
        pass

    @abstractmethod
    def register_thought_class(self, cls: Type[Thought], driver: Optional[Type[ThoughtDriver]] = None) -> None:
        """
        注册一个 thought class, 还可以替换它的 driver.
        注册动作会默认将 Thought 的 path, __name__, __doc__ 等信息去做索引.
        如果 ThoughtClass 实现了 IdentifiableClass, 则会用默认的.
        系统默认的优先级应该是: 1. registered driver. 2. thought's driver. 3. thought's module's driver. 4. ??
        :param cls:
        :param driver:
        :return:
        """
        pass

    @abstractmethod
    def recall_thought_class(
            self,
            # path: str,
            # name: str,
            # description: str,
            recollection: str,
            limit: int, offset: int = 0,
    ) -> List[Type[Thought]]:
        """
        召回已经注册过的 thought class.
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
