"""Test languages/refal5/outline.scm the way Zed turns it into outline items.

Ported from Buffer::outline_items_containing_internal and Buffer::next_outline_item in Zed's crates/language/src/buffer.rs (see zed_autoindent.ZED_VERSION): an item's text is its @context and @name captures joined by spaces, and an @annotation belongs to the item when it ends on the line right above it.

Usage: python tests/test_outline.py
"""
import sys
from pathlib import Path

from tree_sitter import Query, QueryCursor

import zed_autoindent as zed

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# Fixture: expected outline items as (text, first line of the annotation or None)
EXPECTED = {
    "functions.ref": [
        ("$ENTRY Escape", "/**"),
        ("MapJoin", None),
        ("Inc", None),
    ],
    "blocks.ref": [
        ("$ENTRY Json-Parse", None),
        ("Parse-Member", None),
        ("$ENTRY Go", None),
        ("Unescape", None),
    ],
}


def outline(source, query):
    tree = zed.PARSER.parse(source)
    items = []
    annotation_rows = []
    for _, captures in QueryCursor(query).matches(tree.root_node):
        if "item" in captures:
            parts = sorted(
                (node for name in ("context", "name") for node in captures.get(name, [])),
                key=lambda node: node.start_byte,
            )
            text = ""
            last_end = None
            for node in parts:
                if text and node.start_byte > last_end:
                    text += " "
                text += source[node.start_byte : node.end_byte].decode()
                last_end = node.end_byte
            items.append((captures["item"][0].start_point.row, text))
        elif "annotation" in captures:
            node = captures["annotation"][0]
            start, end = node.start_point.row, node.end_point.row
            if end > start and node.end_point.column == 0:
                end -= 1
            if annotation_rows and annotation_rows[-1][1] >= start - 1:
                annotation_rows[-1] = (annotation_rows[-1][0], end)
            else:
                annotation_rows.append((start, end))

    lines = source.decode().split("\n")
    result = []
    for row, text in sorted(items):
        annotation = next((start for start, end in annotation_rows if end == row - 1), None)
        result.append((text, lines[annotation].strip() if annotation is not None else None))
    return result


def main():
    query = Query(zed.LANGUAGE, (ROOT / "languages" / "refal5" / "outline.scm").read_text())
    failures = 0
    for fixture, expected in EXPECTED.items():
        actual = outline((FIXTURES / fixture).read_bytes(), query)
        ok = actual == expected
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {fixture}")
        if not ok:
            print(f"  expected {expected}")
            print(f"  actual   {actual}")
    print(f"Outline: {failures} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
