import sys
import argparse
import os
import yaml
from ghostiss.container import Container
from ghostiss.core.runtime.llms import LLMs
from ghostiss.contracts.storage import Storage, FileStorageProvider
from ghostiss.contracts.configs import ConfigsByStorageProvider
from ghostiss.framework.llms import ConfigBasedLLMsProvider
from ghostiss.framework.llms.test_case import ChatCompletionTestCase, run_test_cases
from rich.console import Console
from rich.panel import Panel
from rich.json import JSON
from rich.markdown import Markdown


def _prepare_container() -> Container:
    container = Container()
    ghostiss_dir = os.path.abspath(os.path.dirname(__file__) + "/../../demo/ghostiss")
    container.register(FileStorageProvider(ghostiss_dir))
    container.register(ConfigsByStorageProvider("configs"))
    container.register(ConfigBasedLLMsProvider("llms/llms_conf.yaml"))
    return container


def main() -> None:
    parser = argparse.ArgumentParser(
        description="run ghostiss llm test cases which located at demo/ghostiss/tests/llm_tests",
    )
    parser.add_argument(
        "--case", "-c",
        help="file name of the case without .yaml suffix",
        type=str,
        default="hello_world"
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
    console = Console()
    for name, message in output.items():
        body = JSON(message.model_dump_json(indent=2, exclude_defaults=True))
        panel = Panel(body, title=name)
        panel2 = Panel(Markdown(message.get_content()))
        console.print(panel)
        console.print(panel2)


if __name__ == "__main__":
    main()
