import re


def test_str_search():
    origin = "foo.yaml"
    s = re.search(r'\.yaml$', origin)
    assert s is not None
    assert origin[s.pos: s.endpos] == "foo.yaml"
