import argparse
import sys
from ghostiss.core.moss import test_container, MossTestSuite, MossResult
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


def print_moss_result(name: str, result: MossResult):
    console.print(
        Panel(
            str(result.returns),
            title=f" case '{name}' returns",
        )
    )
    console.print(
        Panel(
            str(result.std_output),
            title=f" case '{name}' std_output",
        )
    )
    pycontext = result.pycontext.model_dump_json(indent=2, exclude_defaults=True)
    console.print(
        Panel(
            Markdown(f"```json\n{pycontext}\n```"),
            title=f" case '{name}' pycontext",
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="run ghostiss moss test cases, show results from moss defined test cases",
    )
    parser.add_argument(
        "--modulename", '-m',
        help="module name of the testing moss module",
        type=str,
        # 默认使用专门测试 MossTestSuite 的文件.
        default="ghostiss.core.moss.examples.test_suite",
    )
    parser.add_argument(
        "--test_modulename", '-t',
        help="temporary modulename that moss compiler will compile to. default is __test__",
        type=str,
        default="__test__",
    )
    parser.add_argument(
        "--cases", "-c",
        help="the pointed test cases that defined in moss module, split with `,`; "
             "if empty then find cases in module.__tests__",
        type=str,
        default=""
    )

    parsed = parser.parse_args(sys.argv[1:])
    container = test_container()
    cases = []
    if parsed.cases:
        cases = parsed.cases.split(',')
    test_modulename = parsed.test_modulename
    modulename = parsed.modulename

    # 初始化 suite.
    suite = MossTestSuite(container)

    prompt = suite.dump_prompt(modulename=modulename, test_modulename=test_modulename)

    console.print(Panel(
        Markdown(f"```python\n{prompt}\n```"),
        title=f"moss_prompt from {modulename} | test_modulename={test_modulename}",
    ))

    suite.run_module_tests(
        modulename=modulename,
        callback=print_moss_result,
        test_modulename=test_modulename,
        targets=cases,
    )


if __name__ == "__main__":
    main()
