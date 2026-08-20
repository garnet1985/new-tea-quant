"""Timeline SHM：创建方持有句柄后，重复 attach 仍可读。"""
from __future__ import annotations

import pytest

from core.infra.utils.core.owned_shared_memory import shared_memory_available
from core.modules.backtest_engine.core.timeline.timeline import Timeline

pytestmark = pytest.mark.force_run


@pytest.mark.skipif(not shared_memory_available(), reason="shared_memory 不可用")
def test_timeline_shm_readable_after_publish() -> None:
    timeline = Timeline.from_points(["20240101", "20240102"])
    Timeline._publish(timeline)
    try:
        info = {"name": Timeline._shm_name, "size": Timeline._shm_size}
        first = Timeline._read_shm(info)
        second = Timeline._read_shm(info)
        assert first is not None and second is not None
        assert first.points == ("20240101", "20240102")
        assert second.points == first.points
    finally:
        Timeline._unlink_shm()
