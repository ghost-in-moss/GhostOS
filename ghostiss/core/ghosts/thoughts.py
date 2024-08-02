from typing import Optional, List
from abc import ABC, abstractmethod
from ghostiss.entity import Entity, EntityFactory
from ghostiss.core.ghosts.ghost import Ghost
from ghostiss.core.ghosts.events import Event
from ghostiss.core.ghosts.operators import Operator
from ghostiss.core.ghosts.runner import Runner
from ghostiss.abc import Identifiable, Descriptive, Identifier
from ghostiss.helpers import uuid
from ghostiss.core.moss.exports import Exporter


class Thought(Entity, Identifiable, Descriptive, ABC):
    """
    用代码的方式实现的思维链描述, 是 Llm-based Agent 的思维单元.
    可以用来创建并且驱动一个任务.
    Thought 有着各种实现, 包括聊天, 使用工具, 决策, 规划等等.
    因此 Thought 的实例可以视作将成熟的知识和经验封装为可复用的记忆碎片.
    只要继承自 Thought 类, 就可以驱动思维.

    每个 Thought 都要实现 Identifier, 因此有三个关键信息:
    1. id: 用 python 的 module.module:spec 风格描述的一个全局唯一的 thought 路径.
    2. name: thought 可以描述的名称.
    3. description: thought 实例的用途, 能力, 使用思路的简单描述.
    """

    @abstractmethod
    def get_description(self) -> str:
        pass

    @abstractmethod
    def new_task_id(self, g: Ghost) -> str:
        """
        创建一个唯一的 task id.
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


class BasicThought(Thought, Identifiable, Descriptive, ABC):

    def new_task_id(self, g: Ghost) -> str:
        # 如果生成的 task id 是不变的, 则在同一个 process 里是一个单例. 但要考虑互相污染的问题.
        return uuid()

    def on_create(self, g: Ghost, e: Event) -> Optional[Operator]:
        """
        基于 Thought 创建一个 Task 时触发的事件.
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
        op = runner.run(g.container, messenger, thread)
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
            thread, op = runner.run(g.container, messenger, thread)
        session.update_thread(thread)
        return op

    def on_failure_callback(self, g: Ghost, e: Event) -> Optional[Operator]:
        return self._run_event(g, e)

    def on_wait_callback(self, g: Ghost, e: Event) -> Optional[Operator]:
        return self._run_event(g, e)


class Mindset(EntityFactory[Thought], ABC):
    """
    思维集合, 用来管理所有可以使用的 Thought 实例.
    是一个可持续学习, 召回的记忆空间.
    """

    @abstractmethod
    def recall(self, description: str, limit: int = 10, offset: int = 0) -> List[Identifier]:
        """
        尝试使用描述, 从 mindset 中召回一个 Thought 实例.
        :param description: 用自然语言描述想要回忆的对象. 可以是: 你当前的需求|你对某个工具或能力的期望|这个 thought 实例可能的 desc 等.
        :param limit: 召回的最大数量. 会根据接近程度进行排序, 越前面的越高.
        :param offset: 如果召回的数据量非常大, 可以通过 offset + limit 来遍历数据.
        :return: 返回搜索到的 Thought 的 Identifier. 只保留 id, name, description. 未来可以用 id 召回某个精确的 thought 实例.
        """
        pass

    @abstractmethod
    def remember(self, thought: Thought) -> None:
        """
        记住一个思维实例, 可以在未来召回.
        通过这个方法, 可以把 thought 作为 记忆|工具|能力 等保存在思维里.
        """
        pass

    @abstractmethod
    def get_thought(self, thought_id: str) -> Optional[Thought]:
        """
        使用 id 来查找一个 Thought 实例. 前提是已经知道它的 id.
        :param thought_id: Thought 实例通常会有一个可识别的 identifier, 提供唯一 id.
        """
        pass

    @abstractmethod
    def force_get_thought(self, thought_id: str) -> Thought:
        """
        对 get_thought 的封装, 如果目标 thought 不存在会抛出 NotFoundError
        """
        pass


EXPORTS = Exporter().class_sign(Thought).interface(Mindset).model(Identifier)
