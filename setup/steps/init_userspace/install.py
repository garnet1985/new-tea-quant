#!/usr/bin/env python3
"""
安装流程步骤：初始化 userspace 目录。

行为：
- 从 setup/init_userspace 自动读取唯一 zip 包（没有或有多个都报错）
- 解压到目标目录（默认 <repo>/userspace）
- 写入 .ntq/userspace-path.json 供 ProjectContext 读取
"""
from __future__ import annotations

import json
import os
import sys
import zipfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from setup.setup import NewTeaQuantSetup

NewTeaQuantSetup.ensure_venv_for_setup_step(__file__)

INIT_USERSPACE_DIR = _REPO_ROOT / "setup" / "init_userspace"
STATE_FILE = _REPO_ROOT / ".ntq" / "userspace-path.json"


def _default_target_path() -> Path:
    return (_REPO_ROOT / "userspace").resolve()


def _safe_target_path(raw: str | None) -> Path:
    if not raw or not str(raw).strip():
        return _default_target_path()
    return Path(raw).expanduser().resolve()


def _resolve_zip() -> Path:
    zip_files = sorted(INIT_USERSPACE_DIR.glob("*.zip"))
    if not zip_files:
        raise FileNotFoundError(f"未找到 userspace zip，请放置到: {INIT_USERSPACE_DIR}")
    if len(zip_files) > 1:
        names = ", ".join(p.name for p in zip_files)
        raise RuntimeError(f"init_userspace 下检测到多个 zip，请只保留一个: {names}")
    return zip_files[0]


def _write_userspace_state(userspace_path: Path) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "userspacePath": str(userspace_path),
    }
    STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _extract_zip(zip_path: Path, target: Path) -> None:
    if target.exists():
        raise RuntimeError(f"目标路径已存在，请先清理后重试: {target}")
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(target)


def main() -> int:
    target_path = os.getenv("NTQ_USERSPACE_TARGET_PATH", "")
    zip_path = _resolve_zip()
    target = _safe_target_path(target_path)
    _extract_zip(zip_path, target)
    _write_userspace_state(target)
    NewTeaQuantSetup.print_check_ok(f"userspace 初始化完成: {target}")
    NewTeaQuantSetup.print_check_info(f"userspace 路径状态已写入: {STATE_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
