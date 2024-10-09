from __future__ import annotations

from typing import ClassVar, Callable, Optional, MutableMapping, Literal, List, Dict, Set, Union
from abc import ABC
from typing_extensions import Self
from ghostos.prototypes.streamlitapp.utils.session import SessionStateValue
from ghostos.helpers import generate_import_path, import_from_path
from pydantic import BaseModel, Field
import streamlit as st
from pathlib import Path
from gettext import gettext as _
import streamlit_antd_components as sac

__all__ = ["Router", 'Route', 'Link']


class Link:
    """
    wrap streamlit page functions
    """

    def __init__(
            self,
            name: str,
            import_path: str,
            *,
            button_help: Optional[str] = None,
            menu_desc: Optional[str] = None,
            url_path: str | None = None,
            streamlit_icon: str = ":material/box:",
            antd_icon: str = "box-fill",
    ):
        self.name = name
        self.import_path = import_path
        self.streamlit_icon = streamlit_icon
        self.antd_icon = antd_icon
        self.button_help = button_help
        self.menu_desc = menu_desc
        self.url_path = url_path if url_path else name

    def st_page(
            self, *,
            default: bool = False,
            title: Optional[str] = None,
            url_path: Optional[str] = None,
    ) -> st.Page:
        title = _(title) if title is not None else None
        # function
        if ':' in self.import_path:
            page = import_from_path(self.import_path)
        else:
            page = self.import_path

        return st.Page(
            page=page,
            title=title,
            icon=self.streamlit_icon,
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
    url_query: str = Field("", description="urlpath query")

    def page(self, default: bool = False) -> st.Page:
        url_path = self.full_url_path()
        return self.link.st_page(url_path=url_path, default=default)

    @classmethod
    def label(cls) -> str:
        return _(cls.link.name)

    def full_url_path(self) -> str:
        url_path = self.link.url_path
        if self.url_query:
            url_path += "?" + self.url_query
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
            disabled: bool = False,
            use_container_width: bool = False,
    ):
        """
        shall run under `with st.sidebar`
        """
        label = self.label()
        help_ = self.link.button_help
        if help_ is not None:
            help_ = _(help_)
        st.page_link(
            self.page(),
            label=label,
            help=help_,
            icon=self.link.streamlit_icon,
            disabled=disabled,
            use_container_width=use_container_width,
        )

    def antd_menu_item(self, children: Optional[List[sac.MenuItem]] = None) -> sac.MenuItem:
        """
        generate menu item
        """
        menu_desc = self.link.menu_desc
        if menu_desc is not None:
            menu_desc = _(menu_desc)
        return sac.MenuItem(
            label=self.label(),
            description=menu_desc,
            children=children,
            icon=self.link.antd_icon,
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

    def __init__(
            self,
            routes: List[Route], *,
            home: str,
            navigator_names: List[str],
            default_menu: Dict[str, Union[sac.MenuItem, Dict, None]],
            default_sidebar_buttons: List[str],
    ):
        self.routes: Dict[str, Route] = {}
        self.routes_order = []
        self.home = home
        self.append(*routes)
        self.default_menu_tree = default_menu
        self.default_sidebar_buttons = default_sidebar_buttons
        self.default_navigator_names = navigator_names

    def append(self, *routes: Route):
        for route in routes:
            name = route.label()
            if name in self.routes:
                raise KeyError(f"Duplicate route name: {name}")
            self.routes[name] = route
            self.routes_order.append(name)

    def render_homepage(self) -> None:
        route = self.routes[self.home]
        route.render_page_link(use_container_width=True)

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

    def render_page_links(
            self, *,
            names: Optional[List[str]],
            disabled: Optional[Set[str]] = None,
            use_container_width: bool = True,
    ) -> None:
        for name in names:
            route = self.routes[name]
            is_disabled = disabled is not None and name in disabled
            route.render_page_link(
                disabled=is_disabled,
                use_container_width=use_container_width,
            )

    def render_navigator(
            self,
            disabled: Optional[Set[str]] = None,
            use_container_width: bool = True,
    ):
        self.render_page_links(
            names=self.default_navigator_names,
            disabled=disabled,
            use_container_width=use_container_width,
        )

    def render_default_sidebar_buttons(
            self,
            disabled: Optional[Set[str]] = None,
            use_container_width: bool = True,
    ) -> None:
        self.render_page_links(
            names=self.routes_order,
            disabled=disabled,
            use_container_width=use_container_width,
        )

    def antd_menu_items(self, node_tree: Dict[str, Union[sac.MenuItem, Dict, None]]) -> List[sac.MenuItem]:
        result = []
        for label in node_tree:
            item = node_tree[label]
            if isinstance(item, sac.MenuItem):
                item.label = label
                result.append(item)
            else:
                if label not in self.routes:
                    raise KeyError(f"menu label : {label} not found in Route")
                route = self.routes[label]
                children = None
                if isinstance(item, dict) and len(item) > 0:
                    children = self.antd_menu_items(item)
                menu_item = route.antd_menu_item(children)
                result.append(menu_item)
        return result

    def default_antd_menu_items(self) -> List[sac.MenuItem]:
        return self.antd_menu_items(self.default_menu_tree)

    def render_antd_menu(self, items: List[sac.MenuItem]) -> Optional[Route]:
        choose = sac.menu(items, index=-1)
        if choose in self.routes:
            return self.routes[choose]
        return None
