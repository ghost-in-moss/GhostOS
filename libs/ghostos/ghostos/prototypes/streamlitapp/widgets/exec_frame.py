from typing import List, Union, Dict, Iterable, Tuple
import streamlit_antd_components as sac
from ghostos.core.aifunc import ExecFrame, ExecStep


def flatten_exec_frame_tree(frame: ExecFrame) -> Dict[str, Union[ExecFrame, ExecStep]]:
    def iter_frame(fr: ExecFrame, bloodline: List[int]) -> Iterable[Tuple[str, Union[ExecFrame, ExecStep]]]:
        yield __frame_label(fr, bloodline), fr
        idx = 0
        for step in fr.steps:
            idx += 1
            next_bloodline = bloodline.copy()
            next_bloodline.append(idx)
            yield from iter_step(step, next_bloodline)

    def iter_step(step: ExecStep, bloodline: List[int]) -> Iterable[Tuple[str, Union[ExecStep, ExecFrame]]]:
        yield __step_label(step, bloodline), step
        idx = 0
        for fra in step.frames:
            idx += 1
            next_bloodline = bloodline.copy()
            next_bloodline.append(idx)
            yield from iter_frame(fra, next_bloodline)

    result = {}
    for key, value in iter_frame(frame.model_copy(), []):
        result[key] = value
    return result


def render_exec_frame_tree(label: str, frame: ExecFrame):
    root = build_exec_frame_tree_node(frame.model_copy(), [])
    return sac.tree(
        [root],
        label=label,
        size="lg",
        open_all=True,
        show_line=True,
    )


def build_exec_frame_tree_node(frame: ExecFrame, bloodline: List[int]) -> sac.TreeItem:
    children = []
    if len(bloodline) < 20:
        steps = frame.steps
        idx = 0
        for step in steps:
            idx += 1
            next_bloodline = bloodline.copy()
            next_bloodline.append(idx)
            step_node = build_exec_step_tree_node(step, next_bloodline)
            children.append(step_node)
    return sac.TreeItem(
        label=__frame_label(frame, bloodline),
        icon="stack",
        tooltip=f"click to see the frame details",
        children=children,
    )


def build_exec_step_tree_node(step: ExecStep, bloodline: List[int]) -> sac.TreeItem:
    children = []
    if len(bloodline) < 20:
        idx = 0
        for frame in step.frames:
            idx += 1
            next_bloodline = bloodline.copy()
            next_bloodline.append(idx)
            frame_node = build_exec_frame_tree_node(frame, next_bloodline)
            children.append(frame_node)
    return sac.TreeItem(
        __step_label(step, bloodline),
        icon="circle" if len(children) == 0 else "plus-circle",
        tooltip=f"click to see the step details",
        children=children,
    )


def __frame_label(frame: ExecFrame, bloodline: List[int]) -> str:
    suffix = ""
    if len(bloodline) > 0:
        suffix = "__" + "_".join([str(c) for c in bloodline])
    return frame.func_name() + suffix


def __step_label(step: ExecStep, bloodline: List[int]) -> str:
    suffix = ""
    if len(bloodline) > 0:
        suffix = "__" + "_".join([str(c) for c in bloodline])
    return step.func_name() + suffix
