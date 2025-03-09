from ghostos_common.helpers import (
    get_calling_modulename,
    generate_module_and_attr_name,
    get_module_fullname_from_path,
)


def test_get_calling_modulename():
    modulename = get_calling_modulename()
    assert modulename is not None
    assert "test_modules" in modulename


def test_generate_module_name_and_attr():
    from functools import wraps
    from functools import lru_cache
    def foo(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    @lru_cache()
    def bar():
        return 123

    modulename, attr = generate_module_and_attr_name(bar)
    assert "bar" in attr


def test_get_module_fullname_from_path():
    from ghostos_common import helpers
    modulename = get_module_fullname_from_path(helpers.__file__, use_longest_match=True)
    assert modulename is not None
    assert modulename.endswith("ghostos_common.helpers")
