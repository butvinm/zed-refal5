"""Test languages/refal5 against the grammar pinned in extension.toml.

1. Every query in languages/refal5 compiles.
2. Every fixture in tests/fixtures parses without errors.
3. Zed's auto-indent, replayed by zed_autoindent.py, reproduces each fixture's own indentation in three scenarios: each line with the rest of the file correct, select all + `editor: auto indent`, and typing each line key by key.

Usage: python tests/test_indent.py [FIXTURE...]
"""
import sys
from pathlib import Path

from tree_sitter import Query

import zed_autoindent as zed

ROOT = Path(__file__).resolve().parent.parent
QUERIES = ROOT / "languages" / "refal5"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

SCENARIOS = {
    "per-line": lambda lines, query: {row: (indent, None) for row, indent in zed.per_line(lines, query).items()},
    "auto-indent": lambda lines, query: {row: (indent, None) for row, indent in zed.auto_indent(lines, query).items()},
    "typing": zed.typing,
}

# Known disagreements as (fixture, line number, scenario): reason.
# The run fails when one of them stops failing, so remove it then.
KNOWN_FAILURES = {
    ("conditions.ref", 4, "typing"): "typing `<` inserts `<>`, which does not parse as a call until the callee is typed",
    ("conditions.ref", 13, "typing"): "typing `<` inserts `<>`, which does not parse as a call until the callee is typed",
}


def check_queries():
    failures = []
    for path in sorted(QUERIES.glob("*.scm")):
        try:
            Query(zed.LANGUAGE, path.read_text())
        except Exception as error:
            failures.append(f"{path.relative_to(ROOT)}: does not compile: {error}")
    return failures


def check_fixture(path, query):
    lines = path.read_text().split("\n")
    tree = zed.PARSER.parse("\n".join(lines).encode())
    if tree.root_node.has_error:
        return [f"{path.name}: fixture does not parse without errors"]

    failures = []
    skip = zed.comment_rows(lines)
    for scenario, run in SCENARIOS.items():
        for row, (indent, typed) in sorted(run(lines, query).items()):
            if row in skip:
                continue
            want = zed.indent_len(lines[row])
            key = (path.name, row + 1, scenario)
            if indent == want:
                if key in KNOWN_FAILURES:
                    failures.append(f"{path.name}:{row + 1} [{scenario}] now passes, remove it from KNOWN_FAILURES")
                continue
            if key in KNOWN_FAILURES:
                continue
            when = f" after typing {typed!r}" if typed else ""
            failures.append(f"{path.name}:{row + 1} [{scenario}] indent {indent}, want {want}{when}: {lines[row].strip()}")
    return failures


def main():
    fixtures = [Path(arg) for arg in sys.argv[1:]] or sorted(FIXTURES.glob("*.ref"))
    query = Query(zed.LANGUAGE, (QUERIES / "indents.scm").read_text())
    failures = check_queries()
    for path in fixtures:
        fixture_failures = check_fixture(path, query)
        print(f"{'FAIL' if fixture_failures else 'ok  '} {path.name}")
        failures += fixture_failures
    for failure in failures:
        print(failure)
    print(f"Replaying Zed {zed.ZED_VERSION} auto-indent: {len(failures)} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
