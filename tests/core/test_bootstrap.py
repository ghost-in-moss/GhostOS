from ghostos.bootstrap import expect_workspace_dir


def test_expect_app_dir():
    dirname, ok = expect_workspace_dir()
    assert dirname.endswith('.ghostos')
    assert isinstance(ok, bool)
