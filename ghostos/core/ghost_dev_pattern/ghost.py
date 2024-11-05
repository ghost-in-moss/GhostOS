from abc import ABC, abstractmethod
from typing import (
    Protocol, Self, Generic, Type, TypeVar, Tuple, Callable, Union, Optional, List, Literal, Dict,
    Iterable, ClassVar,
)
from .concepts import State, Func, Context, Task, OP
from .runtime import Runtime
from ghostos.container import Container, Contracts
from ghostos.core.moss import PyContext, Moss, MossCompiler
from ghostos.core.session import Session, Event
from ghostos.core.messages import Message
from ghostos.common import IDAbleClass, identify_class, Identifier, Identical
from ghostos.entity import EntityMeta
from pydantic import BaseModel, Field
from contextlib import contextmanager

"""
Ghost 是面向开发者的抽象设计. 
它是 Agent 运行时中最小有状态的思维单元. 开发者可以通过定义 Ghost, 来定义 Agent 可分形嵌套的思维能力. 

Ghost 的定位类似于前端 React 框架的 ReactComponent, 或是 MVC 开发框架里的 Controller. 包含的核心功能: 
1. 响应一个 Task, 并且最终管理 Task 的输出, task.result
2. 管理 Task 运行时的状态, 也就是 Thought. 包含创建, 修改, 完成, 失败等. 
3. 管理有状态的子任务, 也就是 Thought. 包含创建, 取消, 发送消息. 
4. 响应运行过程中接受到的的事件. 作出行动. 
5. 调用 LLM 作为资深的驱动. 由 Ghost 子类实现. 子类的任务包括: 
   - 提供 prompt
   - 提供上下文. 
   - 提供工具, 通常是用 moss 提供的代码交互界面. 
   - 运行大模型. 
   - 执行大模型生成的 actions, 将操作反馈到 runtime. 
   - 保存自身状态, 等待下一轮. 或结束, 终止当前任务. 
   
类似React 框架中, Component 通过一个 JSX Element 被调用; Web API 中, controller 通过 URL 请求被调用;
在 GhostOS 中, Ghost 可以通过 GhostFunc 的形式, 以函数的姿态被调用. 
"""


class Ghost(BaseModel, Identical, ABC):

    @abstractmethod
    def identifier(self) -> Identifier:
        pass

    @classmethod
    def default(cls) -> Self:
        pass

    __fsm__: ClassVar[str] = None


G = TypeVar("G", bound=Ghost)
F = TypeVar("F", bound=Func)
S = TypeVar("S", bound=State)
M = TypeVar("M", bound=Moss)
""" G.F.S.M. => ghost finite state machine"""


class GhostFSM(Protocol[G, F, S, M]):
    state: S
    task: Task[F]

    def __init__(self, ghost: G, task: Task[F], state: S):
        self.ghost = ghost
        self.task = task
        self.state = state

    def identifier(self) -> Identifier:
        return self.ghost.identifier()

    @contextmanager
    def container(self, container: Container) -> Container:
        container = Container(parent=container)
        # bind state
        container.set(State, self.state)
        container.set(self.state.__class__, self.state)
        # bind task
        container.set(Task, self.task)
        container.set(Ghost, self.ghost)
        # bind ghost
        container.set(self.ghost.__class__, self.ghost)
        container.set(Ghost, self.ghost)
        # bind fsm
        container.set(GhostFSM, self)
        container.set(self.__class__, self)
        yield container
        container.destroy()

    @classmethod
    @abstractmethod
    def on_create(cls, runtime: Runtime, ctx: Context[F, S, M]) -> OP:
        pass

    @abstractmethod
    def on_event(self, runtime: Runtime, ctx: Context[F, S, M], event: Event) -> OP:
        pass

    @abstractmethod
    def run(
            self,
            ctx: Context[F, S, M],
            history: List[Message],
            inputs: Iterable[Message],
    ) -> Iterable[Message]:
        pass
