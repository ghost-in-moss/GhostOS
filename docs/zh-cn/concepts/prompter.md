# Prompter

向大模型提供 Prompt 的工作必然走向结构化和模块化. 传统的模板语言无法承载 Prompt Engineering 的复杂性. 

作者认为 Prompt Engineering 应该使用类似前端界面的 `DOM` (Document Object Model) 来构建, 
可能叫做 `POM` (Prompt Object Model). 

对 LLM 生成的 System Prompt 本质上是一个 `POM Tree`, 它可以将上下文相关的各种数据对象组装成 Prompt. 

`POM` 的一些可预见的好处: 

1. 节点可以用数据结构来封装, 方便被其它项目复用. 
2. 可以将复杂的 UI 界面映射成 `POM Tree`, 为 LLM 自动提供视觉对象的额外讯息. 
3. `POM Tree` 可以做前端渲染, 方便人类管理足够复杂的上下文, 甚至可视化渲染.  
4. `POM Tree` 可以编程, 所以可以由 Meta-Agent 自主生成. 
5. 可以针对 `POM Tree` 进行 tokens 的优先级裁剪. 

这个技术实现不是 `GhostOS` 自身的目标, 但由于开源社区还没提供成熟的 `Prompt Object Model` 实现, 因此作者先实现了一个简单版.

详见: [ghostos.prompter](https://github.com/ghost-in-moss/GhostOS/ghostos/prompter.py)


以 [MossAgent](../usages/moss_agent.md) 为例, 它默认的 Prompter 是如下结构: 

```python
    def _get_instruction_prompter(self, session: Session, runtime: MossRuntime) -> Prompter:
        agent = self.ghost
        return TextPrmt().with_children(
            # system meta prompt
            TextPrmt(
                title="Meta Instruction",
                content=AGENT_META_INTRODUCTION,
            ).with_children(
                TextPrmt(title="GhostOS", content=GHOSTOS_INTRODUCTION),
                TextPrmt(title="MOSS", content=MOSS_INTRODUCTION),
                # code context
                get_moss_context_prompter("Code Context", runtime),
            ),
            
            # agent prompt
            TextPrmt(
                title="Agent Info",
                content="The Agent info about who you are and what you are doing: ",
            ).with_children(
                get_agent_identity("Identity", agent.__identifier__()),
                TextPrmt(title="Persona", content=self._get_agent_persona(session, runtime)),
                TextPrmt(title="Instruction", content=self._get_agent_instruction(session, runtime)),
            ),
            
            # context prompt
            TextPrmt(
                title="Context",
                content="",
            ).with_children(
                self._get_context_prompter(session),
            )
        )
```