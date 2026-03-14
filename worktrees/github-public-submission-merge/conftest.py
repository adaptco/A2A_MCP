"""Pytest bootstrap: project-path setup plus async fallback runner."""

import asyncio
import inspect
import sys
from pathlib import Path


PROJECT_ROOT = str(Path(__file__).resolve().parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def pytest_pyfunc_call(pyfuncitem):
    """Execute async tests when pytest-asyncio is not available."""
    testfunction = pyfuncitem.obj
    if inspect.iscoroutinefunction(testfunction):
        asyncio.run(testfunction(**pyfuncitem.funcargs))
        return True
    return None
