from ghostiss import helpers


def test_camel_to_snake():
    assert helpers.camel_to_snake("FooBar") == "foo_bar"
    assert helpers.camel_to_snake("FooBar__") == "foo_bar__"
    assert helpers.camel_to_snake("Foo01") == "foo01"
    assert helpers.camel_to_snake("MoOS") == "mo_os"

    cases = [
        ("FooBar", "foo_bar"),
        ("MOOOS", "mooos"),
        ("Laravel", "laravel"),
    ]

    for origin, expect in cases:
        assert helpers.camel_to_snake(origin) == expect

