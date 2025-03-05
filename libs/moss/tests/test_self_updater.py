from ghostos_moss import get_moss_compiler, PyContext
from ghostos_moss.examples import self_update_moss


def test_self_updater():
    compiler = get_moss_compiler()
    compiler.join_context(PyContext())
    runtime = compiler.compile(self_update_moss.__name__)
    with runtime:
        moss: self_update_moss.Moss = runtime.moss()
        assert moss.updater is not None
        moss.updater.append("foo = 123")
        assert "foo = 123" in runtime.dump_pycontext().code
        # moss.updater.save()
