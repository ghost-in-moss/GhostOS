from ghostos.abcd import MossAction


def test_moss_action_unmarshal_code():
    bad_case = """```python
def run(moss: Moss):
    test_entities()
    moss.pprint("test_entities 运行完成!")
```"""

    value = MossAction.unmarshal_code(bad_case)
    assert not value.startswith("```")
