from typing import Iterable, List, Optional, Tuple
from abc import ABC, abstractmethod
from ghostiss.blueprint.messages.deliver import Pack, PackKind
from ghostiss.blueprint.messages.message import Message
from ghostiss.blueprint.messages.listeners import Listener

SENT = Iterable[Pack]
GENERATES = Iterable[Message]

# todo: 打算删除掉.

class Buffer(ABC):
    """
    将 pack 合并成 message.
    合并成功后, 返回 message.
    """

    @abstractmethod
    def buff(self, pack: Pack) -> Iterable[Message]:
        pass



class BreakPipelineException(Exception):
    """ pipeline shall be stopped"""
    pass


class Pipe(ABC):
    """
    pack 流式传输的一个环节.
    """

    @abstractmethod
    def buffer(self) -> Buffer:
        pass

    @abstractmethod
    def listener(self) -> Optional[Listener]:
        """
        处理过程中产生的消息.
        """
        pass

    @abstractmethod
    def fail(self, err: Exception) -> Optional[List[Pack]]:
        pass

    @abstractmethod
    def destroy(self) -> None:
        """
        考虑到 python 弱鸡的垃圾回收, 需要有一个显式的 destroy 动作.
        如果想要复用一个 pipe, 则不要回收它.
        """
        pass

    def send(self, pack: Pack) -> SENT:
        try:
            buffer = self.buffer()
            listener = self.listener()
            sent, buffered = buffer.buff(pack)
            if buffered and listener:
                # 触发监听动作.
                for msg in buffered:
                    listener.on_message(msg)
            for item in sent:
                # 吐出 buff 后生成的消息体.
                yield item
        except BreakPipelineException:
            raise
        except Exception as e:
            items = self.fail(e)
            if items is not None:
                # 如果触发的异常可以转化成 item 传输, 则继续传输.
                for item in items:
                    yield item
            else:
                # 否则抛出异常, 让外部也停止相关逻辑.
                # todo: 写日志.
                raise BreakPipelineException("unexpect exception during sending") from e

    def buffered(self) -> List[Message]:
        """
        重写这个方法, 可以对生成的消息体进行加工.
        """
        return self.buffer().buffered()


class Pipeline:
    """
    基于 yield 实现的 pack pipeline. 是同步运行的管道, 上游每处理一个 pack, 下游才会拉取一个. 当上游的遍历中断了, 下游也就没有用.

    那么为什么需要一个 Pipeline 呢?
    因为消息的处理逻辑, 可能分为好几层, 对每个包进行了加工和过滤. 举几个例子:
    1. 一个 pipe 做长短链的处理, 发现输出了短链接, 就将之转换成长链再发送.
    2. 一个 pipe 根据 buff 的消息做检查. 一旦发现有违规之类的问题, 就发送某个中断协议并结束流程.
    3. 某一段管道专门进行数据处理.
    """

    def __init__(self, pipes: List[Pipe]):
        # 注意!!! 数组越前面的 pipe, 越早处理消息体. 越后面的 pipe, 越晚处理消息体.
        self.pipes = pipes

    def append(self, pipe: Pipe) -> "Pipeline":
        self.pipes.append(pipe)
        return self

    def send(self, pack: Pack) -> SENT:
        # 如果发送流程出现异常, 则应该抛出到外层, 中断外层的输入.
        length = len(self.pipes)
        if length == 0:
            yield pack
        else:
            pipe = self.pipes[-1]
            forwards = self.pipes[:-1]
            # 启动递归.
            iterator = self._sent(pipe, pack, forwards)
            for item in iterator:
                yield item
                self._check_item(item)

    def _sent(self, pipe: Pipe, pack: Pack, forwards: List[Pipe]) -> SENT:
        next_pipe = None
        next_forwards = []
        length = len(forwards)
        if length > 0:
            next_pipe = forwards[-1]
            next_forwards = forwards[:-1]

        if not next_pipe:
            iterator = pipe.send(pack)
            for item in iterator:
                yield item
        else:
            iterator = pipe.send(pack)
            for item in iterator:
                recursive_sent = self._sent(next_pipe, item, next_forwards)
                for recursive_item in recursive_sent:
                    yield recursive_item

    def _check_item(self, p: Pack) -> None:
        if p["kind"] == PackKind.ERROR:
            raise BreakPipelineException("receive error pack")

    @abstractmethod
    def destroy(self) -> None:
        for pipe in self.pipes:
            pipe.destroy()
        del self.pipes
