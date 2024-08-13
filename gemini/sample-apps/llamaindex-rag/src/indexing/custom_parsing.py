# Copyright 2024 Google, LLC. This software is provided as-is, without
# warranty or representation for any use or purpose. Your use of it is
# subject to your agreement with Google.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Custom Parsing Logic
"""

import copy
import dataclasses
from os import path
import pdb
import re
import typing
from typing import Iterator

import bs4
import markdownify
import marko
import marko.block
import marko.ext
import marko.ext.pangu
from marko.md_renderer import MarkdownRenderer
from more_itertools import windowed
import numpy as np

TABLE_START_MARKER = "START TABLE IN MARKDOWN"
TABLE_END_MARKER = "END TABLE IN MARKDOWN"

SECTION_START_MARKER = "START SECTION"
SECTION_END_MARKER = "END SECTION"

UCS_INFOBOT_SNIPPET_START_MARKER = "_START_OF_TABLE_"
UCS_INFOBOT_SNIPPET_END_MARKER = "_END_OF_TABLE_"

NEW_LINE = "\n"
START_OF_TABLE_SEGMENT = "_START_OF_TABLE_"
END_OF_TABLE_SEGMENT = "_END_OF_TABLE_"
# VERTEXAI_SPAN_TAG = 'vertexai'
# VERTEXAI_STRING_PREFIX = 'VERTEXAI_COMMENT:'

# Tuple witth default HTML elements names to blacklist during cleaning.
# Blacklisted elements, including their children, will be removed recursively.
DEFAULT_CLEAN_HTML_BLACKLIST_ELEMENTS = (
    "title",
    "head",
    "meta",
    "link",
    "script",
    "style",
    "button",
    "img",
)

# Tuple of default HTML element properties to preserve during cleaning. All
# element properties not included in this list will be removed.
DEFAULT_CLEAN_HTML_ALLOWLIST_PROPERTIES = ("rowspan", "colspan")


def convert_html_to_md_text(html_text: str) -> str:
    input_html = simplify_whitespace(html_text)
    soup = bs4.BeautifulSoup(str(input_html), "html.parser")

    for e in soup.select("div.section.blockContent"):
        e.insert_before(
            bs4.BeautifulSoup(f"<span>\n{SECTION_START_MARKER}\n</span>", "html.parser")
        )
        e.insert_after(
            bs4.BeautifulSoup(f"<span>\n{SECTION_END_MARKER}\n</span>", "html.parser")
        )

    # Remove navigational elements that tend to produce very short chunks with
    # only these navigation elements in them, and no semantic value.
    for e in soup.find_all("span", "component_header_button"):
        e.decompose()
    for e in soup.select("a.tab_href"):
        e.decompose()

    soup_clean_html(soup)
    soup_expand_table_colspan(soup)
    soup_expand_table_rowspan(soup)
    soup_convert_tables_to_md(soup)
    for s in soup.select("script"):
        s.extract()
    for s in soup.select("style"):
        s.extract()
    # Markdownify is somehow really sensitive to no newlines around spans, and
    # joins the content that preceeds/follows if there no newline.
    html_str = str(soup)
    html_str = html_str.replace("<span", "\n<span")
    html_str = html_str.replace("</span>", "</span>\n")
    markdown_str = markdownify.markdownify(html_str, heading_style="ATX")

    # TODO: Why are these even left begind?
    markdown_str = markdown_str.replace("![]()", "")

    markdown_str = normalize_markers(markdown_str)
    return remove_trailing_whitespace(markdown_str)


def clean_spaces(string: str) -> str:
    """Cleans input string spaces.

    * Replaces multiple consecutive spaces by a single space.
    * Replace multiple consecutive tabs by a single tab.
    * Replace multiple consecutive newlines by a single newline.
    * Removes multiple consecutive "spacing" characters before a newline.

    Args:
      string: Input string to clean spaces.

    Returns:
      Cleaned spaces from input string.
    """

    string = re.sub(
        pattern=r"(\s*\n\s*)+",
        repl=r"\n",
        string=string,
        flags=re.MULTILINE,
    )
    string = re.sub(
        pattern=r"([ \t])+",
        repl=r" ",
        string=string,
        flags=re.MULTILINE,
    )
    return string


@dataclasses.dataclass
class _CellOffset:
    row: int
    col: int

    def __iter__(self):
        yield self.row
        yield self.col


ANY_WHITESPACE = re.compile(r"\s+", re.MULTILINE)


def soup_clean_html(
    soup: bs4.BeautifulSoup,
    blacklist_elements: tuple[str, ...] = DEFAULT_CLEAN_HTML_BLACKLIST_ELEMENTS,
    allowlist_properties: tuple[str, ...] = (DEFAULT_CLEAN_HTML_ALLOWLIST_PROPERTIES),
    remove_comments: bool = True,
    remove_repeated_blanks: bool = True,
) -> None:
    """Removes or modifies non-semantic content from the HTML dom.

    * Removes html comments when `remove_comments` is True.
    * Replaces all elements not included in `allowlist_elements` and
      `blacklist_elements` by their childrens.
    * Removes all elements included in `blacklist_elements` and their childrens.
    * Removes from all properties from remaining elements not included in
      `allowlist_properties`.
    * Removes repeated blanks from content and replace them by just one instance
      when `remove_repeated_blanks` is True.

    Args:
      soup: `bs4.BeautifulSoup` object containing the html dom to be modified. The
        object in this argument is modified by this function.
      blacklist_elements: Tuple of HTML elements names to blacklist during
        cleaning. Blacklisted elements, including their children, will be removed
        recursively.
      allowlist_elements: Tuple of HTML elements to allow during cleaning.
        Elements in this list will be preserved. Elements not in this list will be
        removed and replaced by their children.
      allowlist_properties: Tuple of HTML element properties to preserve during
        cleaning. All element properties not included in this list will be
        removed.
      remove_comments: Whether to remove html comments (default True).
      remove_repeated_blanks: Whether to remove repeated blanks from content
        (default True).
    """

    if remove_comments:
        for element in soup.find_all(text=lambda text: isinstance(text, bs4.Comment)):
            element.extract()

    for element in soup.find_all(name=blacklist_elements):
        element.decompose()

    for element in soup.find_all():
        # Mark hidden description spans with a prefix
        # if element.name == 'span':
        #   if element.get('id') == VERTEXAI_SPAN_TAG:
        #     element.string = VERTEXAI_STRING_PREFIX + element.string
        # elif
        if element.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            # Markdownify fails miserably if there are newlines or other tags (e.g.
            # divs) inside a heading
            just_text = element.get_text(strip=True)
            element.clear()
            element.string = just_text

    for key in list(soup.attrs.keys()):
        if key not in allowlist_properties:
            del soup[key]
    for element in soup.find_all():
        for key in list(element.attrs.keys()):
            if key not in allowlist_properties:
                del element[key]

    if remove_repeated_blanks:
        for element in soup.find_all(text=True):
            cleaned_string = clean_spaces(string=element.string)
            if re.fullmatch(r"\s*", cleaned_string, flags=re.MULTILINE):
                element.extract()
            elif element.string != cleaned_string:
                element.replace_with(bs4.NavigableString(cleaned_string))


def soup_expand_table_rowspan(element: bs4.Tag) -> None:
    """Materializes cells spanning multiple rows from tables within element.

    Repeats rowspan cells and removes the rowspan property from original cells
    spanning multiple rows.

    Args:
      element: A `bs4.PageElement` object containing the HTML table.
    """

    tables_rowspans = []
    tables_offset = []

    def element_expand_table_rowspan(element: bs4.element.PageElement) -> None:
        if isinstance(element, bs4.NavigableString):
            return

        rowspans = tables_rowspans[0] if tables_rowspans else {}
        offset = tables_offset[0] if tables_offset else _CellOffset(row=0, col=0)
        element = typing.cast(bs4.element.Tag, element)
        if element.name == "table":
            offset = _CellOffset(row=0, col=0)
            rowspans = {}
            tables_rowspans.insert(0, rowspans)
            tables_offset.insert(0, offset)
        elif element.name == "tr":
            offset.col = 0
            insert_element = element
            first_insertion = True
            while tuple(offset) in rowspans:
                new_element = copy.copy(rowspans[tuple(offset)])
                if first_insertion:
                    insert_element.insert(0, new_element)
                    first_insertion = False
                else:
                    insert_element.insert_after(new_element)
                insert_element = new_element
                offset.col += 1
        elif element.name in ("th", "td"):
            if "rowspan" in element.attrs:
                rowspan = element.attrs.get("rowspan", "")
                try:
                    rowspan = int(rowspan)
                except ValueError:
                    rowspan = 1

                for i in range(rowspan - 1):
                    rowspans[(offset.row + i + 1, offset.col)] = element
                del element["rowspan"]

        for child in element.children:
            element_expand_table_rowspan(child)

        if element.name == "table":
            tables_offset.pop(0)
            tables_rowspans.pop(0)
        elif element.name == "tr":
            offset.row += 1
            offset.col = 0
        elif element.name in ("th", "td"):
            offset.col += 1
            insert_element = element
            while tuple(offset) in rowspans:
                new_element = copy.copy(rowspans[tuple(offset)])
                insert_element.insert_after(new_element)
                insert_element = new_element
                offset.col += 1

    element_expand_table_rowspan(element=element)


def soup_expand_table_colspan(element: bs4.PageElement) -> None:
    """Materializes cells spanning multiple cols from tables within element.

    Repeats colspan cells and removes the colspan property from original cells
    spanning multiple cols.

    Args:
      element: A `bs4.PageElement` object containing the HTML table.
    """

    if not isinstance(element, bs4.NavigableString):
        element = typing.cast(bs4.element.Tag, element)
        if element.name in ("th", "td"):
            colspan = element.attrs.get("colspan", "")
            try:
                colspan = int(colspan)
            except ValueError:
                colspan = 1

            for _ in range(colspan - 1):
                del element["colspan"]
                element.insert_after(copy.copy(element))
        for child in element.children:
            soup_expand_table_colspan(element=child)


def element_text_iter(element: bs4.PageElement) -> Iterator[str]:
    if isinstance(element, bs4.NavigableString):
        yield element.string
    else:
        element = typing.cast(bs4.element.Tag, element)
        for child in element.children:
            yield from element_text_iter(child)


def convert_html_text2markdown(element: bs4.PageElement) -> str:
    text = " ".join(element_text_iter(element))
    text = clean_spaces(string=text)
    text = re.sub(pattern=r"([\r\f\b])+", repl=r"", string=text)
    text = re.sub(pattern=r"(\n)+", repl=r"\1", string=text)
    text = re.sub(pattern=r"([ \t])+", repl=r"\1", string=text)
    text = re.sub(pattern=r"(\s)+", repl=r" ", string=text)
    text = re.sub(pattern=r"([|-])", repl=r"\\\1", string=text)
    return text.strip()


def convert_soup_table2markdown(
    table: bs4.Tag,
    pad_columns: bool = False,
) -> str:
    """Converts a table page element to markdown."""

    rows = []
    for row in table.find_all("tr"):
        cols = [
            (column.name == "th", convert_html_text2markdown(column))
            for column in row.find_all(name=("th", "td"))
        ]
        if cols:
            rows.append(cols)

    if not rows:
        return ""

    is_headers = [[is_header for is_header, _ in row] or [False] for row in rows]
    rows = [[value for _, value in row] for row in rows]

    # Transpose if there is not horizontal headers and all values of first column
    # are headers.
    if all(row[0] for row in is_headers) and not all(is_headers[0]):
        rows = list(map(list, zip(*rows)))
        is_headers = list(map(list, zip(*is_headers)))

    # Transpose if there is only a single non-header row, and multiple columns
    if (len(rows) == 1 or (len(rows) == 2 and not all(is_headers[1]))) and len(
        rows[0]
    ) > 1:
        rows = list(map(list, zip(*rows)))
        # If there were headers, they would be row headers now, and we don't handle
        # those well below anyways.
        # TODO: Fix output of row headers.
        is_headers = [[False for item in row] for row in rows]

    max_columns = len(rows[0])

    padding = [
        max(len(row[i]) if i < len(row) else 0 for row in rows)
        for i in range(max_columns)
    ]
    markdown = []
    for row_index, row in enumerate(rows):
        if row_index == 0 and not any(is_headers[row_index]):
            padded_values = [
                " " * padding[i] if pad_columns else "" for i, _ in enumerate(row)
            ]
            markdown.append(f'| {" | ".join(padded_values)} |')
            padded_values = [
                "-" * padding[i] if pad_columns else "-" for i, _ in enumerate(row)
            ]
            markdown.append(f'| {" | ".join(padded_values)} |')

        if row_index != 0 and all(is_headers[row_index]):
            markdown.append("")
        padded_values = [
            value + ((" " * (padding[i] - len(value))) if pad_columns else "")
            for i, value in enumerate(row)
        ]
        markdown.append(f'| {" | ".join(padded_values)} |')

        if (row_index == 0 and any(is_headers[row_index])) or all(
            is_headers[row_index]
        ):
            padded_values = [
                "-" * padding[i] if pad_columns else "-" for i, _ in enumerate(row)
            ]
            markdown.append(f'| {" | ".join(padded_values)} |')
    return NEW_LINE.join(markdown)


def destruct_table(table):
    if table.find("tbody", recursive=False):
        table.find("tbody", recursive=False).replaceWithChildren()

    for tr in table.findAll("tr", recursive=False):
        for td in tr.findAll("td", recursive=False):
            td.replaceWithChildren()

        tr.replaceWithChildren()

    table.replaceWithChildren()


def should_destruct_table(table):
    tbody = table.find("tbody", recursive=False)
    if tbody is not None:
        table = tbody

    if len(table.findAll("tr", recursive=False)) <= 1:
        return True

    if max(len(tr.findAll("td", recursive=False)) for tr in table.findAll("tr")) <= 1:
        return True

    for tr in table.findAll("tr", recursive=False):
        for td in tr.findAll("td", recursive=False):
            if len(td.text) >= 1000:
                return True

    return False


def soup_convert_tables_to_md(soup: bs4.BeautifulSoup) -> None:
    """Converts tables to markdown."""

    table = soup.find("table")
    converted_markdown_tables = 0
    while table is not None:
        if should_destruct_table(table):
            destruct_table(table)

        else:
            table_text = convert_soup_table2markdown(table)
            if not table_text.strip():
                table.decompose()

            new_soup = bs4.BeautifulSoup(
                # f"""<span id="table{i}">{START_OF_TABLE_SEGMENT}{NEW_LINE}TABLE IN MARKDOWN:{NEW_LINE}{NEW_LINE}{table_text}{NEW_LINE}{find_next_vertexai_comment(table)}{NEW_LINE}{END_OF_TABLE_SEGMENT}{NEW_LINE}</span>""", 'html.parser'
                # f"""<span id="table{i}">{TABLE_START_MARKER}{NEW_LINE}{NEW_LINE}{table_text}{NEW_LINE}{find_next_vertexai_comment(table)}{NEW_LINE}{TABLE_END_MARKER}{NEW_LINE}</span>""",
                f"""<span id="table{converted_markdown_tables}">{TABLE_START_MARKER}{NEW_LINE}{NEW_LINE}{table_text}{NEW_LINE}{TABLE_END_MARKER}{NEW_LINE}</span>""",
                "html.parser",
            )
            table.replace_with(new_soup)
            converted_markdown_tables += 1

        table = soup.find("table")


def soup_get_meta_tag(soup, name):
    if tag := soup.find("meta", {"name": name}):
        return tag.get("content", None).lower().strip()
    else:
        return ""


HORIZONTAL_WHITESPACE_PATTERN = re.compile(
    r"[\u0020\u0009\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000\u2028]+"
)
VERTICAL_WHITESPACE_PATTERN = re.compile(r"[\u000A\u000D\u0085]+")
PARAGRAPH_SEPARATOR_PATTERN = re.compile(r"\u2029")


def simplify_whitespace(text):
    text = HORIZONTAL_WHITESPACE_PATTERN.sub(" ", text)
    text = VERTICAL_WHITESPACE_PATTERN.sub("\n", text)
    text = PARAGRAPH_SEPARATOR_PATTERN.sub("\n\n", text)

    return text


def normalize_markers(input):
    # TODO: Can be done with match group replacements in one go
    input = re.sub(
        rf"(\n)+{TABLE_START_MARKER}\n(\n)+",
        repl=rf"\n\n{TABLE_START_MARKER}\n",
        string=input,
    )
    input = re.sub(
        rf"(\n)+{TABLE_END_MARKER}\n(\n)+",
        repl=rf"\n{TABLE_END_MARKER}\n\n",
        string=input,
    )
    input = re.sub(
        rf"(\n)+{SECTION_START_MARKER}\n(\n)+",
        repl=rf"\n\n{SECTION_START_MARKER}\n\n",
        string=input,
    )
    input = re.sub(
        rf"(\n)+{SECTION_END_MARKER}\n(\n)+",
        repl=rf"\n\n{SECTION_END_MARKER}\n\n",
        string=input,
    )
    return input


def remove_trailing_whitespace(input):
    return "\n".join((c.rstrip() for c in input.splitlines()))


def convert_html_to_md_text(html_text: str) -> str:
    input_html = simplify_whitespace(html_text)
    soup = bs4.BeautifulSoup(str(input_html), "html.parser")

    for e in soup.select("div.section.blockContent"):
        e.insert_before(
            bs4.BeautifulSoup(f"<span>\n{SECTION_START_MARKER}\n</span>", "html.parser")
        )
        e.insert_after(
            bs4.BeautifulSoup(f"<span>\n{SECTION_END_MARKER}\n</span>", "html.parser")
        )

    # Remove navigational elements that tend to produce very short chunks with
    # only these navigation elements in them, and no semantic value.
    for e in soup.find_all("span", "component_header_button"):
        e.decompose()
    for e in soup.select("a.tab_href"):
        e.decompose()

    soup_clean_html(soup)
    soup_expand_table_colspan(soup)
    soup_expand_table_rowspan(soup)
    soup_convert_tables_to_md(soup)
    for s in soup.select("script"):
        s.extract()
    for s in soup.select("style"):
        s.extract()
    # Markdownify is somehow really sensitive to no newlines around spans, and
    # joins the content that preceeds/follows if there no newline.
    html_str = str(soup)
    html_str = html_str.replace("<span", "\n<span")
    html_str = html_str.replace("</span>", "</span>\n")
    markdown_str = markdownify.markdownify(html_str, heading_style="ATX")

    # TODO: Why are these even left begind?
    markdown_str = markdown_str.replace("![]()", "")

    markdown_str = normalize_markers(markdown_str)
    return remove_trailing_whitespace(markdown_str)


def convert_html_to_md(input):
    if not isinstance(input, dict):
        raise TypeError(f"'input' must be a dict, got {type(input)}: {input=}")
    markdown_str = convert_html_to_md_text(input["content"])
    soup = bs4.BeautifulSoup(input["content"], "html.parser")
    # title = soup.title.text.strip() if soup.title else ''

    return {
        **{k: v for k, v in input.items() if k != "content"},
        "text": markdown_str,
        "token_length": len(markdown_str) // 5,
    }


# @title split_to_chunks


reference_characters = [r"\*" * i for i in range(1, 11)]

line_lookahead = 10


def fix_citations(md_text: str) -> str:
    lines = md_text.splitlines()
    i_line = 0

    while i_line < len(lines):
        line = lines[i_line]

        found_ref = None
        for ref in reversed(reference_characters):
            if ref not in line:
                continue
            found_ref = ref
            break
        if found_ref is None:
            i_line += 1
            continue

        i_ref_line = None
        for i_maybe_ref_line in range(
            i_line + 1, min(i_line + line_lookahead + 1, len(lines))
        ):
            maybe_ref_line = lines[i_maybe_ref_line]
            if not maybe_ref_line.strip().startswith(found_ref):
                continue
            i_ref_line = i_maybe_ref_line
            break
        if i_ref_line is None:
            i_line += 1
            continue

        replacement_line = lines[i_ref_line].replace(
            found_ref, found_ref.replace("\\", "")
        )

        new_line = line.replace(found_ref, "(" + replacement_line + ")", 1)
        lines[i_line] = new_line
        # TODO(ericpts): This is quadratic in the number of refs. Might have to revisit.
        del lines[i_ref_line]

    return "\n".join(lines)


def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return array[idx]


def destructive_split_to_chunks(input, max_chunk_size):
    num_tables = input.count(f"\n{TABLE_START_MARKER}\n")

    token_length = len(input) // 5

    if token_length <= max_chunk_size:
        return [
            {
                "text": input,
                "token_length": token_length,
            }
        ]

    if num_tables == 0:
        return split_no_tables(input, max_chunk_size)
    if num_tables > 1:
        return split_multiple_tables(input, max_chunk_size)
    else:
        return split_single_table(input, max_chunk_size)


def split_lines_in_two(
    lines,
    split_start_idx,
    common_header_end_idx,
    common_footer_start_idx,
    max_chunk_size,
):
    assert (
        split_start_idx > common_header_end_idx
    ), f"{split_start_idx=} must be greater than {common_header_end_idx=}"
    assert (
        split_start_idx < common_footer_start_idx
    ), f"{split_start_idx=} must be less than {common_footer_start_idx=}"

    top_half = lines[:split_start_idx] + lines[common_footer_start_idx:]
    bottom_half = lines[:common_header_end_idx] + lines[split_start_idx:]
    return [
        *destructive_split_to_chunks("\n".join(top_half), max_chunk_size),
        *destructive_split_to_chunks("\n".join(bottom_half), max_chunk_size),
    ]


# TODO: Can be one patterm
IS_HEADING_RE = re.compile(r"^(%|(#{1,6})) ")
IS_IMPLICIT_HEADING_RE = re.compile(r"^\*\*(.*)\*\*$")


def split_no_tables(input, max_chunk_size):
    lines = input.splitlines()

    def is_heading_or_blank(line):
        return (
            IS_HEADING_RE.search(line)
            or IS_IMPLICIT_HEADING_RE.match(line)
            or not line.strip()
        )

    content_start = 0
    while content_start < len(lines) and is_heading_or_blank(lines[content_start]):
        content_start += 1

    empty_line_idx_list = [
        i for i, l in enumerate(lines[content_start:-1], content_start) if not l.strip()
    ]

    if not empty_line_idx_list:
        token_length = len(input) // 5
        print(
            f"Only one paragraph left, cannot split further: {token_length=} > {max_chunk_size=}"
        )
        return [
            {
                "text": input,
                "token_length": token_length,
            }
        ]

    midpoint_start = (
        find_nearest(empty_line_idx_list, (content_start + len(lines)) // 2) + 1
    )

    return split_lines_in_two(
        lines, midpoint_start, content_start, len(lines), max_chunk_size
    )


def split_multiple_tables(input, max_chunk_size):
    lines = input.splitlines()
    end_table_idx_list = np.where(np.array(lines) == TABLE_END_MARKER)[0]
    first_start_table_end_idx = lines.index(TABLE_START_MARKER)
    last_end_table_start_idx = end_table_idx_list[-1] + 1
    mid_end_table_idx = (
        find_nearest(
            end_table_idx_list,
            (first_start_table_end_idx + last_end_table_start_idx) / 2,
        )
        + 1
    )
    return split_lines_in_two(
        lines,
        mid_end_table_idx,
        first_start_table_end_idx,
        last_end_table_start_idx,
        max_chunk_size,
    )


def split_single_table(input, max_chunk_size):
    print(input)
    lines = input.splitlines()
    table_start_idx = lines.index(TABLE_START_MARKER) + 1
    table_end_idx = lines.index(TABLE_END_MARKER)
    try:
        table_rows_start_idx = next(
            (
                i + 1
                for i, l in enumerate(lines[table_start_idx:], table_start_idx)
                if l.startswith("| - |")
            ),
        )
    except ValueError as e:
        table_rows_start_idx = table_start_idx + 1

    table_subheader_start_idx_list = [
        i - 1
        for i, l in enumerate(lines[table_rows_start_idx:], table_rows_start_idx)
        if l.startswith("| - |")
    ]
    if len(table_subheader_start_idx_list) == 1:
        table_rows_start_idx = table_subheader_start_idx_list[0] + 2

    non_header_rows_count = table_end_idx - table_rows_start_idx
    if non_header_rows_count <= 1:
        token_length = len(input) // 5
        print(
            f"Only one row left in the table, cannot split further: {token_length=} > {max_chunk_size=}"
        )
        return [
            {
                "text": input,
                "token_length": token_length,
            }
        ]
        # raise ValueError(f"Can't split the table further")

    def split_table_in_half(splitpoint_start):
        common_footer_start_idx = table_end_idx
        common_header_end_idx = table_rows_start_idx

        return split_lines_in_two(
            lines,
            splitpoint_start,
            common_header_end_idx,
            common_footer_start_idx,
            max_chunk_size,
        )

    if len(table_subheader_start_idx_list) > 1:
        # TODO: This assumes all lines are equal length, we could do better
        middle_subheader_start_idx = find_nearest(
            table_subheader_start_idx_list, (table_rows_start_idx + table_end_idx) / 2
        )
        return split_table_in_half(middle_subheader_start_idx)
    else:
        return split_table_in_half((table_rows_start_idx + table_end_idx) // 2)


def split_more_to_chunks(
    chunk,
    target_chunk_size,
    max_chunk_size,
    target_heading_level,
    split_sections,
    split_implicit_headings,
):
    token_length = len(chunk) // 5
    if token_length <= target_chunk_size:
        if "NAVSUP FLCSD" in chunk:
            pdb.set_trace()
        return [{"text": chunk, "token_length": token_length}]
    else:
        if target_heading_level < 2:
            new_target_heading_level = target_heading_level + 1
            new_split_sections = False
            new_split_implicit_headings = False
        elif not split_sections:
            # Sections seem to include h3+ headings, so we first split by section
            # then by h3+ headings.
            # TODO: This isn't very robust, as this assumption could change even
            # be different across different docs. We should be able to understand
            # this much more locally: within the section itself.
            new_target_heading_level = 2
            new_split_sections = True
            new_split_implicit_headings = False
        elif target_heading_level < 6:
            new_target_heading_level = target_heading_level + 1
            new_split_sections = True
            new_split_implicit_headings = False
        elif not split_implicit_headings:
            new_target_heading_level = 6
            new_split_sections = True
            new_split_implicit_headings = True
        else:
            return destructive_split_to_chunks(chunk, max_chunk_size)
        # print(f"Calling split_to_chunks(len(doc)={len(c)} target_heading_level={new_target_heading_level} split_sections={new_split_sections} split_implicit_headings={new_split_implicit_headings})")
        return do_split_to_chunks(
            chunk,
            target_chunk_size=target_chunk_size,
            max_chunk_size=max_chunk_size,
            target_heading_level=new_target_heading_level,
            split_sections=new_split_sections,
            split_implicit_headings=new_split_implicit_headings,
        )


def do_split_to_chunks(
    chunk_md,
    target_chunk_size,
    max_chunk_size,
    target_heading_level,
    split_sections,
    split_implicit_headings,
):
    markdown = marko.Markdown(renderer=MarkdownRenderer)
    chunk = markdown.parse(chunk_md)

    def new_heading() -> marko.block.Heading:
        return markdown.parse("# temp").children[0]

    chunks = []
    heading_stack = []

    def new_chunk(with_headings):
        chunk = markdown.parse("")
        if with_headings:
            chunk.children.extend(heading_stack)
        return chunk

    current_chunk = new_chunk(with_headings=False)
    previous_unfinished_chunk = new_chunk(with_headings=False)
    previous_plus_current_chunk = new_chunk(with_headings=False)

    def current_heading_level() -> int:
        try:
            return heading_stack[-1].level
        except IndexError:
            return 0

    def is_implicit_heading(block):
        return (
            isinstance(block, marko.block.Paragraph)
            and len(block.children) == 1
            and isinstance(block.children[0], marko.inline.StrongEmphasis)
        )

    def remove_tail_empty_children(chunk):
        while (
            len(chunk.children) > 0 and not markdown.render(chunk.children[-1]).strip()
        ):
            chunk.children.pop()

    def finish_chunk(allow_merge_with_following=True, new_chunk_with_headings=True):
        nonlocal current_chunk
        nonlocal previous_unfinished_chunk
        nonlocal previous_plus_current_chunk

        remove_tail_empty_children(current_chunk)

        previous_plus_current_md = markdown.render(previous_plus_current_chunk)
        previous_plus_current_token_length = len(previous_plus_current_md) // 5
        previous_unfinished_md = (
            markdown.render(previous_unfinished_chunk)
            if previous_unfinished_chunk
            else ""
        )
        current_md = markdown.render(current_chunk)
        current_token_length = len(current_md) // 5
        current_chunk_semanticaly_empty = all(
            (
                (
                    isinstance(c, marko.block.Heading)
                    or is_implicit_heading(c)
                    or not (rendered := markdown.render(c).strip())
                    or rendered == SECTION_START_MARKER
                    or rendered == SECTION_END_MARKER
                )
                for c in current_chunk.children
            )
        )

        # print(f"finish_chunk:{allow_merge_with_following=}, {target_heading_level=}")
        # print(f"heading_stack={[markdown.render(h) for h in heading_stack]}")
        # print(f"Before:")
        # print("-"*100)
        # print(f"{current_md=}")
        # print(f"{previous_unfinished_md=}")
        # print(f"{previous_plus_current_md=}")

        if (
            allow_merge_with_following
            and previous_plus_current_token_length <= target_chunk_size
        ):
            # We're not yet at target token size with `previous_plus_current` and
            # we could grow it more (because of `allow_merge_with_following`) so
            # don't finish chunking yet, just keep enlarging it until it hits
            # the next branch.
            # For ==, we could finish now, but we have the handle the overshoot
            # case anyways, so we can save some code.
            current_chunk = new_chunk(new_chunk_with_headings)
            if current_chunk_semanticaly_empty:
                # print("b1.1")
                previous_plus_current_chunk = markdown.parse(previous_unfinished_md)
                previous_plus_current_chunk.children.extend(current_chunk.children)
            else:
                # print("b1.2")
                previous_unfinished_chunk = markdown.parse(previous_plus_current_md)
        else:  # not allow_merge_with_following or previous_plus_current_token_length > target_chunk_size
            # We've now exceeded the target on `previous_plus_current or we know
            # we can't grow it further (because of `allow_merge_with_following`
            # beinf False). That means we need to finish `previous_unfinished`
            # as it cannot grow either.
            if previous_unfinished_md.strip():
                # print("b2.a")
                previous_unfinished_token_length = len(previous_unfinished_md) // 5
                # if "NAVSUP FLCSD" in previous_unfinished_md:
                #   pdb.set_trace()
                chunks.append(
                    {
                        "text": previous_unfinished_md,
                        "token_length": previous_unfinished_token_length,
                    }
                )
            previous_unfinished_chunk = None

            if (
                current_token_length > target_chunk_size
                or not allow_merge_with_following
            ):
                # print("b2.b.1")
                # The current chunk can either not be merged with some later one
                # because it's too big, or it's not allowed to merge it. In any
                # case we need to finsih it now.
                if not current_chunk_semanticaly_empty:
                    # Finish the current chunk, including splitting it further if it's
                    # too big.
                    # pdb.set_trace()
                    # print("b2.b.1.a")
                    chunks.extend(
                        split_more_to_chunks(
                            markdown.render(current_chunk),
                            target_chunk_size=target_chunk_size,
                            max_chunk_size=max_chunk_size,
                            target_heading_level=target_heading_level,
                            split_sections=split_sections,
                            split_implicit_headings=split_implicit_headings,
                        )
                    )
                # else:
                # Nothing useful in the current chunk, just drop it on the floor.
                current_chunk = new_chunk(new_chunk_with_headings)
                previous_plus_current_chunk = new_chunk(new_chunk_with_headings)
            else:  # current_token_length <= target_chunk_size and allow_merge_with_following
                # The current chunk is not large enough to finish yet, let it grow and
                # it will get finished later via `previous_plus_current`.
                if not current_chunk_semanticaly_empty:
                    # print("b2.b.2")
                    previous_plus_current_chunk = markdown.parse(current_md)
                    previous_unfinished_chunk = markdown.parse(current_md)
                else:
                    # print("b2.b.3")
                    previous_plus_current_chunk = new_chunk(new_chunk_with_headings)
                current_chunk = new_chunk(new_chunk_with_headings)

        # print(f"After:")
        # print("-"*100)
        # print(f"current_md={repr(markdown.render(current_chunk))}")
        # print(f"previous_plus_current_md={repr(markdown.render(previous_plus_current_chunk))}")
        # print(f"previous_unfinished_md={repr(markdown.render(previous_unfinished_chunk) if previous_unfinished_chunk else '')}")
        # print("*"*100 + "\n")

    def append_chunk(block):
        current_chunk.children.append(block)
        previous_plus_current_chunk.children.append(block)

    for block in chunk.children:
        if isinstance(block, marko.block.Paragraph):
            if markdown.render(block).strip() == SECTION_START_MARKER:
                if split_sections:
                    # A new section is starting. If we're splitting on sections, start
                    # a new chunk. If another section just ended, the current chunk will
                    # be empty and discarded. But sometimes the data is without a section
                    # so we still want to explicitly split here.
                    finish_chunk()
                else:
                    # The marker may be needed later, so keep it - will be removed in a
                    # post-processing step.
                    append_chunk(block)
            elif markdown.render(block).strip() == SECTION_END_MARKER:
                if split_sections:
                    # A section has ended, split the chunk. See above on why are we
                    # splitting on both start and end.
                    finish_chunk()
                else:
                    # The marker may be needed later, so keep it - will be removed in a
                    # post-processing step.
                    append_chunk(block)
            elif is_implicit_heading(block):
                # A paragraph that entirely consists of a strong emphasis we consider
                # an "implicit heading", and is a good last resort to split
                if split_implicit_headings:
                    finish_chunk()
                append_chunk(block)
            else:
                # Just a normal paragraph
                append_chunk(block)
        elif isinstance(block, marko.block.Heading):
            if not markdown.render(block).replace("#", "").strip():
                pass  # Ignore empty headers
            elif block.level <= target_heading_level:
                while len(heading_stack) > 0 and heading_stack[-1].level >= block.level:
                    heading_stack.pop()
                finish_chunk(
                    allow_merge_with_following=(block.level == target_heading_level),
                    new_chunk_with_headings=True,
                )
                heading_stack.append(block)
                append_chunk(block)
            else:
                append_chunk(block)
        else:
            if (
                len(current_chunk.children) > 1
                and not markdown.render(current_chunk.children[-1]).strip()
                and not markdown.render(block).strip()
            ):
                pass  # Skip multiple consecutive empty blocks
            else:
                append_chunk(block)

    finish_chunk(allow_merge_with_following=False)

    return chunks


def normalize_newlines(doc):
    """Ensure there is always a newline before and after a heading, and no
    leading or trailing newlines.
    """
    lines = doc.splitlines()
    output = []
    for p, c, n in windowed([None] + lines + [None], n=3):
        if not marko.block.Heading.pattern.match(c):
            output.append(c)
        else:
            if p is not None and p.strip() and not marko.block.Heading.pattern.match(p):
                output.append("")  # Ensure one empty line before a heading
            output.append(c)
            if n is not None and n.strip():
                output.append("")  # Ensure one empty line after a heading
    return "\n".join(output).strip()


def split_to_chunks(
    input, target_chunk_size=1500, max_chunk_size=2500, target_heading_level=0
):
    if not isinstance(input, dict):
        raise TypeError(f"'input' must be a dict, got {type(input)}")
    doc_title = input["source"]
    doc_md = input["text"]

    if target_heading_level > 2:
        raise ValueError(
            f"'target_heading_level' must be <= 2, got {target_heading_level}"
        )

    try:
        chunks = do_split_to_chunks(
            doc_md,
            target_chunk_size=target_chunk_size,
            max_chunk_size=max_chunk_size,
            target_heading_level=target_heading_level,
            split_sections=False,
            split_implicit_headings=False,
        )
    except Exception as e:
        e.input_name = input["name"]
        raise

    for c in chunks:
        c["text"] = (
            c["text"].replace("\nSTART SECTION\n", "").replace("\nEND SECTION\n", "")
        )
        c["text"] = normalize_newlines(c["text"])
        c["text"] = fix_citations(c["text"])
        lines = c["text"].splitlines()
        h1 = lines[0][2:] if lines[0].startswith("# ") else ""
        if doc_title and (doc_title not in h1):
            if h1 in doc_title:
                c["text"] = "\n".join([f"# {doc_title}", *lines[1:]])
            else:
                h1 = " - " + h1 if h1 else ""
                c["text"] = "\n".join([f"# {doc_title}{h1}", *lines[1:]])

    return [
        {
            **input,
            **c,
        }
        for c in chunks
    ]
