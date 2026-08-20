"""NTQ UI / workbench 进程清理：进程组与 multiprocessing 子进程。

Windows 没有 ``os.getpgid`` / ``os.killpg``；Ctrl+C 必须用 ``taskkill /T``
才能杀掉 ProcessPool 子进程，否则 PowerShell 会卡死。
"""

from __future__ import annotations

import logging
import multiprocessing as mp
import os
import signal
import subprocess
import sys
import threading
import time
from typing import Iterable, List

logger = logging.getLogger(__name__)

_INTERRUPT_LOCK = threading.Lock()
_INTERRUPT_INSTALLED = False
_INTERRUPT_EXITING = False
_INTERRUPT_REQUESTED = False


def interrupt_requested() -> bool:
    """Ctrl+C 已触发（供等待循环尽快退出，勿再睡满超时）。"""
    return _INTERRUPT_REQUESTED


def request_interrupt() -> None:
    global _INTERRUPT_REQUESTED
    _INTERRUPT_REQUESTED = True


def kill_process_group(pid: int, *, grace_sec: float = 5.0) -> None:
    """结束 ``pid`` 及其子进程。Unix 用进程组信号；Windows 用 ``taskkill /T``。"""
    if pid <= 0:
        return
    if os.name == "nt":
        _kill_windows_tree(pid, grace_sec=grace_sec)
        return
    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        return
    except AttributeError:
        _signal_pid(pid, signal.SIGTERM)
        if not _wait_pid(pid, grace_sec):
            _signal_pid(pid, signal.SIGKILL)
        return
    try:
        own_pgid = os.getpgid(os.getpid())
    except ProcessLookupError:
        own_pgid = None
    if own_pgid is not None and pgid == own_pgid:
        _signal_pid(pid, signal.SIGTERM)
        _wait_pid(pid, grace_sec)
        _signal_pid(pid, signal.SIGKILL)
        return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            return
        except PermissionError:
            _signal_pid(pid, sig)
        if sig == signal.SIGTERM:
            if _wait_pid(pid, grace_sec):
                return
            time.sleep(0.2)


def _kill_windows_tree(pid: int, *, grace_sec: float) -> None:
    """``taskkill /T`` 杀掉整棵进程树（含 ProcessPool worker）。"""
    if pid <= 0:
        return
    # 中断路径 grace 很短：直接 /F，避免先软杀再等
    force_first = float(grace_sec) <= 0.2
    if force_first:
        _run_taskkill(pid, force=True, timeout_sec=3.0)
        return
    _run_taskkill(pid, force=False)
    if _wait_pid(pid, max(0.2, float(grace_sec))):
        return
    _run_taskkill(pid, force=True)


def _run_taskkill(pid: int, *, force: bool, timeout_sec: float = 15.0) -> None:
    cmd = ["taskkill", "/T", "/PID", str(pid)]
    if force:
        cmd.insert(1, "/F")
    try:
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=max(1.0, float(timeout_sec)),
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("taskkill pid=%s force=%s: %s", pid, force, exc)
        if force:
            _signal_pid(pid, signal.SIGTERM)


def _signal_pid(pid: int, sig: signal.Signals) -> None:
    try:
        os.kill(pid, sig)
    except (ProcessLookupError, OSError, AttributeError):
        pass


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            proc = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            try:
                os.kill(pid, 0)
            except OSError:
                return False
            return True
        out = proc.stdout or ""
        return str(pid) in out and "No tasks" not in out and "没有" not in out
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _wait_pid(pid: int, timeout_sec: float) -> bool:
    deadline = time.monotonic() + max(0.0, float(timeout_sec))
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return True
        time.sleep(0.1)
    return not _pid_alive(pid)


def terminate_multiprocessing_children(*, grace_sec: float = 3.0) -> None:
    """终止当前 Python 进程下的 ``multiprocessing`` 活跃子进程（ProcessPool worker 等）。"""
    children = [p for p in mp.active_children() if p.is_alive()]
    if not children:
        return
    for proc in children:
        try:
            proc.terminate()
        except Exception as exc:
            logger.debug("terminate child %s: %s", proc.name, exc)
        if os.name == "nt":
            try:
                # 中断路径：立刻 taskkill，勿先睡满 grace
                _kill_windows_tree(int(proc.pid), grace_sec=min(0.15, max(0.0, float(grace_sec))))
            except Exception as exc:
                logger.debug("taskkill child %s: %s", proc.name, exc)
    deadline = time.monotonic() + max(0.0, float(grace_sec))
    while time.monotonic() < deadline:
        if not any(p.is_alive() for p in children):
            return
        time.sleep(0.05)
    for proc in children:
        if not proc.is_alive():
            continue
        try:
            proc.kill()
        except Exception as exc:
            logger.debug("kill child %s: %s", proc.name, exc)
        if os.name == "nt":
            try:
                _kill_windows_tree(int(proc.pid), grace_sec=0.05)
            except Exception as exc:
                logger.debug("taskkill child %s: %s", proc.name, exc)


def kill_pids_with_process_groups(pids: Iterable[int], *, grace_sec: float = 5.0) -> int:
    killed = 0
    seen: set[int] = set()
    for pid in pids:
        if pid in seen:
            continue
        seen.add(pid)
        kill_process_group(pid, grace_sec=grace_sec)
        killed += 1
    return killed


def pids_listening_on(port: int) -> List[int]:
    """监听 ``port`` 的 PID 列表（Unix: lsof；Windows: netstat）。"""
    if port <= 0:
        return []
    if os.name == "nt":
        return _pids_listening_on_windows(port)
    try:
        out = subprocess.run(
            ["lsof", "-ti", f":{port}", "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
            check=False,
            timeout=8,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []
    return [int(line) for line in out.stdout.splitlines() if line.strip().isdigit()]


def _pids_listening_on_windows(port: int) -> List[int]:
    try:
        out = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            check=False,
            timeout=8,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []
    found: List[int] = []
    seen: set[int] = set()
    port_s = str(int(port))
    for raw in (out.stdout or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        upper = line.upper()
        if "LISTENING" not in upper and "LISTEN" not in upper:
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        local = parts[1] if parts[0].upper() == "TCP" else parts[0]
        host, sep, local_port = local.rpartition(":")
        if not sep:
            continue
        local_port = local_port.strip("]")
        if local_port != port_s:
            continue
        try:
            pid = int(parts[-1])
        except ValueError:
            continue
        if pid > 0 and pid not in seen:
            seen.add(pid)
            found.append(pid)
    return found


def process_cmdline(pid: int) -> str:
    if pid <= 0:
        return ""
    if os.name == "nt":
        return _process_cmdline_windows(pid)
    try:
        out = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return ""
    return (out.stdout or "").strip()


def _process_cmdline_windows(pid: int) -> str:
    try:
        out = subprocess.run(
            [
                "wmic",
                "process",
                "where",
                f"ProcessId={pid}",
                "get",
                "CommandLine",
                "/value",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=8,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return ""
    for line in (out.stdout or "").splitlines():
        if line.lower().startswith("commandline="):
            return line.split("=", 1)[1].strip()
    return ""


def windows_new_process_group_flag() -> int:
    """``subprocess.Popen`` 用：子进程不吃控制台 Ctrl+C，由父进程 ``taskkill``。"""
    if os.name != "nt":
        return 0
    return int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) or 0)


def _force_exit_now(code: int = 130) -> None:
    """立刻杀子进程并 ``os._exit``；handler / 等待循环共用，禁止长阻塞。"""
    global _INTERRUPT_EXITING
    request_interrupt()
    if _INTERRUPT_EXITING:
        os._exit(code)
    _INTERRUPT_EXITING = True
    try:
        sys.stderr.write("\n收到中断，正在结束子进程…\n")
        sys.stderr.flush()
    except Exception:
        pass
    try:
        # grace≈0：Windows 上 taskkill 后不再睡满数百毫秒
        terminate_multiprocessing_children(grace_sec=0.05)
    except Exception:
        pass
    os._exit(code)


def install_interrupt_force_exit() -> None:
    """Ctrl+C / Ctrl+Break：杀掉 multiprocessing 子进程后 ``os._exit``。

    禁止在 signal handler 里做 DuckDB CHECKPOINT：查询或 ProcessPool
    占用文件锁时会永久卡死，Windows PowerShell 表现为无法退出。
    等待 ``wait_for_main`` 等循环会读 ``interrupt_requested()``，勿再睡满超时。
    """
    global _INTERRUPT_INSTALLED
    if threading.current_thread() is not threading.main_thread():
        return
    with _INTERRUPT_LOCK:
        if _INTERRUPT_INSTALLED:
            return

        def _handler(signum, frame) -> None:  # noqa: ARG001
            _force_exit_now(130)

        signal.signal(signal.SIGINT, _handler)
        sigbreak = getattr(signal, "SIGBREAK", None)
        if sigbreak is not None:
            try:
                signal.signal(sigbreak, _handler)
            except (OSError, ValueError, AttributeError):
                pass
        if os.name == "nt":
            _install_windows_console_ctrl_handler()
        _INTERRUPT_INSTALLED = True


def _install_windows_console_ctrl_handler() -> None:
    """Windows：控制台 Ctrl+C 可能不走 Python SIGINT，补 ``SetConsoleCtrlHandler``。"""
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return

    HandlerRoutine = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)

    @HandlerRoutine
    def _console_handler(ctrl_type: int) -> bool:
        # 0=CTRL_C_EVENT 1=CTRL_BREAK_EVENT 2=CTRL_CLOSE_EVENT
        if ctrl_type in (0, 1, 2):
            # 控制台回调在独立线程；直接强制退出，避免卡在主线程 C 层 wait
            _force_exit_now(130)
            return True
        return False

    try:
        # 保持引用，避免被 GC
        install_interrupt_force_exit._win_ctrl_handler = _console_handler  # type: ignore[attr-defined]
        ctypes.windll.kernel32.SetConsoleCtrlHandler(_console_handler, True)
    except Exception as exc:
        logger.debug("SetConsoleCtrlHandler: %s", exc)


def interrupt_force_exit_installed() -> bool:
    return _INTERRUPT_INSTALLED
