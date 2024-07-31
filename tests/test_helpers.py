from ghostiss import helpers


def test_camel_to_snake():
    assert helpers.camel_to_snake("FooBar") == "foo_bar"
    assert helpers.camel_to_snake("FooBar__") == "foo_bar__"
    assert helpers.camel_to_snake("Foo01") == "foo01"
    assert helpers.camel_to_snake("MOSS") == "mo_os"

    cases = [
        ("FooBar", "foo_bar"),
        ("MOOOS", "mooos"),
        ("Laravel", "laravel"),
    ]

    for origin, expect in cases:
        assert helpers.camel_to_snake(origin) == expect


def test_get_calling_module():
    module = helpers.get_calling_module(1)
    assert module == "test_helpers"

    module = helpers.get_calling_module_test()
    assert module == "ghostiss.helpers"


def test_yaml_pretty_dump():
    import yaml
    from ghostiss.helpers import yaml_pretty_dump

    data = {"foo": "foo\nbar"}
    dumped = yaml_pretty_dump(data)
    assert "|" in dumped

    data2 = yaml.safe_load(dumped)
    assert "|" not in data2
