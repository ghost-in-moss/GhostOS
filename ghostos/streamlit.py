from typing import Protocol
from abc import ABC, abstractmethod

__all__ = [
    'StreamlitObject', 'StreamlitRenderable',
    'is_streamlit_renderable', 'render_streamlit_object',
    'StreamlitRenderer', 'GroupRenderer',
]


class StreamlitRenderable(Protocol):

    @abstractmethod
    def __streamlit_render__(self):
        pass


class StreamlitObject(ABC):
    @abstractmethod
    def __streamlit_render__(self):
        pass


class StreamlitRenderer(ABC):

    @abstractmethod
    def render(self, value) -> bool:
        pass


class GroupRenderer(StreamlitRenderer):
    def __init__(self, *renderers: StreamlitRenderer):
        self.renderers = list(renderers)

    def render(self, value) -> bool:
        for renderer in self.renderers:
            if renderer.render(value):
                return True
        return False


def is_streamlit_renderable(obj):
    return isinstance(obj, StreamlitObject) or hasattr(obj, "__streamlit_render__")


def render_streamlit_object(obj) -> bool:
    if is_streamlit_renderable(obj):
        fn = getattr(obj, "__streamlit_render__", None)
        if fn is not None:
            fn()
            return True
    return False
