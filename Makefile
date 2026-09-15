GRAMMAR_REPOSITORY := https://github.com/butvinm/tree-sitter-refal5
GRAMMAR_COMMIT := $(shell sed -n 's/^commit = "\(.*\)"/\1/p' extension.toml)
PYTHON ?= python3
VENV := .venv
# Rebuilt whenever the grammar commit in extension.toml changes
STAMP := $(VENV)/.grammar-$(GRAMMAR_COMMIT)

.PHONY: test

test: $(STAMP)
	$(VENV)/bin/python tests/test_indent.py
	$(VENV)/bin/python tests/test_outline.py

# tree-sitter is pinned because 0.26.0 crashes on Python 3.14
$(STAMP):
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --quiet "tree-sitter==0.25.2"
	$(VENV)/bin/pip install --quiet --force-reinstall --no-deps "tree-sitter-refal5 @ git+$(GRAMMAR_REPOSITORY)@$(GRAMMAR_COMMIT)"
	rm -f $(VENV)/.grammar-*
	touch $@
