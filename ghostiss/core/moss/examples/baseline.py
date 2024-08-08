from ghostiss.core.moss.abc import MOSS


# baseline test case for moss

def plus(a: int, b: int) -> int:
    return a + b


# <moss>
# 使用 `# <moss>` 和 `# </moss>` 包裹的代码不会对大模型呈现.

if __name__ == '__test__':
    """
    用这种方式定义的代码可以直接用来做单元测试. 
    """
    def main(moss: MOSS) -> int:
        """
        模拟一个 main 方法, 测试 moss 的调用.
        assert 返回值是 3. 外部的 MOSSRuntime 调用这个方法.
        详见 tests.core.moss.examples.test_baseline
        """
        return plus(1, 2)

# </moss>
