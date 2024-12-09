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

import mesop as me

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


_DEFAULT_BORDER = me.Border.all(
    me.BorderSide(
        color="#e0e0e0",
        width=1,
        style="solid",
    )
)

_STYLE_CONTAINER = me.Style(
    display="grid",
    grid_template_columns="5fr 2fr",
    grid_template_rows="auto 5fr",
    height="100vh",
)

_STYLE_MAIN_HEADER = me.Style(
    border=_DEFAULT_BORDER, padding=me.Padding(top=15, left=15, right=15, bottom=5)
)

_STYLE_MAIN_COLUMN = me.Style(
    border=_DEFAULT_BORDER,
    padding=me.Padding.all(15),
    overflow_y="scroll",
)

_STYLE_TITLE_BOX = me.Style(display="inline-block")

_STORY_INPUT_STYLE = me.Style(
    width="500px"
    # display="flex",
    # flex_basis="max(100vh, calc(50% - 48px))",
)

_BOX_STYLE = me.Style(
    flex_basis="max(100vh, calc(50% - 48px))",
    background="#fff",
    border_radius=12,
    box_shadow=("0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"),
    padding=me.Padding(top=16, left=16, right=16, bottom=16),
    display="flex",
    flex_direction="column",
)

_SPINNER_STYLE = me.Style(
    display="flex",
    flex_direction="row",
    padding=me.Padding.all(16),
    align_items="center",
    gap=10,
)

FANCY_TEXT_GRADIENT = me.Style(
    color="transparent",
    background=(
        "linear-gradient(72.83deg,#4285f4 11.63%,#9b72cb 40.43%,#d96570 68.07%)" " text"
    ),
)

_STYLE_CURRENT_TAB = me.Style(
    color="#99000",
    border_radius=0,
    font_weight="bold",
    border=me.Border(
        bottom=me.BorderSide(color="#000", width=2, style="solid"),
        top=None,
        right=None,
        left=None,
    ),
)

_STYLE_OTHER_TAB = me.Style(
    color="#8d8e9d",
    border_radius=0,
    # font_weight="bold",
)

_TABBER_STYLE = me.Style(
    padding=me.Padding(top=0, right=0, left=0, bottom=2),
    border=me.Border(
        bottom=me.BorderSide(color="#e5e5e5", width=1, style="solid"),
        top=None,
        right=None,
        left=None,
    ),
)
