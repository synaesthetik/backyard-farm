.PHONY: docs docs-serve docs-clean

# Build reference documentation (MkDocs + Material theme)
# Prerequisites: Python 3 and pip must be available
docs:
	pip install -r requirements-docs.txt -q
	mkdocs build --strict

# Serve docs locally at http://127.0.0.1:8000 for live preview
docs-serve:
	pip install -r requirements-docs.txt -q
	mkdocs serve

# Remove built site directory
docs-clean:
	rm -rf site/
