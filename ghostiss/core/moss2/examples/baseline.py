from ghostiss.core.moss2.abc import MOSS


# baseline test case for moss

def plus(a: int, b: int) -> int:
    return a + b


# <moss>

if __name__ == '__test__':
    def main(moss: MOSS) -> int:
        return plus(1, 2)

# </moss>
