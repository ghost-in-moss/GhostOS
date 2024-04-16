# what should agent see

An agent should see messages below:

+ system prompt
  - moos interfaces: show llm how to use moos
  - prompt properties: properties will be used to generate prompt. property name is title, value is prompt content.
  - tools: methods that available
+ chat history
+ system context
  - task information
  - memories
+ user input
+ instructions
  - thought


# moos interface

moos interface 总是要占据若干个 tokens. 关于它要设计使之变得最小. 如果这套机制可以 work, 未来可以想象有模型将 moos interface 内置.
这样模型不再需要 prompt 也能够正确使用 moos interface. 

moos interface 应该要包含的: 

* 输出关键字: 通过关键字来控制流式输出, 可以输出不同类型的控制流. 自动被加工为处理逻辑. 
* 基础操作方法. 

# 关键问题

moos 的操作理想情况下, 能够支持自然语言函数. 自然语言函数期望所有的参数都是自然语言. 
然后通过一个 task 将它变成正常的函数调用. 
所以我需要发明一个自然语言函数. 并且保证它可以使用 python 或其它语言的 runtime. 

## 函数简介

可能是这样的效果: 
```markdown
- 询问天气(城市, 日期|nil): 可以用来询问天气
+ moos: 操作系统
  + lib: 代码仓库
    - import(函数路径): 引入一个仓库
```

这样可以生成一个庞大的函数调用树, 而且不用占用太多的 tokens.

调用的时候, llm 输出流式消息: 
```markdown
:run>
moos.lib.import("foo.bar")
```

然后系统就能够正确地执行这些函数. 执行前可以调用一个小模型来做代码的生成. 当然初期可以用大模型.
- 用领域模型的好处是可以提速.
- 自然语言函数输出的内容放到 function 类型消息里. 或者 system 类型消息里. 


