from ghostiss.helpers.dictionary import (dict_without_none, dict_without_zero)
from ghostiss.helpers.string import camel_to_snake
from ghostiss.helpers.yaml import yaml_pretty_dump, yaml_multiline_string_pipe
from ghostiss.helpers.modules import (
    import_from_path, parse_import_module_and_spec, join_import_module_and_spec,
    get_module_spec, generate_module_spec, generate_import_path,
    Importer,
)
from ghostiss.helpers.io import BufferPrint
from ghostiss.helpers.time import Timeleft

from typing import Callable


# --- private methods --- #
def __uuid() -> str:
    from uuid import uuid4
    return str(uuid4())


# --- facade --- #

uuid: Callable[[], str] = __uuid
""" patch this method to change global uuid generator"""

