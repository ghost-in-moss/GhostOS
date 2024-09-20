import inspect
from typing import Optional

from ghostos.prototypes.mosstemp import template
from ghostos.helpers import get_calling_modulename, rewrite_module_by_path

__all__ = ['init_moss_module']


def init_moss_module(modulename: Optional[str] = None):
    """
    init moss file with default template
    """
    if not modulename:
        modulename = get_calling_modulename(1)
    source = inspect.getsource(template)
    rewrite_module_by_path(modulename, source)
