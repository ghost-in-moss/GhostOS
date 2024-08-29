from ghostos.core.moss import test_container
from ghostos.core.moss.abc import MossCompiler, Moss, MOSS_TYPE_NAME
from ghostos.core.moss.pycontext import PyContext
from ghostos.core.moss.examples import mem_baseline as baseline


from rich.console import Console
from rich.markdown import Markdown


def json_format(data: str) -> Markdown:
    return Markdown(f"""
```json
{data}
```
""")


def default_converter(o):
    if isinstance(o, PyContext):
        return ""  # 或者 o.isoformat() 等其他格式
    raise TypeError("Object of type '%s' is not JSON serializable" % type(o).__name__)


def test_mem_exec():

    container = test_container()
    compiler = container.force_fetch(MossCompiler)

    compiler.join_context(PyContext(module=baseline.__name__))
    code = compiler.pycontext_code()
    assert "from __future__" in code

    runtime = compiler.compile(None)

    moss = runtime.moss()
    assert isinstance(moss, Moss)

    prompter = runtime.prompter()
    assert prompter is not None

    result = runtime.execute(target="test_main", local_args=["moss"])
    console = Console()
    for item in result:
        if isinstance(item, str):
            # Split the string on new line characters and print each part on a new line
            for line in item.split('\\n'):
                console.print(line)
        else:
            # If it's not a string, just print it as it is
            console.print(item)

    assert 'successfully' in result.std_output

    # 最后成功销毁.
    runtime.destroy()


if __name__ == '__main__':
    test_mem_exec()

