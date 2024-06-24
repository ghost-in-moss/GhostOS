def test_or_operator() -> None:
    a = "foo" or ""
    b = "" or "foo"
    assert a == b == "foo"
