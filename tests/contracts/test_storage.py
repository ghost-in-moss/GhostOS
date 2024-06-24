import os
from ghostiss.contracts.storage import FileStorage


def test_file_storage():
    path = os.path.dirname(__file__)
    storage = FileStorage(path)
    value = storage.get("foo.yaml")
    assert value is not None
    storage.put("foo.yaml", value)
    value2 = storage.get("foo.yaml")
    assert value == value2
