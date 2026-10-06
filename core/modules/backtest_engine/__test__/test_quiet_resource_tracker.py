"""中断退出时，已删除的共享内存不再让 resource tracker 警告泄漏。"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.force_run

_REPO = Path(__file__).resolve().parents[4]


@pytest.mark.skipif(os.name == "nt", reason="POSIX resource tracker")
def test_shutdown_quiet_when_segments_already_unlinked() -> None:
    script = textwrap.dedent(
        """
        import _posixshmem
        from multiprocessing import resource_tracker
        from multiprocessing.shared_memory import SharedMemory

        from core.quiet_resource_tracker import install

        install()
        shm = SharedMemory(create=True, size=64)
        name = shm._name
        shm.close()
        _posixshmem.shm_unlink(name)

        live = SharedMemory(create=True, size=64)
        live_name = live._name
        live.close()
        resource_tracker._resource_tracker._stop()
        try:
            _posixshmem.shm_unlink(live_name)
        except FileNotFoundError:
            pass
        else:
            raise SystemExit("live segment was not reclaimed")
        """
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "leaked shared_memory" not in proc.stderr
    assert "/psm_" not in proc.stderr
