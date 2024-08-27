from ghostos.core.llms import FunctionalToken
from ghostos.core.moss.abc import MossPrompter
from pydantic import BaseModel, Field

__all__ = ['MOSSArgument', 'DEFAULT_MOSS_FUNCTIONAL_TOKEN', 'DEFAULT_MOSS_PROMPT_TEMPLATE']


class MOSSArgument(BaseModel):
    code: str = Field(description="generated moss code that include `def main(os: MOSS) -> Operator`")


DEFAULT_MOSS_FUNCTIONAL_TOKEN = FunctionalToken(
    token=">moss:",
    name="moss",
    description="""
You can output the Python code that MOSS is supposed to run after this token. 
The system will automatically execute them. 
Notice:
- MOSS-related output is not visible to user.
- You are only able to generate MOSS code within this token.
- The content after this token shall be pure Python code only. 
- You can send anything directly before this token, not after it.
- **Never** use ``` to embrace your code.
- Need not to mention the code you generated to user.
""".strip(),
    deliver=False,
    parameters=MOSSArgument.model_json_schema(),
)

DEFAULT_MOSS_PROMPT_TEMPLATE = """
# MOSS 

You are equipped with the MOSS (Model-oriented Operating System) that provides tools and thought directions in python interface.
With MOSS you shall generate a single block of Python code in which defines a function `def main(os: MOSS) -> Operator:`, 
the MOSS will automatically execute them. 

**Directives for MOSS**:
- **Code Generation Only**: Produce a block of Python code for the `main` function. 
  The interface, class and abstract methods in context are ALREADY implemented in external system, 
  and passed into main as arguments, DON'T implement them or instantiate them again, 
  just invoke them directly on you need.
- **Format Requirement**: Your output must be a single block of Python code enclosed within triple backticks. 
  Do not include any additional text, comments, or explanations outside this code block. 
  Do not invoke main method by yourself.

**External System Responsibilities**:
- **Execution and Data Fetching**: The external system will concatenate your code with the true context 
  (implemented all abstract methods and interface), execution the main method and wait to fetch the result.
- **Result Handling**: The external system will process the results and manage user interactions. 
  Std output will be buffed by MOSS, you can generate operator to observe them.


Here is the context provided to you in this turn:

```python
{code}
```

**Notices**
0. You need not to use MOSS when you don't need it's api such as tell raw text or use other functional tokens.
1. MOSS is a private system only serve for you, **never mention it existence**.
2. MOSS code shall be generated within functional token, markdown python block will not do, and **don't repeat the code with markdown**.
3. MOSS will automatic execute the main function so you never execute it again.
4. **Return Operator**: You shall always use method that MOSS provide you to return an Operator from function main. 
5. In the generated MOSS code, ** YOU SHALL NOT WRITE ANYTHING BUT CODE AND COMMENTS BECAUSE MOSS CODE NEVER SEND TO USER**.
6. Your generated code must include `def main(os: MOSS) -> Operator` method which will be executed following your intention. 
"""


def get_default_moss_prompt(prompter: MossPrompter) -> str:
    code_prompt = prompter.dump_context_prompt()
    return DEFAULT_MOSS_PROMPT_TEMPLATE.format(code=code_prompt)
