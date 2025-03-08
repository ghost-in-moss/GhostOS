__all__ = ['A', 'foo']
A = dict[int, str]


def foo(a: A) -> list[str]:
    return list(a.values())


# test A is reflect-able

if __name__ == '__main__':
    from ghostos_moss.prompts import reflect_code_prompt
    from ghostos_moss.utils import is_typing

    assert is_typing(A) is True
    reflection = reflect_code_prompt(A, throw=True)
    assert reflection == "dict[int, str]", reflection
