import pytest


@pytest.fixture(autouse=True)
def _isolate_state():
    from django.core.cache import cache

    from trips.api import rate_limit

    cache.clear()
    rate_limit.reset()
    yield
