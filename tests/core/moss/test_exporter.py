from ghostiss.core.moss.exports import Exporter


class Foo:
    bar: int


def test_exports_has_modulename():
    from ghostiss.core.ghosts.thoughts import EXPORTS

    count = 0
    assert EXPORTS.import_from == "ghostiss.core.ghosts.thoughts"
    for i in EXPORTS.iterate():
        count += 1
        assert i.import_from() == "ghostiss.core.ghosts.thoughts"

    assert count > 0
