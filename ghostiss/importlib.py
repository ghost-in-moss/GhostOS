from __future__ import annotations

from typing import Dict, Any


class Imported:

    def __init__(
            self,
            module: str,
            parent: str,
            variable: str | None = None,
            desc: str | None = None,
    ):
        self.module = module
        self.parent = parent
        self.variable = variable
        self.desc = desc

    def do_import(self) -> Any:
        pass


class ExportedTrie:
    pass


def import_module(module: str, alias: str = "") -> Dict[str, Imported]:
    raise NotImplemented("Import modules not implemented yet")


def import_vars(from_module: str, *values: str, **alias: str) -> Dict[str, Imported]:
    raise NotImplemented("Import vars not implemented yet")


def export_interfaces(*values: Any) -> None:
    raise NotImplemented("Export interfaces not implemented yet")


def export(*values: Any) -> None:
    raise NotImplemented("Export not implemented yet")


def exported() -> ExportedTrie:
    raise NotImplemented("Export not implemented yet")
