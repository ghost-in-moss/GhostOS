from typing import Optional

from ghostos.streamlit import (
    is_streamlit_renderable,
    StreamlitObject,
    render_streamlit_object,
    Rendered
)


def test_render_streamlit_object():
    class Foo(StreamlitObject):

        def __streamlit_render__(self) -> Optional[Rendered]:
            return Rendered(value=self, changed=False)

    foo = Foo()
    assert is_streamlit_renderable(foo)
    r = render_streamlit_object(foo)
    assert not r.changed
    assert r.value is foo
