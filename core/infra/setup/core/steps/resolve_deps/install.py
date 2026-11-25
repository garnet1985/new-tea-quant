#!/usr/bin/env python3
"""
安装 Python 依赖（requirements.txt）。
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = next(
    p
    for p in Path(__file__).resolve().parents
    if (p / "install.py").is_file() and (p / "core" / "system.json").is_file()
)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.infra.setup.core.shared.env import NewTeaQuantSetup
from core.infra.utils import Utils

NewTeaQuantSetup.ensure_venv_for_setup_step(__file__)

_ONLY_BINARY = (
    "numpy,pandas,duckdb,psycopg2-binary,cffi,curl-cffi,lxml,mini-racer,psutil"
)
_PROBE_NAMES = ("numpy", "pandas", "duckdb")
# 3.11 / 3.12 轮子齐全，跳过探测省时间；3.13+ 再提前 dry-download。
_WHEEL_PROBE_MIN = (3, 13)


def _pin_from_requirements(req: Path, name: str) -> str | None:
    pattern = re.compile(rf"^{re.escape(name)}==(\S+)", re.IGNORECASE)
    for line in req.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        matched = pattern.match(text)
        if matched:
            return f"{name}=={matched.group(1)}"
    return None


def _should_probe_wheels() -> bool:
    return sys.version_info[:2] >= _WHEEL_PROBE_MIN


def _abort_if_wheels_missing(req: Path) -> int | None:
    """
    对强制二进制的核心包做一次 dry download。

    仅 Python 3.13+：新小版本常缺 cp3xy 轮子。3.11/3.12 跳过以节省时间。
    """
    if not _should_probe_wheels():
        return None

    pins = [_pin_from_requirements(req, name) for name in _PROBE_NAMES]
    pins = [p for p in pins if p]
    if not pins:
        return None

    with tempfile.TemporaryDirectory(prefix="ntq-wheel-probe-") as tmp:
        probe = Utils.pkg.run_pip(
            [
                "download",
                "--no-deps",
                "--only-binary",
                ":all:",
                "-d",
                tmp,
                *pins,
            ],
            cwd=str(_REPO_ROOT),
        )
    if probe == 0:
        return None

    ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(
        f"错误: 当前 Python {ver} 缺少 numpy/pandas/duckdb 的预编译轮子"
        f"（安装强制 --only-binary）。",
        file=sys.stderr,
    )
    print(
        "这是扩展模块 ABI/轮子问题：请改用已有轮子的解释器（建议 3.11 或 3.12），"
        "删除仓库根目录 venv/ 后重新安装。",
        file=sys.stderr,
    )
    return 1


def main() -> int:
    print(f"当前依赖安装解释器: {sys.executable}", file=sys.stderr)
    Utils.pkg.announce()

    if Utils.pkg.pip_meets_minimum((24, 0)):
        print("pip 已满足最低版本，跳过联网自升级。", file=sys.stderr)
    else:
        print("升级 pip …", file=sys.stderr)
        upgraded = Utils.pkg.run_pip(["install", "--upgrade", "pip"])
        if upgraded != 0 and not Utils.pkg.pip_meets_minimum((21, 0)):
            print(Utils.pkg.pip_hint(), file=sys.stderr)

    print("清除 pip cache …", file=sys.stderr)
    subprocess.run([sys.executable, "-m", "pip", "cache", "purge"], check=False)

    req = _REPO_ROOT / "requirements.txt"
    if not req.is_file():
        print(f"错误: 未找到 requirements.txt: {req}", file=sys.stderr)
        return 1

    early = _abort_if_wheels_missing(req)
    if early is not None:
        return early

    code = Utils.pkg.run_pip(
        [
            "install",
            "--no-compile",
            "--only-binary",
            _ONLY_BINARY,
            "-r",
            str(req),
        ],
        cwd=str(_REPO_ROOT),
    )
    if code != 0:
        ver = f"{sys.version_info.major}.{sys.version_info.minor}"
        print(
            f"依赖安装失败。若日志含 No matching distribution，多半是 Python {ver} "
            "尚无对应预编译包；请换 3.11/3.12 并删除 venv/ 后重试。",
            file=sys.stderr,
        )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
