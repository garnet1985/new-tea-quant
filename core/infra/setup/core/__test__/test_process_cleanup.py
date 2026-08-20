"""Windows / Unix 进程清理：Ctrl+C 必须能杀掉进程树。"""

from __future__ import annotations

import os
import subprocess

import pytest

from core.ui.process_cleanup import (
    interrupt_requested,
    kill_process_group,
    pids_listening_on,
    request_interrupt,
    windows_new_process_group_flag,
)

pytestmark = pytest.mark.force_run


def test_kill_process_group_windows_uses_taskkill(monkeypatch) -> None:
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(
        "core.ui.process_cleanup._wait_pid",
        lambda pid, timeout_sec: True,
    )
    kill_process_group(4242, grace_sec=0.1)
    assert calls
    assert calls[0][0] == "taskkill"
    assert "/PID" in calls[0]
    assert "4242" in calls[0]
    assert "/T" in calls[0]


def test_pids_listening_on_windows_does_not_match_prefix_port(monkeypatch) -> None:
    stdout = (
        "  TCP    127.0.0.1:8888     0.0.0.0:0    LISTENING    4242\n"
        "  TCP    127.0.0.1:88880    0.0.0.0:0    LISTENING    99\n"
    )

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout, "")

    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert pids_listening_on(8888) == [4242]


def test_windows_new_process_group_flag_nonzero_on_nt(monkeypatch) -> None:
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(
        subprocess,
        "CREATE_NEW_PROCESS_GROUP",
        0x00000200,
        raising=False,
    )
    assert windows_new_process_group_flag() == 0x00000200


def test_kill_process_group_unix_uses_killpg(monkeypatch) -> None:
    if os.name == "nt":
        pytest.skip("unix path")
    signals = []

    monkeypatch.setattr(os, "getpgid", lambda pid: 9000 if pid == 111 else 1)
    monkeypatch.setattr(
        os,
        "killpg",
        lambda pgid, sig: signals.append((pgid, sig)),
    )
    monkeypatch.setattr(
        "core.ui.process_cleanup._wait_pid",
        lambda pid, timeout_sec: True,
    )
    kill_process_group(111, grace_sec=0.1)
    assert signals
    assert signals[0][0] == 9000


def test_request_interrupt_sets_flag(monkeypatch) -> None:
    import core.ui.process_cleanup as pc

    monkeypatch.setattr(pc, "_INTERRUPT_REQUESTED", False)
    assert interrupt_requested() is False
    request_interrupt()
    assert interrupt_requested() is True
    monkeypatch.setattr(pc, "_INTERRUPT_REQUESTED", False)