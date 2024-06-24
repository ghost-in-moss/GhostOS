import os


def test_path_join():
    value = os.path.join("/a/b/c", "d/e/f")
    assert value == "/a/b/c/d/e/f"

    value = os.path.join("/a/b/c", "/d/e/f")
    assert value == "/d/e/f"
