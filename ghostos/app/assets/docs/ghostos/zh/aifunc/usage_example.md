同步调用的例子: 

```python 
from ghostos_container import Container
from ghostos.core.aifunc import AIFuncExecutor
from ghostos.demo.aifuncs.weather import WeatherAIFunc, WeatherAIFuncResult


# 同步调用. 
def call_example(con: Container, req: WeatherAIFunc) -> WeatherAIFuncResult:
    '''
    async call an AIFunc and wait for result
    '''
    executor = con.force_fetch(AIFuncExecutor)
    return executor.execute(req)
``` 

异步调用的例子: 

```python 
from ghostos_container import Container
from ghostos.core.aifunc import AIFuncExecutor, ExecFrame
from ghostos.core.messages import new_basic_connection
from ghostos.demo.aifuncs.weather import WeatherAIFunc, WeatherAIFuncResult


def stream_call_example(con: Container, req: WeatherAIFunc) -> WeatherAIFuncResult:
    '''
    async call an AIFunc and wait for result
    '''
    from threading import Thread

    executor = con.force_fetch(AIFuncExecutor)

    stream, receiver = new_basic_connection()
    frame = ExecFrame.from_func(req)
    t = Thread(target=executor.execute, args=(req, frame, stream))
    t.start()

    with receiver:
        for msg in receiver.recv():
            # do something
            pass
    t.join()
    return frame.get_result()
```