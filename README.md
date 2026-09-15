# Refal5 for Zed

[Refal5](https://en.wikipedia.org/wiki/Refal) language support for [Zed](https://zed.dev), including syntax highlighting, comment toggling, auto-indentation, and code outline.

## Installation

1. Clone

```shell
git clone https://github.com/butvinm/zed-refal5
```

2. Install as Dev extension

Zed -> Extensions -> Install Dev Extension -> Select cloned directory

## Comments

A Refal line comment must start with `*` at column 0, but `editor: toggle comments` inserts `* ` after the indentation. Extensions cannot ship keybindings, so add this to your keymap to comment at column 0 in `.ref` files:

```json
{
  "context": "Editor && extension == ref",
  "bindings": {
    "cmd-/": ["editor::ToggleComments", { "ignore_indent": true }]
  }
}
```
