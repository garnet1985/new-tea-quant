"""POSIX resource tracker：退出时回收残留共享内存，已删除的段不再警告。

Python 3.9 在 Ctrl+C 杀掉进程后仍记着 ``/psm_*``。段若已被 unlink，
标准 tracker 会先警告泄漏，再因文件不存在再警告一次。
"""
from __future__ import annotations

import os
import signal
import sys
import warnings
from pathlib import Path

_INSTALLED = False
_REPO_ROOT = Path(__file__).resolve().parents[1]


def install() -> None:
    """在 tracker 首次启动前换上安静版清理逻辑。"""
    global _INSTALLED
    if os.name == "nt" or _INSTALLED:
        return
    from multiprocessing import resource_tracker as rt

    if getattr(rt.ResourceTracker.ensure_running, "_ntq_quiet", False):
        _INSTALLED = True
        return
    rt.ResourceTracker.ensure_running = _ensure_running
    _INSTALLED = True


def main(fd: int) -> None:
    """跟踪器子进程：读注册表，退出时 unlink 残留段，ENOENT 不打印。"""
    from multiprocessing.resource_tracker import _CLEANUP_FUNCS, _HAVE_SIGMASK, _IGNORED_SIGNALS

    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    if _HAVE_SIGMASK:
        signal.pthread_sigmask(signal.SIG_UNBLOCK, _IGNORED_SIGNALS)

    for stream in (sys.stdin, sys.stdout):
        try:
            stream.close()
        except Exception:
            pass

    cache = {rtype: set() for rtype in _CLEANUP_FUNCS.keys()}
    try:
        with open(fd, "rb") as handle:
            for line in handle:
                try:
                    cmd, name, rtype = line.strip().decode("ascii").split(":")
                    if rtype not in _CLEANUP_FUNCS:
                        continue
                    if cmd == "REGISTER":
                        cache[rtype].add(name)
                    elif cmd == "UNREGISTER":
                        cache[rtype].discard(name)
                except Exception:
                    pass
    finally:
        for rtype, names in cache.items():
            cleanup = _CLEANUP_FUNCS.get(rtype)
            if cleanup is None:
                continue
            for name in list(names):
                try:
                    cleanup(name)
                except FileNotFoundError:
                    pass
                except Exception:
                    pass


def _ensure_running(self) -> None:
    """与标准库相同的拉起方式，子进程改为运行本模块的 ``main``。"""
    from multiprocessing import resource_tracker as rt
    from multiprocessing import spawn, util

    with self._lock:
        if self._fd is not None:
            if self._check_alive():
                return
            os.close(self._fd)
            try:
                if self._pid is not None:
                    os.waitpid(self._pid, 0)
            except ChildProcessError:
                pass
            self._fd = None
            self._pid = None
            warnings.warn(
                "resource_tracker: process died unexpectedly, "
                "relaunching.  Some resources might leak."
            )

        fds_to_pass = []
        try:
            fds_to_pass.append(sys.stderr.fileno())
        except Exception:
            pass
        code = (
            "import sys; sys.path.insert(0, {root!r}); "
            "from core.quiet_resource_tracker import main; main({fd})"
        )
        read_fd, write_fd = os.pipe()
        try:
            fds_to_pass.append(read_fd)
            exe = spawn.get_executable()
            args = [exe] + util._args_from_interpreter_flags()
            args += ["-c", code.format(root=str(_REPO_ROOT), fd=read_fd)]
            try:
                if rt._HAVE_SIGMASK:
                    signal.pthread_sigmask(signal.SIG_BLOCK, rt._IGNORED_SIGNALS)
                pid = util.spawnv_passfds(exe, args, fds_to_pass)
            finally:
                if rt._HAVE_SIGMASK:
                    signal.pthread_sigmask(signal.SIG_UNBLOCK, rt._IGNORED_SIGNALS)
        except Exception:
            os.close(write_fd)
            raise
        else:
            self._fd = write_fd
            self._pid = pid
        finally:
            os.close(read_fd)


_ensure_running._ntq_quiet = True  # type: ignore[attr-defined]
