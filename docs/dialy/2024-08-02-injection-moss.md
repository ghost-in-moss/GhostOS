# 计划实现 injection moss. 

这是之前的一个废案, 因为复杂度高了. 现在看起来有必要. 

简单来说: 

1. pycontext 可以指定一个 py 文件 (使用 module 的方式指定)
2. moss 会先读出这个 py 文件的源码, exec 它.
3. 然后 moss 会根据 pycontext 的其它内容, 动态拼装上下文. 
4. pycontext.imported 应该改名叫 pycontext.injections
5. pycontext 考虑可以添加代码, 但这个必须在添加时进行构建, 确保没有异常. 否则会永远失败. 
    - 理想情况下 pycontext 还是 import 为主, 让 meta-thought 去修改文件里的代码. 
6. Thought 往 MOSS 里添加的上下文变量, 依然会添加到这个临时的 module. 
7. 仍然用 reflect + Exporter 的方式, 去理解代码里变量 (主要是引入变量), 生成 prompt. 不过 prompt 主要以注释形式出现. 
8. 设计一个分隔符, 用来定义不对 LLM 展示的代码. 
9. 支持在文件里定义好初始化方法 (比如 `def __init__(moss: MOSS) -> None` ), 可以直接注入 MOSS, 运行初始化.  
10. 最终仍然要让 LLM 基于当前上下文写一个方法, 例如 `def main(moss: MOSS) -> Operator`

评估目标: 
1. 尽可能所见即所得: 当前这版 moss 最大的问题是所见非所得
2. 相对优雅的方式
3. 考虑安全性的问题
4. 增加一些 meta 方法用来理解当前 module 的上下文. 

关联性修改: 

1. moss_test 要改名 moss_runner_test
2. moss_runner_test 要能自动生成 moss_test, 就是把大模型写代码存成独立的文件, 可以独立测试优化. 
3. 要测试不用 functional token 的模式. 
4. 要设计一个配置参数, 直接将 Runner 变成全代码驱动的. 也就是 LLMs 只用代码做输出. 