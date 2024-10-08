from __future__ import annotations

from typing import ClassVar, Callable, Optional, MutableMapping, Literal, List, Dict, Set
from abc import ABC
from typing_extensions import Self

from ghostos.prototypes.streamlitapp.utils.session import SessionStateValue
from pydantic import BaseModel, Field
import streamlit as st
from pathlib import Path
from ghostos.helpers import generate_import_path

__all__ = ["Router", 'Route', 'Link']


class Link:
    """
    wrap streamlit page functions
    """

    def __init__(
            self,
            name: str,
            page: str | Path | Callable[[], None],
            *,
            title: str | None = None,
            icon: str | None = None,
            url_path: str | None = None,
    ):
        self.name = name
        self.page = page
        self.title = title if title else name
        self.icon = icon
        self.url_path = url_path if url_path else name

    def st_page(self, *, default: bool = False, url_path: Optional[str] = None) -> st.Page:
        return st.Page(
            page=self.page,
            title=self.title,
            icon=self.icon,
            url_path=url_path,
            default=default,
        )

    def switch_page(self, url_path: Optional[str] = None) -> None:
        st.switch_page(self.st_page(url_path=url_path))


class Route(SessionStateValue, BaseModel, ABC):
    """
    wrap the basic methods:
    1. the data useful to render a streamlit page
    2. switch to a streamlit page
    3. render a navigation
    4. render a page switch button
    5. render a page switch dialog
    """

    link: ClassVar[Link]

    help: Optional[str] = Field(None, description="help message of the route")
    query: str = Field("", description="urlpath query")

    def page(self, default: bool = False) -> st.Page:
        url_path = self.full_url_path()
        return self.link.st_page(url_path=url_path, default=default)

    def full_url_path(self) -> str:
        url_path = self.link.url_path
        if self.query:
            url_path += "?" + self.query
        return url_path

    def switch_page(self) -> None:
        """
        bind self to the session state and switch the page.
        """
        # bind the route value to the session state
        url_path = self.full_url_path()
        self.bind(st.session_state)
        self.link.switch_page(url_path=url_path)

    def render_page_link(
            self, *,
            typ: Literal["primary", "secondary"] = "secondary",
            disabled: bool = False,
            use_container_width: bool = False,
    ):
        """
        shall run under `with st.sidebar`
        """
        label = self.link.title
        help_ = self.help
        st.page_link(
            self.page(),
            label=label,
            help=help_,
            icon=self.link.icon,
            disabled=disabled,
            use_container_width=use_container_width,
        )

    @classmethod
    def session_state_key(cls) -> str:
        return generate_import_path(cls)

    @classmethod
    def get(cls, session_state: MutableMapping) -> Optional[Self]:
        key = cls.session_state_key()
        if key in session_state:
            return session_state[key]
        return None

    @classmethod
    def default(cls) -> Self:
        return cls()

    def bind(self, session_state: MutableMapping) -> None:
        key = self.session_state_key()
        session_state[key] = self


class Router:

    def __init__(self, routes: List[Route], *, sidebar_buttons: List[str] = None):
        self.routes: Dict[str, Route] = {}
        self.routes_order = []
        self.append(*routes)
        self.sidebar_buttons = sidebar_buttons

    def append(self, *routes: Route):
        for route in routes:
            name = route.link.name
            if name in self.routes:
                raise KeyError(f"Duplicate route name: {name}")
            self.routes[name] = route
            self.routes_order.append(name)

    def pages(self, default: Optional[str] = None, names: Optional[List[str]] = None) -> List[st.Page]:
        pages = []
        if names is None:
            names = self.routes_order
        idx = 0
        for name in names:
            route = self.routes[name]
            if default is None:
                is_default = idx == 0
            else:
                is_default = name == default
            idx += 1
            page = route.page(default=is_default)
            pages.append(page)
        return pages

    def render_sidebar_page_links(
            self,
            names: Optional[List[str]] = None,
            primary: Optional[Set[str]] = None,
            disabled: Optional[Set[str]] = None,
            use_container_width: bool = True,
    ) -> None:
        if names is None:
            names = self.sidebar_buttons
        if names is None:
            names = self.routes_order
        for name in names:
            route = self.routes[name]
            is_disabled = disabled is not None and name in disabled
            route.render_page_link(
                typ="primary" if primary and name in primary else "secondary",
                disabled=is_disabled,
                use_container_width=use_container_width,
            )
