"""进程间 SharedMemory：创建方必须持有句柄。

Windows 上 ``SharedMemory.close()`` 会关掉最后一个 mapping handle，
子进程再 ``SharedMemory(name=wnsm_…)`` 就会报「找不到指定的文件」。
POSIX 上 close 只关 fd，对象仍在直到 unlink；两边统一：创建方持有到 cleanup。
"""
from __future__ import annotations

from typing import Optional

try:
    from multiprocessing.shared_memory import SharedMemory
except ImportError:  # pragma: no cover
    SharedMemory = None  # type: ignore[misc, assignment]


def shared_memory_available() -> bool:
    return SharedMemory is not None


def create_owned_shared_memory(blob: bytes) -> "SharedMemory":
    """创建一块共享内存并写入 ``blob``；调用方必须一直持有返回值直到 unlink。"""
    if SharedMemory is None:
        raise RuntimeError("multiprocessing.shared_memory 不可用")
    if not blob:
        raise ValueError("shared memory blob 不能为空")
    shm = SharedMemory(create=True, size=len(blob))
    try:
        shm.buf[: len(blob)] = blob
        _unregister_from_resource_tracker(shm)
    except Exception:
        try:
            shm.close()
            shm.unlink()
        except Exception:
            pass
        raise
    return shm


def attach_shared_memory(name: str) -> "SharedMemory":
    if SharedMemory is None:
        raise RuntimeError("multiprocessing.shared_memory 不可用")
    shm = SharedMemory(name=name)
    _unregister_from_resource_tracker(shm)
    return shm


def close_and_unlink(shm: Optional["SharedMemory"]) -> None:
    if shm is None:
        return
    try:
        shm.close()
    except Exception:
        pass
    try:
        shm.unlink()
    except FileNotFoundError:
        pass
    except Exception:
        pass


def _unregister_from_resource_tracker(shm: "SharedMemory") -> None:
    """避免 spawn 子进程把父进程的 mapping 提前 unlink。"""
    try:
        from multiprocessing import resource_tracker

        name = getattr(shm, "_name", None) or shm.name
        resource_tracker.unregister(name, "shared_memory")
    except Exception:
        pass
