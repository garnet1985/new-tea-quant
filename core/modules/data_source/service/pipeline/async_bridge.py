"""在 JobPipeline 线程 worker 内运行 async coroutine。"""
from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any, Coroutine, TypeVar

T = TypeVar("T")


def run_async_in_sync(coro: Coroutine[Any, Any, T]) -> T:
    """在同步/线程池上下文中运行 async coro（与 BundleExecutionService 原逻辑一致）。"""

    def _run_in_new_loop() -> T:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            try:
                pending = asyncio.all_tasks(loop)
                if pending:
                    loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
            except Exception:
                pass
            try:
                asyncio.set_event_loop(None)
            except Exception:
                pass
            loop.close()

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return _run_in_new_loop()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_run_in_new_loop).result()
