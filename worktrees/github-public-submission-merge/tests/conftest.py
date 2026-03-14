import sys
import os
from pathlib import Path

# Add the project root to sys.path so tests can import from 'app', 'orchestrator', 'schemas', etc.
# This assumes conftest.py is in the 'tests' directory, one level below root.
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
