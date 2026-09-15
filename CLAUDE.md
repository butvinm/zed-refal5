# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Zed extension for Refal-5 with no extension code of its own: `languages/refal5` holds the language config and tree-sitter queries (highlights, brackets, indents, outline). The grammar lives in https://github.com/butvinm/tree-sitter-refal5 and is pinned by commit in `extension.toml`. The `grammars/` directory is Zed's checkout of that commit, not the grammar source. The grammar repo keeps its own `queries/highlights.scm` for tools other than Zed, so keep it identical to `languages/refal5/highlights.scm` when changing either.

## Commands

- `make test`: build `.venv` with tree-sitter and the grammar at the pinned commit, then check that every query compiles, every fixture parses, a replay of Zed's auto-indent reproduces every fixture, and the outline lists the expected functions. CI runs the same on every PR.
- `.venv/bin/python tests/test_indent.py tests/fixtures/blocks.ref`: test one fixture, once `make test` has built `.venv`.
- In Zed, click Rebuild on the Refal5 card in Extensions (or run `zed: rebuild dev extension`) to load changes, and `zed: open log` to see query or grammar errors.

## Releases

`version` in `extension.toml` is the only release signal. Do not infer releases
from commit messages, create tags manually, or add a separate release command.
Keep its line in the form `version = "0.2.2"`: the release job reads this fixed
format with Bash and sed directly in the workflow, without a separate script.
When a release is intended, increase the stable `major.minor.patch` version in
the same changes that are to be released. Manually check that version in Zed
before pushing or merging it to `master`.

On a push to `master`, CI runs `make test`, then compares the manifest version
before and after the entire push. An unchanged version only runs tests; a lower
version fails release validation. PRs never publish. A version increase creates
a lightweight `v<version>` tag at the tested push commit, a GitHub Release with
generated notes, and an update PR in `zed-industries/extensions`. CI never edits
the manifest. A tag created with the workflow token does not need to trigger
another workflow: all release steps run in the same job.

Re-run a failed workflow after fixing external configuration. Existing tags must
point to the same commit, and an existing GitHub Release is reused. Do not move
published tags or reuse version numbers. Acceptance of the registry PR remains
under Zed's control; a GitHub Release alone does not mean the catalog is updated.

## Grammar changes

Zed rejects a whole query file that mentions a node the pinned grammar doesn't have. So a grammar change takes two PRs: merge the tree-sitter-refal5 PR first, with a merge commit rather than a squash (a squash creates a new hash), then update `commit` in `extension.toml` here, in the same PR as any query that uses the new nodes. `make test` fails if a query doesn't compile against the pin.

## Indentation

The target layout is https://github.com/butvinm/Json.ref: a construct split across lines continues one level deeper than the line it starts on, and its closing bracket returns to that line's indentation. This covers function and call block bodies, the `,` `:` `=` lines after a pattern, results continued past their `=` or `,` line, and multi-line `<...>` and `(...)`.

How Zed applies `indents.scm`, as read from its source:

- A line is indented relative to the previous non-blank line: one level deeper if an `@indent` range starts on that line and continues past this one, or back to the indentation of the start line of a range that ends between the two lines. It never goes two levels deeper in one line and never aligns to a column.
- `@start` moves a range's start to the end of the captured node, and `@end` moves its end to the start of the captured node.
- When an edit changes a line's suggested indent, Zed does not apply it if the line has just ended up inside an ERROR node. That is why the grammar accepts unfinished sentences and conditions: code being typed must parse without errors for indentation to follow.

## Tests

`tests/zed_autoindent.py` ports Zed's `Buffer::suggest_autoindents` and `Buffer::compute_autoindents`, because Zed cannot test an extension without a person typing. `tests/test_indent.py` replays it over `tests/fixtures/*.ref` in three scenarios: each line with the rest of the file correct, select all + `editor: auto indent`, and typing each line key by key after Enter, with brackets auto-closed. The typing scenario fails a line whose indent is wrong after any keystroke from its first character, since that is what a user sees. Fixtures are written in the target layout, so their own indentation is the expected result. Known disagreements are listed with a reason in `KNOWN_FAILURES`, and the run fails when one of them starts passing.

`tests/test_outline.py` builds outline items from `outline.scm` the way Zed does (`Buffer::next_outline_item`): the `@context` and `@name` captures joined by spaces, with an `@annotation` attached when it ends on the line right above the item. `outline.scm` drives Zed's `outline: toggle`, the outline panel and the breadcrumbs.

The ports can go stale when Zed changes its auto-indent or outline code. Before relying on the tests, and whenever Zed releases a new version, compare `ZED_VERSION` in `tests/zed_autoindent.py` with the latest release:

```sh
gh release view --repo zed-industries/zed --json tagName
```

If it is newer, diff the ported functions (named in the docstrings of `tests/zed_autoindent.py` and `tests/test_outline.py`) between the tags, for example by fetching `crates/language/src/buffer.rs` at each tag with `gh api "repos/zed-industries/zed/contents/crates/language/src/buffer.rs?ref=<tag>" -H 'Accept: application/vnd.github.raw'` (search the Zed repo for the function names if the file has moved). Port any behavior change, then update `ZED_VERSION`.

## Editing gotchas

- A Refal line comment must start with `*` at column 0, but `editor: toggle comments` inserts `* ` after the indentation, and extensions cannot ship keybindings. The README gives a keybinding with `ignore_indent`.
- Zed matches a code fence tag against the language name and `path_suffixes`, not `code_fence_block_name`, which is why `refal` is listed as a suffix.
