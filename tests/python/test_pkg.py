import pkgutil


def test_iter_modules():
    from ghostos.core import moss
    values = pkgutil.iter_modules(moss.__path__, prefix=moss.__name__ + '.')
    assert len(list(values)) > 1
