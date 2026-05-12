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
import shutil
import sys
import tempfile
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


def _is_userspace_structure_ready(target: Path) -> bool:
    # 最小完整性检查：后续 db_connection 必须依赖该文件。
    required = target / "config" / "database" / "common.json"
    return required.is_file()


def _extract_zip(zip_path: Path, target: Path) -> None:
    if target.exists():
        raise RuntimeError(f"目标路径已存在，请先清理后重试: {target}")

    # 先解压到临时目录，便于做结构归一化（拍平 userspace/ 外层目录）并过滤 macOS 垃圾目录。
    with tempfile.TemporaryDirectory(prefix="ntq_userspace_") as td:
        tmp_root = Path(td)
        with zipfile.ZipFile(zip_path, "r") as zf:
            valid_members = []
            for info in zf.infolist():
                name = info.filename
                if not name:
                    continue
                parts = Path(name).parts
                if "__MACOSX" in parts:
                    continue
                if any(part.startswith("._") for part in parts):
                    continue
                valid_members.append(info)
            zf.extractall(tmp_root, members=valid_members)

        # 兼容 userspace.zip 中以 userspace/ 作为外层目录的打包方式，自动拍平。
        inner_root = tmp_root / "userspace"
        source_root = inner_root if inner_root.exists() else tmp_root

        target.mkdir(parents=True, exist_ok=True)
        for child in source_root.iterdir():
            shutil.move(str(child), str(target / child.name))


def main() -> int:
    target_path = os.getenv("NTQ_USERSPACE_TARGET_PATH", "")
    conflict_policy = os.getenv("NTQ_USERSPACE_CONFLICT_POLICY", "skip").strip().lower() or "skip"
    if conflict_policy not in ("skip", "overwrite"):
        conflict_policy = "skip"
    zip_path = _resolve_zip()
    target = _safe_target_path(target_path)
    if target.exists():
        if conflict_policy == "skip":
            if not _is_userspace_structure_ready(target):
                raise RuntimeError(
                    "目标路径已存在，但不是可用的 userspace 结构（缺少 config/database/common.json）。"
                    f"请改用“覆盖”或清理后重试: {target}"
                )
            NewTeaQuantSetup.print_check_item("warn", f"目标路径已存在，按策略跳过解压: {target}")
            _write_userspace_state(target)
            NewTeaQuantSetup.print_check_ok(f"userspace 初始化完成（跳过覆盖）: {target}")
            NewTeaQuantSetup.print_check_info(f"userspace 路径状态已写入: {STATE_FILE}")
            return 0
        if conflict_policy == "overwrite":
            NewTeaQuantSetup.print_check_item("warn", f"目标路径已存在，按策略覆盖: {target}")
            shutil.rmtree(target)

    _extract_zip(zip_path, target)
    _write_userspace_state(target)
    NewTeaQuantSetup.print_check_ok(f"userspace 初始化完成: {target}")
    NewTeaQuantSetup.print_check_info(f"userspace 路径状态已写入: {STATE_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
