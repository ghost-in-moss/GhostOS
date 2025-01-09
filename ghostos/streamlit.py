from typing import Protocol, Optional, NamedTuple, Any
from abc import ABC, abstractmethod

__all__ = [
    'StreamlitObject', 'StreamlitRenderable',
    'is_streamlit_renderable', 'render_streamlit_object',
    'StreamlitRenderer', 'GroupRenderer',
    'Rendered',
]


class Rendered(NamedTuple):
    value: Any
    changed: bool


class StreamlitRenderable(Protocol):

    @abstractmethod
    def __streamlit_render__(self) -> Optional[Rendered]:
        pass


class StreamlitObject(ABC):
    @abstractmethod
    def __streamlit_render__(self) -> Optional[Rendered]:
        pass


class StreamlitRenderer(ABC):

    @abstractmethod
    def render(self, value) -> Optional[Rendered]:
        pass


class GroupRenderer(StreamlitRenderer):
    def __init__(self, *renderers: StreamlitRenderer):
        self.renderers = list(renderers)

    def render(self, value) -> Optional[Rendered]:
        for renderer in self.renderers:
            result = renderer.render(value)
            if result is None:
                continue
            return result
        return None


def is_streamlit_renderable(obj):
    return isinstance(obj, StreamlitObject) or hasattr(obj, "__streamlit_render__")


def render_streamlit_object(obj) -> Optional[Rendered]:
    if is_streamlit_renderable(obj):
        fn = getattr(obj, "__streamlit_render__", None)
        if fn is not None:
            r = fn()
            return r
    return None
