from typing import TYPE_CHECKING
from ghostos.helpers.dictionary import (dict_without_none, dict_without_zero)
from ghostos.helpers.string import camel_to_snake
from ghostos.helpers.yaml import yaml_pretty_dump, yaml_multiline_string_pipe
from ghostos.helpers.modules import (
    import_from_path,
    import_class_from_path,
    parse_import_path_module_and_attr_name,
    join_import_module_and_spec,
    get_module_attr,
    generate_module_and_attr_name,
    generate_import_path,
    Importer,
    is_method_belongs_to_class,
    get_calling_modulename,
    rewrite_module,
    rewrite_module_by_path,
    create_module,
    create_and_bind_module,
)
from ghostos.helpers.io import BufferPrint
from ghostos.helpers.timeutils import Timeleft, timestamp_datetime, timestamp
from ghostos.helpers.hashes import md5, sha1, sha256
from ghostos.helpers.trans import gettext, ngettext, get_current_locale, GHOSTOS_DOMAIN

from ghostos.helpers.coding import reflect_module_code, unwrap
from ghostos.helpers.openai import get_openai_key
from ghostos.helpers.tree_sitter import tree_sitter_parse, code_syntax_check

if TYPE_CHECKING:
    from typing import Callable


# --- private methods --- #
def __uuid() -> str:
    from uuid import uuid4
    # keep uuid in 32 chars
    return md5(str(uuid4()))


# --- facade --- #

uuid: "Callable[[], str]" = __uuid
""" patch this method to change global uuid generator"""
