def test_dict_items():
    a = {1: 2, 3: 4}
    for k, v in a.items():
        assert k == 1
        assert v == 2
        break
