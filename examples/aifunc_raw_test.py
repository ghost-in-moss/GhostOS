import sys
from os.path import dirname
from ghostos.core.aifunc import AIFuncExecutor

# I hate python imports
ghostos_project_dir = dirname(dirname(__file__))
sys.path.append(ghostos_project_dir)

"""
Raw test of AIFuncExecutor and Frame
Print out almost every thing. 
"""

if __name__ == '__main__':
    from ghostos.bootstrap import application_container
    from ghostos.demo.aifuncs.agentic import AgentFn
    from ghostos.framework.streams import new_connection
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    import json

    console = Console()
    from threading import Thread

    debug = False

    executor = application_container.force_fetch(AIFuncExecutor)
    fn = AgentFn(
        request="help me to find news about OpenAI O1 model",
    )
    stream, receiver = new_connection(-1, accept_chunks=False)
    frame, caller = executor.new_exec_frame(fn, stream)
    t = Thread(target=caller)
    t.start()

    with receiver as items:
        for item in items:
            tail = item.done()
            payloads = json.dumps(tail.payloads, indent=2, ensure_ascii=False)

            payloads_info = ""
            if debug:
                payloads_info = f"""
            
```json
{payloads}
```
"""
            console.print(Panel(
                Markdown(
                    tail.get_content() + payloads_info
                ),
                title=tail.name,
            ))
    if debug:
        console.print(Panel(
            Markdown(
                f"""
    ```json
    {frame.model_dump_json(indent=2)}
    ```
    """
            ),
            title="frame details",
        ))
    result = frame.get_result()
    if result is not None:
        console.print(Panel(
            Markdown(
                f"""
```json
{result.model_dump_json(indent=2)}
```
"""
            ),
            title="final result",
        ))
    elif err := frame.last_step().error:
        console.print(Panel(
            Markdown(
                err.content
            ),
            title="result error",
        ))



