"""进程间 SharedMemory：创建方必须持有句柄直到 cleanup。

跨平台差异（Python 3.9+）：

- **Windows**（``os.name == "nt"``）
  - 不走 resource_tracker；块在最后一个 handle ``close`` 后销毁。
  - ``SharedMemory.unlink()`` 实际是空操作。
  - 创建方必须一直持有返回的 ``SharedMemory``，否则 worker
    ``SharedMemory(name=wnsm_…)`` 会报「找不到指定的文件」。

- **POSIX**（Linux / macOS）
  - create/attach 都会 ``resource_tracker.register``。
  - 创建方/attach 方立刻 ``unregister``，避免 spawn 子进程退出时误 unlink。
  - cleanup 用 ``_posixshmem.shm_unlink``，**不要**再调会二次
    ``unregister`` 的 ``SharedMemory.unlink()``（3.9 tracker 会
    ``KeyError: '/psm_…'``）。
"""
from __future__ import annotations

import os
from typing import Optional, Set

try:
    from multiprocessing.shared_memory import SharedMemory
except ImportError:  # pragma: no cover
    SharedMemory = None  # type: ignore[misc, assignment]

_IS_WINDOWS = os.name == "nt"

# POSIX：本进程已 UNREGISTER 过的 ``_name``（含前导 /）。Windows 不用。
_UNREGISTERED: Set[str] = set()


def shared_memory_available() -> bool:
    return SharedMemory is not None


def create_owned_shared_memory(blob: bytes) -> "SharedMemory":
    """创建一块共享内存并写入 ``blob``；调用方必须持有返回值直到 ``close_and_unlink``。"""
    if SharedMemory is None:
        raise RuntimeError("multiprocessing.shared_memory 不可用")
    if not blob:
        raise ValueError("shared memory blob 不能为空")
    shm = SharedMemory(create=True, size=len(blob))
    try:
        shm.buf[: len(blob)] = blob
    except Exception:
        close_and_unlink(shm)
        raise
    _detach_from_resource_tracker(shm)
    return shm


def attach_shared_memory(name: str) -> "SharedMemory":
    """按名 attach。POSIX 勿传已带 ``/`` 的 ``_name``（会变成 ``//psm_…``）。"""
    if SharedMemory is None:
        raise RuntimeError("multiprocessing.shared_memory 不可用")
    text = str(name or "").strip()
    if not _IS_WINDOWS and text.startswith("/"):
        text = text[1:]
    shm = SharedMemory(name=text)
    _detach_from_resource_tracker(shm)
    return shm


def close_and_unlink(shm: Optional["SharedMemory"]) -> None:
    """关闭句柄；POSIX 再销毁命名对象。Windows 仅 close（末 handle 即销毁）。"""
    if shm is None:
        return
    name = getattr(shm, "_name", None)
    try:
        shm.close()
    except Exception:
        pass
    if _IS_WINDOWS:
        return
    _posix_shm_unlink(name)
    if name:
        _UNREGISTERED.discard(str(name))


def _detach_from_resource_tracker(shm: "SharedMemory") -> None:
    """POSIX：UNREGISTER 一次，并屏蔽后续 ``shm.unlink()`` 的二次 UNREGISTER。

    Windows：SharedMemory 根本不 register，这里什么都不做（也不要 unregister）。
    """
    if _IS_WINDOWS:
        return
    key = getattr(shm, "_name", None)
    if key:
        text = str(key)
        if text not in _UNREGISTERED:
            try:
                from multiprocessing import resource_tracker

                resource_tracker.unregister(text, "shared_memory")
            except Exception:
                pass
            _UNREGISTERED.add(text)
    _patch_posix_unlink_no_tracker(shm)


def _patch_posix_unlink_no_tracker(shm: "SharedMemory") -> None:
    """仅 POSIX：实例 ``unlink`` 改成只 ``shm_unlink``，不再打 tracker。"""

    def _unlink_no_tracker() -> None:
        _posix_shm_unlink(getattr(shm, "_name", None))

    try:
        shm.unlink = _unlink_no_tracker  # type: ignore[method-assign]
    except Exception:
        pass


def _posix_shm_unlink(name: Optional[str]) -> None:
    if _IS_WINDOWS or not name:
        return
    try:
        from _posixshmem import shm_unlink

        shm_unlink(name)
    except FileNotFoundError:
        pass
    except Exception:
        pass


__all__ = [
    "attach_shared_memory",
    "close_and_unlink",
    "create_owned_shared_memory",
    "shared_memory_available",
]
