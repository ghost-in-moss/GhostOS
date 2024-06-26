import os
from ghostiss.contracts.storage import FileStorage


def _prepare_storage() -> FileStorage:
    path = os.path.dirname(__file__)
    storage = FileStorage(path)
    return storage


def test_file_storage():
    storage = _prepare_storage()
    value = storage.get("foo.yaml")
    assert value is not None
    storage.put("foo.yaml", value)
    value2 = storage.get("foo.yaml")
    assert value == value2


def test_file_storge_dir_with_pattern():
    storage = _prepare_storage()
    iterator = storage.dir("", False, r'yaml')
    files = list(iterator)
    assert len(files) == 1
    assert files[0] == "foo.yaml"

    # 包含了其它文件.
    iterator = storage.dir("", True)
    assert len(list(iterator)) > 0
