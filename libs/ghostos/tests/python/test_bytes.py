from io import BytesIO


def test_bytes():
    b = BytesIO()
    b.write(b'hello')
    got = b.getvalue()
    assert len(got) == 5
