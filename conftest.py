<<<<<<< HEAD
"""Root conftest.py — ensures project root is on sys.path and configures pytest-asyncio."""
import sys
from pathlib import Path

# Insert project root so `from orchestrator...` and `from agents...` work everywhere
PROJECT_ROOT = str(Path(__file__).resolve().parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
=======
import asyncio
import inspect


def pytest_pyfunc_call(pyfuncitem):
    testfunction = pyfuncitem.obj
    if inspect.iscoroutinefunction(testfunction):
        asyncio.run(testfunction(**pyfuncitem.funcargs))
        return True
    return None
>>>>>>> 117e2e444ff3d500482857ebf717156179fbdeed
