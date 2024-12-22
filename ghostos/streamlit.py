from typing import Protocol, Self, TypeVar, Optional, NamedTuple, Generic
from abc import ABC, abstractmethod

__all__ = [
    'StreamlitObject', 'StreamlitRenderable',
    'is_streamlit_renderable', 'render_streamlit_object',
    'StreamlitRenderer', 'GroupRenderer',
    'Rendered',
]

T = TypeVar('T')


class Rendered(Generic[T], NamedTuple):
    value: T
    changed: bool


class StreamlitRenderable(Protocol):

    @abstractmethod
    def __streamlit_render__(self) -> Optional[Rendered[Self]]:
        pass


class StreamlitObject(ABC):
    @abstractmethod
    def __streamlit_render__(self) -> Optional[Rendered[Self]]:
        pass


class StreamlitRenderer(ABC):

    @abstractmethod
    def render(self, value: T) -> Optional[Rendered[T]]:
        pass


class GroupRenderer(StreamlitRenderer):
    def __init__(self, *renderers: StreamlitRenderer):
        self.renderers = list(renderers)

    def render(self, value: T) -> Optional[Rendered[T]]:
        for renderer in self.renderers:
            result = renderer.render(value)
            if result is None:
                continue
            return result
        return None


def is_streamlit_renderable(obj):
    return isinstance(obj, StreamlitObject) or hasattr(obj, "__streamlit_render__")


def render_streamlit_object(obj: T) -> Optional[Rendered[T]]:
    if is_streamlit_renderable(obj):
        fn = getattr(obj, "__streamlit_render__", None)
        if fn is not None:
            r = fn()
            return r
    return None
