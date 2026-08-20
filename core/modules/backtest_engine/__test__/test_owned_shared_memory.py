"""创建方持有 SharedMemory 句柄时，close attach 后仍可再次 attach。"""
from __future__ import annotations

import pytest

from core.modules.backtest_engine.core.shared.owned_shared_memory import (
    attach_shared_memory,
    close_and_unlink,
    create_owned_shared_memory,
    shared_memory_available,
)

pytestmark = pytest.mark.force_run


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
