# MOSS test suites

准备为 moss 驱动的 agents 建立一系列的测试用例. 这些测试用例不是应用级的, 主要验证和优化 MOSS 的基础 prompt.

基本分类:

- 工具调用: 对齐各种常规 agent 的基线能力.
- 基础类库: 一些场景不强相关的功能性类库, 比如搜索模块等.
- 当前任务管理: 使用 mindflow 控制当前任务的行为.
- 多任务调度: 基于 thought 和 multi-tasks 创建自任务, 并测试各种通讯.
- 规划能力: 使用拥有规划能力的 Thought 驱动其它 Thought 运行规划.
- Multi-agent: 将 thoughts 包装成 agent, 可以开启独立进程, 实现 agent 之间通讯.
- 变量类型消息: 让 llms 感知变量类型的消息. 验证可以基于 moss 提供的 lib, 去操作变量类型的消息.
- meta-thought: 用来构建一个 thought 的 meta thought. 二阶即无穷阶.
- 自我修改: 允许修改当前 thought 自身的配置.
- 任务型 thought: thought 的上下文根据 task 描述构建, 有非常具体的领域描述. 同时提供相关能力.
- SWE-bench: 与 SWE-bench 相关的测试用例.
- 具身智能: 具身智能体的测试用例. 用写代码的方式驱动自身的行为.
- 可学习 Thought: 拥有可以持续学习的 library, 学习成功作用于后续行为. 
- 异步逻辑: 异步多任务场景下, 会在一个 thread 中出现乱续插入. 验证模型对乱续插入的响应能力. 

以上功能测试都是为了未来的应用构想做准备. 这些测试点并不代表未来应用落地场景的形态, 只是用来论证 MOSS 对应用的价值. 

## 工具调用

工具调用场景对齐现在基于 function call 实现的各种 agent.
设想基线测试需要 mock 一系列的 libraries:

1. 音乐播放
2. 新闻搜索相关
3. 文本阅读, 比如 pdf 阅读.
4. 搜索商品, 购物
5. 地理搜索 POI
6. 搜索工具.

基于这些 libraries 的测试用例:

1. 根据用户意图, 调用一个工具.
2. 对工具 a 的结果做加工, 调用工具 b.
3. 有多轮上下文, 多次调用工具.
4. 搜索工具
5. 根据搜索工具的结果, 立刻调用工具.

## 基础类库

提供一些基础类库, 验证 llms 会根据 moss 提供的这些基础类库, 完成特定的需求.

- modules 搜索:  可以根据需求来搜索类库, 选择类库.
- pypi (github, poetry) 搜索: 可以搜索 pypi, 并且根据搜索结果运行安装命令.
- git: 可以运行 git 的基本指令, 并且返回结果.
- terminal: 可以在指定的 workspace 里运行 bash 命令行.
- doc memory: 让 llms 自己定义 BaseModel 然后生成文档数据库, 然后自己用 base model 创建记忆, 用索引字段召回记忆. 
- rag memory: 让 llms 定义自然语言的记忆, 生成自然语言的 index, 使用 embedding 存储和支持召回. 

## 当前任务管理

Thought 运行在一个 Task 内部, 需要通过一系列指令来操作 task 自身的状态变更 (预计叫 taskmanager 或 mindflow) . 测试用例:

1. functional tokens / MOSS API / Tools 是三种可选的驱动方式. 优先前二者.
2. Awaits: llms 向上一层 or 用户提问, 等待回答.
3. fail: 提供异常信息后, 调用 api 描述任务失败. 也希望 llms 在一个 moss 代码里写 try except 主动调用 fail .
4. finish: 如果当前任务运行多轮后, 信息已经完备, 验证 llms 调用 finish 完成这个任务并记录发送结果.
5. observe: 测试用 moss 运行代码后, 主动观察结果.
6. 测试在 canceled, fail, finish 等动作之后, 仍然收到新的事件并运行.

也要验证使用 functional tokens 快速实现上述操作.
未来的 Host Thought 预计用 functional token 来快速应答. 因此也要实现 7:

- llms 调用某个 token, 快速回复用户, 实际上会 fork 当前会话然后运行一个有 moss 的流程. 

## 多任务调度

Thought 可以使用 multi-tasks (或别的名字) 来管理自己的子任务. 子任务通过一个 Thought 实例来创建, 所以 MOSS 要提供:
1. 不同的 Thought 类, llms 生成参数去实例化. 
2. Thought 实例, llms 只要看到它们的 identifier, 用变量名就可以操作. 

子 tasks 在 prompt 里可以用  `name: description` 的方式呈现. 

预计要测试的用例: 
- fork: 当前 task fork 自身创建子 task. 
- 取消: 根据用户需求, 父 task 主动取消一个子 task
- 追问: 根据用户需求, 父 task 向一个子 task 进行追问. 
- 创建: 根据用户需求, 父 task 使用多个 thought (类/实例) 创建子任务. 
- finish_callback: 根据子 task 返回的结果驱动下一步. 
- wait_callback: 得到子 task 的问题后, 要主动补充讯息给子 task, 或者先向上一层提问, 然后通知子 task. 
- failed_callback: 子任务失败后的回调. 

## 规划能力

在多任务调度的基础上, 预计有一些规划类 Thought, 本身可以接受别的 Thought 实例作为参数, 用来构建规划. 想要测试的规划能力:
既要测试 multi-tasks 的调度, 也要测试 child task 的执行. 

- 分支图 Thought: 定义若干步骤, 每个步骤都有可能的子步骤. 通过 next_step 来定向. 
- DAG Thoughts: 定义多个 thoughts 构成的邻接表, 系统进行拓扑排序后, 自动在每一层创建并发多任务运行. 然后在反思节点反思, 继续或中断.
- 迭代 Thought: 这个 thought 会有个默认的迭代方法, 每一轮运行完, llms 需要反思是 continue 还是 break. 没有决策.
- 决策树 Thought: 这个 thought 会定义出 N 个子 thoughts, 根据输入决策出可能的执行 thought, 交给这个 thought 代替自己执行. 

## multi-agent

和 multi-tasks 基本一样, 区别是用 Agent(Thought) 来创建任务. 这个 agent 可以有独立的人格, 独立的上下文, 运行时使用独立的 process.
其它原理基本都一样. 人格与记忆隔离是 multi-agent 区别于 thought 的本质. 
测试用例的思路也差不多. 同样规划能力应该要能作用于 multi-agent. 


## 变量类型消息

需要对一些消息做变量化改造, 让 llms 能意识到这是某种变量, 可以通过 MOSS 提供的 API 对变量进行处理加工. 
所以每个变量类消息, 都要有对应的 library 来操作它. 
需要测试的变量类型: 

- images: 图片类. 对于多模态大模型而言, 图片需要被处理成二进制或上传文件. 同时 llm 还要能感知它作为一个变量. 
- big text: 大文本. 
- file: 各种类型的文件. 
- direction: 对 shell 发送的指令. llms 要能感知到指令的类型和数据结构. 可能通过 tool 对端上发送的. 比如播放音乐. 

变量类型消息的难点在于 prompt. 对端展示的 content 显然和 llms 感知的 memory 不一样.

## meta-thought

一个可以多轮对话, 多轮思考, 用来构建指定 thought 的 meta-thought. 主要验证 moss 提供了 meta 的能力. 
一个典型的例子是创建 tool-thought: 

- 生成 thought 的 name 和 description
- 选择 thought 的模型
- 搜索 thought 使用的 module, 并且提供给它. 
- 定义 thought 的 prompt

多轮运行时不断修改一个数据结构, 最终将它保存.
显然 meta-thought 要使用一些拥有 meta 能力的类库: 
- llm-api: 看到各种 llm-api
- modules: 搜索和引用各种类库. 

最理想的 meta thought, 是看到任何一个 EntityClass 类型的 Thought, 都可以对它进行加工. 
初期可能要建立一系列的 meta-thought: 

- tools-thought-meta: 编辑一个使用工具的 thought.
- method-thought-meta: 可以自己在 workspace 里写属于这个 ghost 的 method.
- library-thought-meta: 可以自己在 workspace 里创建 library.

更 meta 的 thought 是直接阅读一个 thought 的源码, 然后自己也能够写源码. 一步步来. 


## 自我修改

一种实验性的想法. 提供 library, 让 thought 可以阅读和修改自己. 
有几种级别: 

1. 修改自己的配置: 修改 prompt, pycontext 等. 
2. 修改自己的实现: 阅读自己的源码, 然后 fork 一个 thought 类, 修改源码的逻辑. 

另一种做法不是提供 library, 而是提供一个 child thought, 开启一个 meta-thought 的任务来修改自身. 
这样可以用于 on_finish 事件, 驱动 thought 在完成任务后持续自我优化. 要做的实验非常多. 

## 任务型 Thought

Thought 会运行在一个 Task 内, 要根据任务来生成 system prompt, 作为任务运行的第一驱动.
需要创建一系列的基线 Thought 用来验证. 初期测试的方向可以集中于 coding 和 swe-bench 的需求. 

- http api 封装: 给定一个 http 接口, 让 llm 自己封装一个它可以调用的 tool. 
- 领域代码编写: 给定 dal, logic 层范式, 让 llm 维护和编写相关代码. 比如假设目标项目是 django.
- 源码优化: 立足于某个 module, 可以修改和优化源码. 比如翻译注释. 
- 代码理解: 理解一个 module, 为它生成 description 和 reflect.exporter 用于召回. 
- 单元测试: 围绕单元测试, 可以执行它们, 或者定位问题. 
- 文档编写: 让 llms 为一个文档生成元信息, 元信息存在 yaml 里. 根据多轮对话, llm 可以修改 yaml 里的元信息, 然后根据元信息循环修改整个文档.

## SWE-bench

设计 swe-bench 问题的解题流程, 然后测试解题流程里的关键帧. 
当前理解, 就是对上述其它测试用例的场景化运用, 需要有更明确的 swe 场景. 具体测试用例有待调研结果. 


## 具身智能

shell 通过 driver 抽象提供自己可以调用的各种命令. llm 调用这些命令后, 与 shell 进行通讯, 操作 shell 运行. 
预计 driver 提供的 api 并不是 atomic 的, 会有其它算法和模型在其中 (比如寻路). 

llms 生成的代码会在一个 thread 里持续运行, 底层需要有时间感. 举个例子: 

```python
def main(os: "MOSS") -> "Operator":
    # 画一个三角形. 
    os.sphero.move(angle=0, speed=90, duration=1)
    os.sphero.move(angle=0, speed=180, duration=1)
    os.sphero.move(angle=0, speed=270, duration=1)
    return os.observe()
```

一个高级测试目标, 让 LLM 阅读 shell api 后, 自己封装出可以驱动它的指令. 
如果这个做好了, 满足某类协议的设备, 几乎全部都可以通过 LLM 自行封装出 driver 并驱动. 那就太牛了. 

## 可学习 Thought

可学习的 Thought 指它拥有两个东西: 

- memory lib: 一个类库, 可以操作相关记忆. 
- memory runner: 这个 runner 会自动调用 memory 的讯息来补充上下文, 为 thought 运行提供提示. 

典型的例子, 是根据 input 自动 RAG 召回 examples 或者 cot. 但 Thought 可以主动调用方法存储 example 或 cot. 
llms 生成的 moss 代码可能是:

```python
def main(os: "MOSS") -> "Operator":
    os.examples.memorize()  # 系统自动把上一轮对话 user => output 存储到 rag 记忆里. 
    return os.awaits("回复用户的内容")
```

## 异步逻辑

在基于 event 的全异步驱动框架下, task 运行时虽然是串行的, 但输入和回复之间却不一定是连贯的, 可能会有各种乱序.
乱序可以通过类似 tool id 的做法, 在上下文中标记关联关系, 期待 llms 能正确理解异步回调. 
也需要做一些基线测试, 方便构建异步回调的 prompt. 