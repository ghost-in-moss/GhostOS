from ghostos.core.aifunc import ExecFrame, ExecStep, AIFunc, AIFuncResult
from threading import Thread


class Tool(AIFunc):
    foo: str = "foo"


class ToolResult(AIFuncResult):
    err: str = ""


def test_exec_frame():
    def next_step(f: ExecFrame, depth: int):
        if depth > 3:
            return
        for i in range(3):
            st = f.new_step()
            threads = []
            for k in range(3):
                sub_frame = st.new_frame(Tool())
                th = Thread(target=next_step, args=(sub_frame, depth + 1))
                th.start()
                threads.append(th)
            for th in threads:
                th.join()

    t = Tool()
    fr = ExecFrame.from_func(t)
    next_step(fr, 0)

    assert len(fr.steps) == 3
    for step in fr.steps:
        assert step.depth == 0
        assert len(step.frames) == 3
    assert fr.depth == 0
    assert fr.steps[0].frames[0].steps[0].frames[0].depth == 2


