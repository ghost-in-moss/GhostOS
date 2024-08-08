from ghostiss.core.moss.abc import MOSS

# <moss>
"""
使用独立行 `# <moss>\n` 开头, 直到结尾或者独立行 `# </moss>` 的代码, 
在生成 prompt 时默认对 LLM 不可见, 但仍然会执行. 

所以以下代码不会在 moss 的 context prompt 里, 对 LLM 不可见. 

在这个区块里, 可以定义和 MOSS 运行生命周期有关的代码. LLM 感知不到它们, 但也会生效. 

具体类型可以查看: 
from ghostiss.moss.lifecycle import __moss_prompt__, __moss_exec__, __moss_compile__

注意, 每个生命周期的函数都是可选的. 
"""

# </moss>
