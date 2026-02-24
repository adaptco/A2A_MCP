#!/bin/sh

# Find all Python files and lint them
find . -name "*.py" -print0 | xargs -0 pylint --fail-under=8.0
