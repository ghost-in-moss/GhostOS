from typing import List, Dict, Optional, Callable
from ghostos_moss.abcd import MossCompiler, Execution
from ghostos_moss.pycontext import PyContext
from ghostos_container import Container
from queue import Queue
from threading import Thread


class MossTestSuite:
    MAGIC_TEST_CASES_ATTR_NAME = "__moss_test_cases__"

    def __init__(self, container: Container):
        self._container = container

    def container(self) -> Container:
        return self._container

    def dump_prompt(
            self,
            *,
            modulename: str,
            test_modulename: str = "__test__",
    ) -> str:
        compiler = self._container.force_fetch(MossCompiler)
        compiler.join_context(PyContext(module=modulename))
        runtime = compiler.compile(test_modulename)
        return runtime.prompter().dump_module_prompt()

    def run_module_tests(
            self, *,
            modulename: str,
            callback: Callable[[str, Execution], None],
            test_modulename: str = "__test__",
            targets: Optional[str] = None,
    ) -> None:
        """
        run the test cases in moss module, and returns each case's result to callback function.
        :param callback: callback on (test_case_name, MossResult)
        :param modulename: the target moss module
        :param test_modulename: the modulename that MossCompiler shall build.
        :param targets: the target functions that should be tested,
                        if None, test the func names from `__moss_test_cases__`
        :return:
        """
        compiler = self._container.force_fetch(MossCompiler)
        compiler.join_context(PyContext(module=modulename))
        runtime = compiler.compile(test_modulename)
        compiled = runtime.module()
        if not targets:
            targets: List[str] = compiled.__dict__.get(self.MAGIC_TEST_CASES_ATTR_NAME)
            if not isinstance(targets, List):
                raise AttributeError(f"Module {modulename} has no {self.MAGIC_TEST_CASES_ATTR_NAME} attribute")
        if not targets:
            raise AttributeError(f"test cases are empty")
        self.parallel_run_moss_func(
            modulename=modulename,
            callback=callback,
            test_module_name=test_modulename,
            funcs=targets,
        )

    def run(
            self, *,
            modulename: str,
            test_module_name: str = "__test__",
            target: str = "test_main",
            args: Optional[List[str]] = None,
            kwargs: Dict[str, str] = None,
    ) -> Execution:
        """
        运行一个指定的 moss 测试.
        :param modulename: 想要测试的 moss 文件的模块路径.
        :param test_module_name: 运行时创建的临时 module 名.
        :param target: 想要调用 moss 文件中的某个方法.
        :param args: 给 target 方法传递的 args 参数. 会从 module.__dict__ 查找真值.
        :param kwargs: 给 target 方法传递的 kwargs. 会从 module.__dict__ 查找真值.
        :return: Moss 执行后的 result.
        """
        compiler = self._container.force_fetch(MossCompiler)
        compiler.join_context(PyContext(module=modulename))
        runtime = compiler.compile(test_module_name)
        result = runtime.execute(target=target, local_args=args, local_kwargs=kwargs)
        return result

    def parallel_run_moss_func(
            self, *,
            modulename: str,
            funcs: List[str],
            callback: Callable[[str, Execution], None],
            test_module_name: str = "__test__",
    ) -> None:
        """
        并发地运行多个测试方法, FIFO 返回结果.
        :param callback: callback on (str, MossResult)
        :param modulename: 目标 module 的名字.
        :param funcs: 需要运行的 funcs.
        :param test_module_name: 测试时创建的临时 module_name.
        :return: 从队列中逐个取出.
        """
        queue = Queue()

        def runner(fn: str, q: Queue) -> None:
            """
            测试用 queue 来阻塞返回结果.
            :param fn: 要测试的方法名.
            :param q: 队列
            :param c: condition
            :param
            """
            r = self.run(
                modulename=modulename,
                test_module_name=test_module_name,
                target=fn,
                args=['moss'],
            )
            q.put((fn, r))

        threads = []
        for func in funcs:
            t = Thread(target=runner, args=(func, queue))
            t.start()
            threads.append(t)

        i = 0
        while i < len(threads):
            result = queue.get(block=True)  # 获取数据
            name, moss_result = result
            callback(name, moss_result)
            i += 1

        queue.task_done()
        for t in threads:
            t.join()
