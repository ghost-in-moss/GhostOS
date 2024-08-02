from ghostiss.helpers.dictionary import (dict_without_none, dict_without_zero)
from ghostiss.helpers.string import camel_to_snake
from ghostiss.helpers.yaml import yaml_pretty_dump, yaml_multiline_string_pipe
from ghostiss.helpers.modules import import_from_str
from ghostiss.helpers.io import BufferPrint

from typing import Callable


# --- private methods --- #
def __uuid() -> str:
    from uuid import uuid4
    return str(uuid4())


# --- facade --- #

uuid: Callable[[], str] = __uuid
""" patch this method to change global uuid generator"""

