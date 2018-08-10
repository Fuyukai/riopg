"""
pytest helpers
"""
import os

import inspect
import multio
import pytest
from functools import wraps


def _wrapper(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        return multio.run(fn, *args, **kwargs)

    return inner


# copied from trio
@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    if inspect.iscoroutinefunction(pyfuncitem.obj):
        pyfuncitem.obj = _wrapper(pyfuncitem.obj)


# not copied from trio
@pytest.fixture(scope="session", autouse=True)
def multio_init(*args, **kwargs):
    multio.init(os.environ.get("MULTIO_LIB"))
