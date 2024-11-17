from ghostos.helpers import Timeleft


def test_timeleft_with_zero():
    left = Timeleft(0)
    assert left.alive()
    assert left.alive()
