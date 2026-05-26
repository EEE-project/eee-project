import pytest

import eee._registry as _reg


@pytest.fixture(autouse=True)
def reset_registry():
    registered_before = dict(_reg._registered)
    cache_before = dict(_reg._cache)
    fallback_before = _reg._fallback
    yield
    _reg._registered.clear()
    _reg._registered.update(registered_before)
    _reg._cache.clear()
    _reg._cache.update(cache_before)
    _reg._fallback = fallback_before
