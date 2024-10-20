import pkgutil


def test_iter_modules():
    from ghostos.core import ghosts
    values = pkgutil.iter_modules(ghosts.__path__, prefix=ghosts.__name__ + '.')
    assert len(list(values)) > 1
