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
from typing import TypedDict

from dataclasses_json import dataclass_json
import mesop as me


class Page(TypedDict):
    display: str
    route: str


page_json = [
    {"display": "Generate story", "route": "/"},
    {"display": "Marketing campaign", "route": "/marketing"},
    {"display": "Image playground", "route": "/images"},
    {"display": "Video playground", "route": "/videos"},
]


@dataclass_json
@me.stateclass
class State:
    pages: list[Page] = field(default_factory=lambda: page_json)
    current_page: str


def navigate_to(e: me.ClickEvent):
    s = me.state(State)
    s.current_page = e.key
    me.navigate(e.key)
    yield


_DEFAULT_BORDER = me.Border.all(
    me.BorderSide(
        color="#e0e0e0",
        width=1,
        style="solid",
    )
)

_STYLE_MAIN_HEADER = me.Style(
    border=_DEFAULT_BORDER,
    padding=me.Padding.all(5),
)

_STYLE_CURRENT_NAV = me.Style(color="#99000", border_radius=0, font_weight="bold")


def page_navigation_menu(url: str) -> None:
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
    page_navigation_menu(url=url)
    me.slot()

    state = me.state(State)
    return state.current_page
