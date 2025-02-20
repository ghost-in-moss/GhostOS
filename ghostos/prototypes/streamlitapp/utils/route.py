from __future__ import annotations

from typing import ClassVar, Callable, Optional, MutableMapping, TypeVar, List, Dict, Set, Union
from abc import ABC
from typing_extensions import Self
from ghostos.prototypes.streamlitapp.utils.session import SessionStateValue
from ghostos_common.helpers import generate_import_path, import_from_path
from pydantic import BaseModel, Field
import streamlit as st
from streamlit.navigation.page import StreamlitPage
from ghostos_common.helpers import gettext as _
import streamlit_antd_components as sac
from urllib.parse import urlencode

__all__ = ["Router", 'Route', 'Link']

T = TypeVar("T")


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
        self.url_path = url_path if url_path else name.lower().replace(" ", '_')
        self._page_instance: Optional[StreamlitPage] = None

    def st_page(
            self, *,
            default: bool = False,
            title: Optional[str] = None,
    ) -> st.Page:
        title = _(title) if title is not None else None
        # function
        if self._page_instance is None:
            if ':' in self.import_path:
                page_method = import_from_path(self.import_path)
            else:
                page_method = self.import_path

            self._page_instance = st.Page(
                page=page_method,
                title=title,
                icon=self.streamlit_icon,
                url_path=self.url_path,
                default=default,
            )
        return self._page_instance

    def switch_page(self, params: Optional[dict] = None) -> None:
        if params:
            st.query_params.from_dict(params)
        st.switch_page(self.st_page())


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

    def page(self, default: bool = False) -> st.Page:
        return self.link.st_page(default=default)

    @property
    def url_query(self) -> str:
        data = self.model_dump(exclude_defaults=True)
        return urlencode(data)

    @classmethod
    def label(cls) -> str:
        return _(cls.link.name)

    def switch_page(self) -> None:
        """
        bind self to the session state and switch the page.
        """
        # bind the route value to the session state
        self.bind(st.session_state)
        self.link.switch_page(self.model_dump(exclude_defaults=True))

    def rerun(self) -> None:
        self.bind(st.session_state)
        st.rerun()

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
        self.bind(st.session_state)
        page = self.page()
        st.page_link(
            page,
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
            data = session_state[key]
            for key, val in st.query_params.items():
                data[key] = val
            return cls(**data)
        return None

    def bind(self, session_state: MutableMapping) -> None:
        from ghostos_container import get_caller_info
        key = self.session_state_key()
        session_state[key] = self.model_dump(exclude_defaults=True)

    @classmethod
    def label_of_current_page(cls) -> str:
        current = generate_import_path(Route)
        if current in st.session_state:
            return st.session_state[current]
        return ""

    @classmethod
    def get_route_bound(cls, value: T, key: str = "") -> T:
        if not key:
            key = generate_import_path(type(value))
        session_key = cls.session_state_key() + ":" + key
        if session_key in st.session_state:
            return st.session_state[session_key]
        st.session_state[session_key] = value
        return value


class Router:

    def __init__(
            self,
            routes: List[Route], *,
            home: str,
            navigator_page_names: List[str],
            default_menu: Dict[str, Union[sac.MenuItem, Dict, None]],
            default_sidebar_buttons: List[str],
            current_page: str = None,
    ):
        self.routes: Dict[str, Route] = {}
        self.routes_order = []
        self.home = home
        self.append(*routes)
        self.default_menu_tree = default_menu
        self.default_sidebar_buttons = default_sidebar_buttons
        self.default_navigator_names = navigator_page_names
        self.current_page: str = current_page if current_page is not None else self.home

    def with_current(self, route: Route) -> Self:
        self.current_page = route.label()
        self.routes[route.label()] = route
        return self

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
        """
        render sidebar pages
        :param default:
        :param names:
        :return:
        """
        pages = []
        if names is None:
            names = self.routes_order
        idx = 0
        if default is None:
            default = self.current_page

        for name in names:
            route = self.routes[name]
            is_default = name == default
            idx += 1
            if is_default:
                route.bind(st.session_state)
            page = route.page(default=is_default)
            pages.append(page)
        return pages

    def render_page_links(
            self, *,
            names: Optional[List[str]],
            disabled: Optional[Set[str]] = None,
            use_container_width: bool = True,
    ) -> None:
        """
        render streamlit page link buttons
        """
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
        """
        render default page links built buttons
        """
        self.render_page_links(
            names=self.default_navigator_names,
            disabled=disabled,
            use_container_width=use_container_width,
        )

    def _antd_menu_items(self, node_tree: Dict[str, Union[sac.MenuItem, Dict, None]]) -> List[sac.MenuItem]:
        """
        return antd menu items from routes.
        """
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
                    children = self._antd_menu_items(item)
                menu_item = route.antd_menu_item(children)
                result.append(menu_item)
        return result

    def default_antd_menu_items(self) -> List[sac.MenuItem]:
        return self._antd_menu_items(self.default_menu_tree)

    def render_antd_menu(self, items: List[sac.MenuItem]) -> Optional[Route]:
        choose = sac.menu(items, index=-1)
        if choose in self.routes:
            return self.routes[choose]
        return None
