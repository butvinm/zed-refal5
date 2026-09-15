"""A replay of Zed's auto-indent, to test languages/refal5/indents.scm without running Zed.

Ported from Buffer::suggest_autoindents and Buffer::compute_autoindents in Zed's crates/language/src/buffer.rs:
https://github.com/zed-industries/zed/blob/v1.19.2/crates/language/src/buffer.rs

Only what this extension uses is ported: the @indent, @start, @end and @outdent captures, the (ERROR) guard, and Zed's default auto_indent_using_last_non_empty_line = true. Line-pattern rules such as increase_indent_pattern are not ported.

How Zed indents a line: relative to the previous non-blank line, one level deeper if a range from indents.scm starts on that line and continues past this one, or back to the start line of a range that ends between the two lines. When an edit changes a line's suggestion, Zed applies the new one unless the line has just ended up inside an ERROR node.
"""
import tomllib
from dataclasses import dataclass
from pathlib import Path

import tree_sitter_refal5
from tree_sitter import Language, Parser, Query, QueryCursor

ZED_VERSION = "1.19.2"

LANGUAGE = Language(tree_sitter_refal5.language())
PARSER = Parser(LANGUAGE)
ERROR_QUERY = Query(LANGUAGE, "(ERROR) @error")
CONFIG = tomllib.loads((Path(__file__).resolve().parent.parent / "languages" / "refal5" / "config.toml").read_text())
TAB_SIZE = CONFIG.get("tab_size", 4)

OPEN = {"{": "}", "(": ")", "<": ">"}
CLOSE = {close: open for open, close in OPEN.items()}


def indent_len(line):
    return len(line) - len(line.lstrip(" \t"))


def is_blank(line):
    return not line.strip()


def point(p):
    return (p.row, p.column)


@dataclass
class Suggestion:
    basis_row: int
    delta: int  # -1, 0 or 1 level
    within_error: bool


class Snapshot:
    """A parsed buffer with the indent ranges and error ranges Zed derives from it."""

    def __init__(self, lines, query):
        self.lines = lines
        self.tree = PARSER.parse("\n".join(lines).encode())
        self.ranges = self._indent_ranges(query)
        self.errors = [
            (point(node.start_point), point(node.end_point))
            for _, captures in QueryCursor(ERROR_QUERY).matches(self.tree.root_node)
            for node in captures["error"]
        ]

    def _indent_ranges(self, query):
        ranges = []
        outdents = []
        for _, captures in QueryCursor(query).matches(self.tree.root_node):
            start = end = None
            for node in captures.get("indent", []):
                start = start or point(node.start_point)
                end = end or point(node.end_point)
            for node in captures.get("start", []):
                start = point(node.end_point)
            for node in captures.get("end", []):
                end = point(node.start_point)
            for node in captures.get("outdent", []):
                outdents.append(point(node.start_point))
            if start is None or end is None or start[0] == end[0]:
                continue
            for existing in ranges:
                if existing[0] == start:
                    existing[1] = max(existing[1], end)
                    break
            else:
                ranges.append([start, end])
        ranges.sort()
        for position in sorted(outdents):
            for existing in reversed(ranges):
                if existing[0] <= position < existing[1]:
                    existing[1] = position
                    break
        return ranges

    def _prev_non_blank_row(self, row):
        while row > 0:
            row -= 1
            if not is_blank(self.lines[row]):
                return row
        return None

    def suggest(self, first_row, end_row):
        prev_row = self._prev_non_blank_row(first_row) or 0
        prev_row_start = (prev_row, indent_len(self.lines[prev_row]))
        suggestions = []
        for row in range(first_row, end_row):
            row_start = (row, indent_len(self.lines[row]))
            indent_from_prev = False
            outdent_to = None
            for start, end in self.ranges:
                if start[0] >= row:
                    break
                if start[0] == prev_row and end > row_start:
                    indent_from_prev = True
                if prev_row_start < end <= row_start:
                    outdent_to = start[0] if outdent_to is None else min(outdent_to, start[0])
            within_error = any(start[0] < row and end > row_start for start, end in self.errors)
            if outdent_to == prev_row:
                suggestion = Suggestion(prev_row, 0, within_error)
            elif indent_from_prev:
                suggestion = Suggestion(prev_row, 1, within_error)
            elif outdent_to is not None and outdent_to < prev_row:
                suggestion = Suggestion(outdent_to, 0, within_error)
            else:
                suggestion = Suggestion(prev_row, 0, within_error)
            suggestions.append(suggestion)
            prev_row, prev_row_start = row, row_start
        return suggestions

    def resolve(self, suggestion, computed=None):
        base = (computed or {}).get(suggestion.basis_row, indent_len(self.lines[suggestion.basis_row]))
        return max(0, base + TAB_SIZE * suggestion.delta)


def per_line(lines, query):
    """Indent Zed suggests for each line when every other line is already correct."""
    snapshot = Snapshot(lines, query)
    return {
        row: snapshot.resolve(snapshot.suggest(row, row + 1)[0])
        for row, line in enumerate(lines)
        if not is_blank(line)
    }


def auto_indent(lines, query):
    """Indent of each line after select all + `editor: auto indent`."""
    snapshot = Snapshot(lines, query)
    computed = {}
    for row, suggestion in enumerate(snapshot.suggest(0, len(lines))):
        computed[row] = snapshot.resolve(suggestion, computed)
    return {row: indent for row, indent in computed.items() if not is_blank(lines[row])}


def typing(lines, query):
    """Type each line key by key after pressing Enter at the end of the previous line, with the previous lines correct.

    Returns, for each line, the indent it has after every keystroke from the first character on: the first wrong one if any, otherwise the final one, with the typed text at that moment.
    """
    results = {}
    for row, line in enumerate(lines):
        if row == 0 or is_blank(line):
            continue
        previous = lines[:row]
        content = line.lstrip(" \t")
        want = indent_len(line)

        # Enter inserts a new line, which always takes the suggestion.
        snapshot = Snapshot(_typed_buffer(previous, row, indent_len(previous[-1]), ""), query)
        indent = snapshot.resolve(snapshot.suggest(row, row + 1)[0])
        before = Snapshot(_typed_buffer(previous, row, indent, ""), query)
        old = before.suggest(row, row + 1)[0]

        result = None
        for typed in range(1, len(content) + 1):
            after = Snapshot(_typed_buffer(previous, row, indent, content[:typed]), query)
            new = after.suggest(row, row + 1)[0]
            new_indent = after.resolve(new)
            if new_indent != before.resolve(old) and (not new.within_error or old.within_error):
                indent = new_indent
                after = Snapshot(_typed_buffer(previous, row, indent, content[:typed]), query)
                new = after.suggest(row, row + 1)[0]
            before, old = after, new
            if indent != want:
                result = (indent, content[:typed])
                break
        results[row] = result or (indent, content)
    return results


def _typed_buffer(previous, row, indent, typed):
    """The buffer while `typed` is typed on `row`, with brackets and quotes auto-closed as Zed does.

    Closers for brackets opened on this row follow the cursor. Closers for brackets opened on earlier rows sit on their own lines below, as Enter between a pair leaves them.
    """
    stack, quote = _unclosed("\n".join(previous + [" " * indent + typed]))
    same_row = "".join(OPEN[bracket] for bracket, bracket_row in reversed(stack) if bracket_row == row)
    below = [
        " " * indent_len(previous[bracket_row]) + OPEN[bracket]
        for bracket, bracket_row in reversed(stack)
        if bracket_row < row
    ]
    return previous + [" " * indent + typed + quote + same_row] + below


def _unclosed(text):
    """Brackets left open at the end of `text` as (bracket, row), and the quote left open, if any."""
    stack = []
    row = column = 0
    state = None  # None, "'", '"', "block" or "line"
    i = 0
    while i < len(text):
        char = text[i]
        if char == "\n":
            row, column = row + 1, 0
            if state == "line":
                state = None
            i += 1
            continue
        step = 1
        if state in ("'", '"'):
            if char == "\\":
                step = 2
            elif char == state:
                state = None
        elif state == "block":
            if text.startswith("*/", i):
                state, step = None, 2
        elif column == 0 and char == "*":
            state = "line"
        elif text.startswith("/*", i):
            state, step = "block", 2
        elif char in ("'", '"'):
            state = char
        elif char in OPEN:
            stack.append((char, row))
        elif char in CLOSE and stack and stack[-1][0] == CLOSE[char]:
            stack.pop()
        i, column = i + step, column + step
    return stack, state if state in ("'", '"') else ""


def comment_rows(lines):
    """Rows of line comments and multi-line block comments, where indentation is free text.

    A line like `/* empty */ = /* empty */;` is code, since its comments close on the same line.
    """
    rows = set()
    in_block = False
    for row, line in enumerate(lines):
        starts_in_block = in_block
        opens_block_at_start = False
        i = 0
        while i < len(line):
            if not in_block and line.startswith("/*", i):
                opens_block_at_start = opens_block_at_start or not line[:i].strip()
                in_block, i = True, i + 2
            elif in_block and line.startswith("*/", i):
                in_block, i = False, i + 2
            else:
                i += 1
        if starts_in_block or line.startswith("*") or (in_block and opens_block_at_start):
            rows.add(row)
    return rows
