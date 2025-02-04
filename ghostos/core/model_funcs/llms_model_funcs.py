from typing import List
from ghostos.core.model_funcs.abcd import LLMModelFunc
from pydantic import BaseModel, Field

__all__ = ["TextCompletion", "FileReader"]


class TextCompletion(LLMModelFunc[str]):
    """
    a very simple example of how to define a LLMModelFunc
    """

    text: str = Field(description="the text completion instruction.")

    def run(self) -> str:
        messages = [{"role": "user", "content": self.text}]
        return self._generate(messages)


class FileReader(LLMModelFunc[str]):
    filename: str = Field(description="the absolute file name.")
    # llm_api =
    question: str = Field(description="the question to answer about this file.")
    max_content: int = Field(
        default=50000,
        description="the max content of the file.",
    )
    allow_ext: List[str] = Field(
        default_factory=lambda: ['.py', '.md', '.txt', '.yaml', '.toml', '.yml'],
        description="allowed file extension"
    )
    instruction: str = Field(
        default="""
You task is to read a file content and answer the user's question.

the content of file `{filename}` are below: 

```<article name=`{filename}`>
{content}
```</article name=`{filename}`>
""",
        description="the instruction template for the llm",
    )

    def run(self) -> str:
        from os.path import abspath, exists
        filename = abspath(self.filename)
        if not exists(filename):
            raise FileNotFoundError(f"File {self.filename} does not exist.")
        if not self.question:
            raise AssertionError("question cannot be empty.")

        allowed = False
        for ext in self.allow_ext:
            if filename.endswith(ext):
                allowed = True
                break
        if not allowed:
            raise FileNotFoundError(f"file {self.filename} has invalid types, only allowed {self.allow_ext}.")

        with open(filename, "r") as f:
            content = f.read()
            if len(content) > self.max_content:
                raise ValueError(f"File {self.filename} is too long. max content is {self.max_content}.")

        instruction = self.instruction.format(
            filename=filename,
            content=content,
        )
        return self._generate([
            {"content": instruction, "role": "system"},
            {"content": self.question, "role": "user"},
        ])


class GenerateLLMModelFunc(LLMModelFunc[str]):
    quest: str = Field(description="")

    def run(self) -> str:
        with open(__file__, 'r') as f:
            source_code = f.read()

        # instruction is required to the model.
        instruction = f"""
Your request is to define a `LLMModelFunc` class that user want. 

The coding context about `LLMModelFunc` is:
```python
{source_code}
```
"""
        messages = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": self.quest},
        ]
        result = self._generate(messages)
        parts = result.rsplit("```python", 1)
        result = parts[0] if len(parts) == 1 else parts[1]
        return result.strip("```python").strip("```").strip()
