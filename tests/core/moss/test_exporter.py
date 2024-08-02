from ghostiss.core.moss.exports import Exporter


class Foo:
    bar: int


def test_export_with_modulename():
    f = Exporter(modulename="foo").model(Foo).get("Foo")
    assert "import Foo" in f.generate_prompt()


def test_exports_has_modulename():
    from ghostiss.core.ghosts.thoughts import EXPORTS

    count = 0
    assert EXPORTS.module == "ghostiss.core.ghosts.thoughts"
    for i in EXPORTS.iterate():
        count += 1
        assert i.module() == "ghostiss.core.ghosts.thoughts"

    assert count > 0
