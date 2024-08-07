def test_func_set_attr():
    setattr(test_func_set_attr, "__test__", "test")
    assert test_func_set_attr.__test__ == "test"
