from typing import TypedDict, Dict
from ghostos_common.helpers.files import is_pathname_ignored


def test_is_pathname_ignored():
    class Case(TypedDict):
        name: str
        patterns: Dict[str, bool]
        is_dir: bool

    cases = [
        Case(name="name", patterns={"name": True, "!name": False}, is_dir=True),
        Case(name=".idea", patterns={".idea": True, ".idea/": True}, is_dir=True),
    ]

    for c in cases:
        for pattern, expected in c['patterns'].items():
            try:
                assert is_pathname_ignored(c['name'], [pattern], c['is_dir']) is expected
            except AssertionError:
                print(c)
                raise
