import sys
import argparse
import os
import yaml
from ghostos.container import Container
from ghostos.core.llms import LLMs
from ghostos.contracts.storage import Storage
from ghostos.framework.configs import ConfigsByStorageProvider
from ghostos.framework.llms import ConfigBasedLLMsProvider
from ghostos.framework.storage import FileStorageProvider
from ghostos.framework.llms.test_case import ChatCompletionTestCase, run_test_cases, ChatCompletionTestResult
from ghostos.helpers import yaml_pretty_dump
from rich.console import Console
from rich.panel import Panel
from rich.json import JSON
from rich.markdown import Markdown
from os.path import dirname, abspath

demo_dir = dirname(dirname(abspath(__file__)))


def _prepare_container() -> Container:
    container = Container()
    container.register(FileStorageProvider(demo_dir))
    container.register(ConfigsByStorageProvider("configs"))
    container.register(ConfigBasedLLMsProvider("llms_conf.yml"))
    return container


def main() -> None:
    parser = argparse.ArgumentParser(
        description="run ghostos llm test cases which located at demo/tests/llm_tests",
    )
    parser.add_argument(
        "--case", "-c",
        help="file name of the case without .yaml suffix",
        type=str,
        default="hello_world"
    )
    parser.add_argument(
        "--save", "-s",
        help="save the test results to the case",
        action="store_true",
        default=False,
    )

    parsed = parser.parse_args(sys.argv[1:])
    container = _prepare_container()
    storage = container.force_fetch(Storage)
    prefix = "tests/llm_tests/"
    file_name = os.path.join(prefix, parsed.case + ".yaml")
    content = storage.get(file_name)
    if content is None:
        raise FileNotFoundError(f"file {file_name} not found")

    data = yaml.safe_load(content)
    test_case = ChatCompletionTestCase(**data)
    llms = container.force_fetch(LLMs)

    output = run_test_cases(test_case, llms)
    test_result = ChatCompletionTestResult()
    test_result.results = output

    console = Console()
    for name, message in output.items():
        body = JSON(message.model_dump_json(indent=2, exclude_defaults=True))
        panel = Panel(body, title=name)
        panel2 = Panel(Markdown(message.get_content()))
        console.print(panel)
        console.print(panel2)

    if parsed.save:
        test_case.results.insert(0, test_result)
        data = yaml_pretty_dump(test_case.model_dump(exclude_defaults=True))
        storage.put(file_name, data.encode("utf-8"))
        console.print("save the test results to the case")


if __name__ == "__main__":
    main()
