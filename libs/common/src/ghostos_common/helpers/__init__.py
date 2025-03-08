from typing import TYPE_CHECKING
from ghostos_common.helpers.dictionary import (dict_without_none, dict_without_zero)
from ghostos_common.helpers.string import camel_to_snake
from ghostos_common.helpers.yaml import yaml_pretty_dump, yaml_multiline_string_pipe
from ghostos_common.helpers.modules import (
    import_from_path,
    import_class_from_path,
    import_instance_from_path,
    parse_import_path_module_and_attr_name,
    join_import_module_and_spec,
    get_module_attr,
    generate_module_and_attr_name,
    generate_import_path,
    get_module_fullname_from_path,
    Importer,
    is_method_belongs_to_class,
    get_calling_modulename,
    rewrite_module,
    rewrite_module_by_path,
    create_module,
    create_and_bind_module,
)
from ghostos_common.helpers.io import BufferPrint
from ghostos_common.helpers.timeutils import Timeleft, timestamp_datetime, timestamp, timestamp_ms
from ghostos_common.helpers.hashes import md5, sha1, sha256
from ghostos_common.helpers.trans import gettext, ngettext, GHOSTOS_DOMAIN

from ghostos_common.helpers.coding import reflect_module_code, unwrap
from ghostos_common.helpers.openai import get_openai_key
from ghostos_common.helpers.tree_sitter import tree_sitter_parse, code_syntax_check
from ghostos_common.helpers.code_analyser import (
    get_code_interface, get_code_interface_str,
    get_attr_source_from_code, get_attr_interface_from_code,
)
from ghostos_common.helpers.files import generate_directory_tree, list_dir, is_pathname_ignored

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
