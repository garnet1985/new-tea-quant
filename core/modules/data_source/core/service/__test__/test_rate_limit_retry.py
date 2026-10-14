"""频率超限：暂停该接口的限流器，等窗口过去再请求。"""
import time

from core.modules.data_source.core.base_class.base_provider import BaseProvider
from core.modules.data_source.core.data_class.error import ProviderError
from core.modules.data_source.core.service.rate_limiter import (
    _RATE_LIMITERS,
    _RATE_LIMITERS_LOCK,
    RateLimiter,
)


class _Provider(BaseProvider):
    provider_name = "tushare"

    def _initialize(self):
        return None


def test_namechange_limit_is_the_token_cap():
    from userspace.extensions.data_source.providers.tushare.provider import TushareProvider

    assert TushareProvider.api_limits["get_namechange"] == 500


def test_pause_holds_the_next_acquire():
    limiter = RateLimiter(max_per_minute=10, api_name="pause-test")
    limiter.pause(0.2)
    started = time.perf_counter()
    limiter.acquire()
    assert time.perf_counter() - started >= 0.15


def test_rate_limit_retries_after_the_window():
    key = "tushare:get_namechange"
    limiter = RateLimiter(max_per_minute=10, api_name=key)
    with _RATE_LIMITERS_LOCK:
        previous = _RATE_LIMITERS.get(key)
        _RATE_LIMITERS[key] = limiter
    provider = _Provider(config={})
    provider._RATE_LIMIT_PAUSE_SECONDS = 0.05
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("抱歉，您访问接口(namechange)频率超限(500次/分钟)")
        return "ok"

    try:
        assert provider.invoke_with_retry("get_namechange", fn) == "ok"
        assert calls["n"] == 2
    finally:
        with _RATE_LIMITERS_LOCK:
            if previous is None:
                _RATE_LIMITERS.pop(key, None)
            else:
                _RATE_LIMITERS[key] = previous


def test_rate_limit_gives_up_after_two_waits():
    provider = _Provider(config={})
    provider._RATE_LIMIT_PAUSE_SECONDS = 0.0

    def fn():
        raise RuntimeError("频率超限(500次/分钟)")

    try:
        provider.invoke_with_retry("get_namechange", fn)
        assert False, "expected ProviderError"
    except ProviderError as error:
        assert "频率超限" in str(error.original_error)
