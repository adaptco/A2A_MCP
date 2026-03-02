# conftest.py – Project root marker for pytest
# This file ensures that the project root is added to sys.path,
# allowing imports like `from agents.tester import TestReport` to resolve.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
