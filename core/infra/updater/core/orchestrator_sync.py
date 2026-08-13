"""把编排源码拷到运行时目录（userspace/system/updater）。

源码在 ``core/infra/updater/core/orchestrator/``；升级过程中必须跑拷贝，
不能 import 本包内的 pipeline（core 正在被镜像覆盖）。
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Sequence

ORCHESTRATOR_SRC = Path(__file__).resolve().parent / "orchestrator"
RUNTIME_FILES: Sequence[str] = (
    "pipeline.py",
    "helper.py",
    "run_apply.py",
    "upgrade_entry.py",
    "README.md",
)


def sync_orchestrator(dest: Path) -> List[str]:
    """用编排源码覆盖 ``dest``（通常为 ``userspace/system/updater``）。不含 ``__test__``。"""
    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    notes: List[str] = []
    for name in RUNTIME_FILES:
        src = ORCHESTRATOR_SRC / name
        if not src.is_file():
            continue
        out = dest / name
        shutil.copy2(src, out)
        notes.append(str(out))
    return notes
