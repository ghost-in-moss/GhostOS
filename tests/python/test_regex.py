from typing import NamedTuple, List, Tuple
import re


def test_str_search():
    origin = "foo.yaml"
    s = re.search(r'\.yaml$', origin)
    assert s is not None
    assert origin[s.pos: s.endpos] == "foo.yaml"


def test_path_match():
    cases: List[Tuple[str, str, bool]] = [
        ("__init__.cpython-312.pyc", r'\.pyc$', True),
        ("__pycache__/abc.pyc", r'__pycache__', True),
        ("__pycache__/__init__.cpython-312.pyc", r'\.pyc$|__pycache__', True),

    ]
    for path, pattern, match in cases:
        m = re.search(pattern, path)
        assert match == (m is not None), f" {pattern}; {path}; {match}"
