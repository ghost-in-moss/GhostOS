from ghostos.helpers.dictionary import (dict_without_none, dict_without_zero)
from ghostos.helpers.string import camel_to_snake
from ghostos.helpers.yaml import yaml_pretty_dump, yaml_multiline_string_pipe
from ghostos.helpers.modules import (
    import_from_path, parse_import_module_and_spec, join_import_module_and_spec,
    get_module_spec, generate_module_spec, generate_import_path,
    Importer, is_method_belongs_to_class,
)
from ghostos.helpers.io import BufferPrint
from ghostos.helpers.time import Timeleft

from typing import Callable


# --- private methods --- #
def __uuid() -> str:
    from uuid import uuid4
    return str(uuid4())


# --- facade --- #

uuid: Callable[[], str] = __uuid
""" patch this method to change global uuid generator"""

