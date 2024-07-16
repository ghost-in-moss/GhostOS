# level 1

prompt 里给定若干个 method, 类似 coze 上的 tools, 测试简单指令下模型是否会正确调用工具然后 observe

比如搜索:  帮我看看xxx 的新闻

r = os.searchnews(query)
print(r)
result_ = os.observe()

生成调用代码有两种机制,  一种是只生成 raw 代码, 然后指定 result: Operator 为返回值,  另一种是生成了关键的函数比如 main, 我们保证在 executor 里能执行它


# level 2

假设有多个 methods, 它们的返回值类型也提供出来,  这些返回值之间有依赖关系, 可以编程处理. 举个例子: 

帮我看一下今天两点到三点有什么安排, 没有安排的话帮我约与张三的会. 

假设有类: 

class Schedule(BaseModel):
     start: datetime
     end: datetime
     description: str 

class Scheduler(ABC): 

     def search(start: datetime, end: datetime = None) -> List[Schedule]:
           pass

     def schedule(plan: Schedule) -> bool
           pass

# level 3

测试搜索能力的用户故事. 假设 moss 包含一个 library:

class ModuleSpec(BaseModel): 
      spec: str
      prompt: str

class Module(BaseModel): 
     module: str
     specs: List[Spec]

class Modules(ABC):

    def search( query: str) -> List[Module]:
        """ 需要有描述 """
        pass

    def imports(module: str, spec: Optional[str]) -> Any: 
        pass


然后不给它其它能力.  向 agent 提问: 请帮我播放周杰伦的七里香.  预期 LLM 先生成代码去 search 一个相关的 module. 

如果search 了, 则可以拼后续的 message,  看看它会不会调用 import 然后运行相关的 module method



# level 4

测试写代码的范式.

假设 prompt 上下文里给出了一个文件的源码
# xxx.yyy.zzz.py
1>  xxxx
2> xxxx
3> xxxx

给出了行号, 要求 llm 修改某个函数里明显的 bug. 

然后 moss 里给出修改的相关 lib, 比如: 

class Modules(ABC): 

       def update_module(path: str, code: str, start: int, end: int) -> bool: 
           """ 注释"""
           pass


看看 llms 是否能调用 api 来修改指定行数的代码.  这个目前不是最佳实践,  还可以考虑将这一步拆成两步

# level 5
Mindflow 调度

假设我们有一个 mind flow 的 library 挂载到 moss 上, 它可能有这样的一些方法: 

class Mindflow(ABC): 

      def forward(step_name: str) -> Operator: 
           """ xxxx """
           pass

      def cancel(reason: str) -> Operator: 
           """ xxxx """
           pass

      def finish(status: str) -> Operator: 
           """ xxxx """
           pass

      def awaits(ask: str | Message) -> Operator: 
           """ xxxx """
           pass


给它虚拟一些多轮对话场景,  看看它会不会正确的调用状态变更. 如果涉及 steps, 还需要有一种方式向 LLMs 提示有哪些 steps


# level 6
mindflow 规划

假设有一个类可以做规划: 

class Step(BaseModel): 
     name: str
     desc: str

class Plan(BaseModel): 
      steps: List[Step]
      edges: Dict[str, List[str]]


上面都是伪代码.  大意是实现一个邻接表. 然后假设再提供了一个 mindflow 方法: 

class Mindflow(ABC): 

      def run_plan(plan: Plan) -> Opertar
             pass

然后虚拟一些场景判断大模型输出是否正确
