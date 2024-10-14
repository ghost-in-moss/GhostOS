from abc import abstractmethod
from typing import Iterable, Callable, Tuple
from typing_extensions import Literal, Protocol, Self

__all__ = [
    "Item", "Message",
    "Delivery",
    "UpStream", "Connection",
    "Pipe", "Pipeline", "PipeAdapter",
    "build_pipeline",
]


class Item(Protocol):
    """
    消息协议中的最小传输单元.
    """

    @abstractmethod
    def seq(self) -> Literal["head", "chunk", "complete"]:
        pass


class Message(Protocol):
    """
    消息协议中一个完整的包. 包含首包, 间包, 尾包.
    """

    @abstractmethod
    def head(self) -> Item:
        pass

    @abstractmethod
    def chunks(self) -> Iterable[Item]:
        pass

    @abstractmethod
    def tail(self) -> Item:
        pass


class Delivery(Protocol):
    """
    获取一组传输的 Package, 或许需要资源回收.
    """

    @abstractmethod
    def __enter__(self) -> Iterable[Message]:
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        pass


class UpStream(Protocol):
    """
    下游向上游传输消息的方式.
    用于异步模型.
    """

    @abstractmethod
    def deliver(self, item: Item) -> bool:
        pass

    @abstractmethod
    def stopped(self) -> bool:
        pass

    @abstractmethod
    def send(self, items: Iterable[Item]) -> bool:
        pass

    @abstractmethod
    def accept_chunks(self) -> bool:
        pass

    @abstractmethod
    def __enter__(self) -> Self:
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """
        inform final or error to upstream
        :param exc_type:
        :param exc_val:
        :param exc_tb:
        :return:
        """
        pass


Connection = Callable[[...], Tuple[UpStream, Delivery]]
"""
Connection is a function create both upstream and delivery.
"""

Parser = Callable[[Iterable[Item]], Iterable[Message]]
"""
解析 Item 完成粘包. 
"""

Pipeline = Callable[[Iterable[Message]], Iterable[Message]]
"""
对流式传输的 Package 进行阻断和过滤. 
"""


class Pipe(Protocol[Pipeline]):
    """
    Pipeline 的一个中间节点. 可以任意拼组顺序.
    """

    def attach(self, pipeline: Pipeline) -> Pipeline:
        def run(inputs: Iterable[Message]) -> Iterable[Message]:
            next_inputs = self.receive(inputs)
            outputs = pipeline(next_inputs)
            return self.callback(outputs)

        return run

    @abstractmethod
    def receive(self, inputs: Iterable[Message]) -> Iterable[Message]:
        pass

    @abstractmethod
    def callback(self, outputs: Iterable[Message]) -> Iterable[Message]:
        pass


def build_pipeline(destination: Pipeline, *pipes: Pipe[Pipeline]) -> Pipeline:
    pipeline = destination
    for pipe in reversed(pipes):
        pipeline = pipe.attach(pipeline)
    return pipeline


PipeAdapter = Callable[[Pipe], Pipe]
