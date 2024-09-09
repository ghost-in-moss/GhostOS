# 发布计划要完成的事情

+ 功能完善
  + 命令行 console 完善, debug, 全异步运行通过
  + 单任务状态, 多任务调度通过
  + messenger 支持 <xml> 语法
  + 默认的 chat preparer 完善
  + MOSS Thought 基线
+ 基础类库
  + 集成 LlamaIndex
  + 消息协议支持图片
    + 支持阅读字符串图片, 返回图片类型消息
  + 领域 memory
    + thought 库文件的召回
    + moss 类文件的召回. 放在 moss 目录下?
  + Terminal ? 
  + PDF 阅读? (可以用来做 case)
  + tree-sitter 级别的阅读和重写?
  + 文件保存
+ 功能集成
  + 网络搜索
  + 网页浏览
  + 基础 memory
+ 文档建设 (初期)
  + quick start
  + moss 定义
  + 基本功能用法
+ 功能性 agent 开发
  + 项目介绍 Agent
  + 批量代码阅读, 中文转成英文注释
+ 文件清理
  + 删除 moss_p1
  + 删除 quests
  + 历史 exports 清理
  + 删除 runner 相关
  + 整理 scripts
  + demo 下 ghostos 相关文件清理
  + 清理 assets 目录
+ 目录与文件名管理
+ scripts
  + llm_tests
  + demo
  + aifunc_tests (不如文件级好用)
  + poetry 初始化项目仓库
+ 应用形态
  + 命令行执行的对话界面 console driver
  + 单元测试的 debug 工具
  + ghost function decorator 完善
  + 与 python 文件对话的 agent, 优先级最高, 很多类库需要它来优化
  + 基于 docs 文件生成的 agent
  + 目录级的 agent
  + 项目级的 agent.
  + 实现了 openai api 的 single agent. 目标是可以对接 OpenUI
  + 可以生成 moss 代码的 agent
  + 文件级的 aifunction
  + 文件级的可对话 moss agent, 专门用来单独运行. 活在目录里的 agent. 
  + 语音 shell + 截屏 + 说话 + 拍照?  mac 的 ai 化? 树莓派具身智能?
  + 树莓派的全代码 AI 智能体
  + 写单元测试, 并且能主动测试的 agent. 
  + 可以持续积累记忆的模块. 记忆最好用文件存. 
+ 演示案例
  + 自主生成 sphero driver 的代码
  + 批量阅读自己的所有文件, 并替换中文注释为英文注释
  + swe bench 测试
  + ghost func 实现大规模 mock?
  + 异步双工交互

# 时间规划? 

只有 7 个工作日时间. 考虑到最近生病, 进度还会有比较大的影响. 要对所有目标做一个优先级排序.
先排一个三天内的. 

1. 文件级的 agent, 使之可以独立对话. 后续各种功能都要依赖它. 
2. 规划任务, 对多个文件进行批量修改的 agent.
3. 能帮我封装工具的 agent. 接下来各种类库都要靠它封装. 
4. 能帮我写单元测试, debug 的 agent.
