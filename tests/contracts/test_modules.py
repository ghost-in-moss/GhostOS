from ghostos.contracts.modules import DefaultModules


def test_default_modules_iter():
    m = DefaultModules()
    from ghostos import contracts
    result = list(m.iter_modules(contracts))

    assert "ghostos.contracts" not in result
    result2 = list(m.iter_modules("ghostos.contracts"))
    assert result == result2
