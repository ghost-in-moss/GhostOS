import re


def test_str_match():
    assert re.search(r'\.yaml$', "foo.yaml") is not None
