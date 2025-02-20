from ghostos_moss.abcd import Moss


def plus(a: int, b: int) -> int:
    return a + b


# <moss-hide>
if __name__ == '__test__':
    """
    可以这样定义只在当前文件编译成 modulename=__test__ 才运行的方法. 
    """


    def test_1(moss: Moss) -> int:
        return plus(0, 1)


    def test_2(moss: Moss) -> int:
        return plus(1, 1)


    def test_3(moss: Moss) -> int:
        return plus(1, 2)


    __moss_test_cases__ = ['test_1', 'test_2', 'test_3']
    """用这个魔术变量, 可以让 MossTestSuit 批量调用三个方法测试. """

# </moss-hide>
