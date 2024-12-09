# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from dataclasses import field
from typing import Any, Generator, TypedDict

from dataclasses_json import dataclass_json
import mesop as me

# pylint: disable=E0402
from .styles import _STYLE_CURRENT_NAV, _STYLE_MAIN_HEADER

# pylint: disable=E0402


class Page(TypedDict):
    """Page class"""

    display: str
    route: str


page_data = [
    {"display": "Generate story", "route": "/"},
    {"display": "Marketing campaign", "route": "/marketing"},
    {"display": "Image playground", "route": "/images"},
    {"display": "Video playground", "route": "/videos"},
]

page_json = [Page(**data) for data in page_data]  # type: ignore[typeddict-item]


@dataclass_json
@me.stateclass
class State:
    """Mesop state class"""

    # pylint: disable=E3701
    pages: list[Page] = field(default_factory=lambda: page_json)
    current_page: str = ""
    # pylint: disable=E3701


def navigate_to(e: me.ClickEvent) -> Generator[None, Any, None]:
    """Navigate to a page event"""
    s = me.state(State)
    s.current_page = e.key
    me.navigate(e.key)
    yield


def page_navigation_menu(url: str) -> None:
    """Page navigation menu creation"""
    print(f"url: {url}")
    state = me.state(State)
    with me.box(style=_STYLE_MAIN_HEADER):
        with me.box(style=me.Style(display="flex", flex_direction="row", gap=12)):
            for page in state.pages:
                disabled = False
                if state.current_page == page.get("route"):
                    disabled = True
                me.button(
                    page.get("display"),
                    key=f"{page.get('route')}",
                    on_click=navigate_to,
                    disabled=disabled,
                    style=_STYLE_CURRENT_NAV if disabled else me.Style(),
                    # type="flat" if disabled else "stroked"
                )


@me.content_component
def nav_menu(url: str) -> str:
    """Navigation menu component"""
    page_navigation_menu(url=url)
    me.slot()

    state = me.state(State)
    return state.current_page
