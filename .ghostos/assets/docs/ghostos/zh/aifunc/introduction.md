
AI Func 将大语言模型的能力整合到 python 代码中, 将一个继承自 `pydantic.BaseModel` 的类可以作为函数使用, 
运行时大模型将看到代码所处的上下文, 在理解代码的基础上, 自行进行多轮思考, 并写出执行代码.
`AI Func` 可以相互嵌套. 