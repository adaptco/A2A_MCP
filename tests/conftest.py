import asyncio
import inspect


def pytest_pyfunc_call(pyfuncitem):
    testfunction = pyfuncitem.obj
    if inspect.iscoroutinefunction(testfunction):
        asyncio.run(testfunction(**pyfuncitem.funcargs))
        return True
    return None
