from ghostos.prototypes.ghostfunc import ghost_func


@ghost_func.decorator()
def plus(a: int, b: int) -> int:
    """
    :return: a + b
    """
    pass


if __name__ == "__main__":
    print(plus(1, 2))
