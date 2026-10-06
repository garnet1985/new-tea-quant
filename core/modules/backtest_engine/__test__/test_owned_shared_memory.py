"""创建方持有 SharedMemory 句柄时，close attach 后仍可再次 attach。"""
from __future__ import annotations

import io
import os
import time
from contextlib import redirect_stderr

import pytest

from core.modules.backtest_engine.core.shared.owned_shared_memory import (
    attach_shared_memory,
    close_and_unlink,
    create_owned_shared_memory,
    shared_memory_available,
)

pytestmark = pytest.mark.force_run

_IS_WINDOWS = os.name == "nt"


@pytest.mark.skipif(not shared_memory_available(), reason="shared_memory 不可用")
def test_owner_handle_keeps_mapping_alive_after_attach_close() -> None:
    blob = b"ntq-shm"
    owner = create_owned_shared_memory(blob)
    try:
        for _ in range(2):
            attached = attach_shared_memory(owner.name)
            try:
                assert bytes(attached.buf[: len(blob)]) == blob
            finally:
                attached.close()
    finally:
        name = owner.name
        close_and_unlink(owner)

    with pytest.raises((FileNotFoundError, OSError)):
        attach_shared_memory(name)


@pytest.mark.skipif(not shared_memory_available(), reason="shared_memory 不可用")
@pytest.mark.skipif(_IS_WINDOWS, reason="resource_tracker 仅 POSIX SharedMemory 使用")
def test_unlink_after_detach_does_not_keyerror_resource_tracker() -> None:
    """回归：create 已 UNREGISTER 后再 shm.unlink() 不得再打 tracker。"""
    owner = create_owned_shared_memory(b"ntq-shm-unlink")
    err = io.StringIO()
    try:
        with redirect_stderr(err):
            owner.unlink()
            time.sleep(0.35)
    finally:
        try:
            owner.close()
        except Exception:
            pass
    text = err.getvalue()
    assert "KeyError" not in text
    assert "resource_tracker" not in text or "/psm_" not in text


@pytest.mark.skipif(not shared_memory_available(), reason="shared_memory 不可用")
@pytest.mark.skipif(not _IS_WINDOWS, reason="Windows 专用：unregister 不得对未 register 的块调用")
def test_windows_create_does_not_touch_resource_tracker() -> None:
    """Windows SharedMemory 不 register；误 unregister 会 KeyError。"""
    err = io.StringIO()
    owner = None
    try:
        with redirect_stderr(err):
            owner = create_owned_shared_memory(b"ntq-shm-win")
            attached = attach_shared_memory(owner.name)
            attached.close()
            time.sleep(0.2)
    finally:
        close_and_unlink(owner)
    assert "KeyError" not in err.getvalue()
