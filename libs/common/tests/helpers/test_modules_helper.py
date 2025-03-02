from ghostos_common.helpers import get_calling_modulename


def test_get_calling_modulename():
    modulename = get_calling_modulename()
    assert modulename is not None
    assert "test_modules" in modulename
