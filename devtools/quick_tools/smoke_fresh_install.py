#!/usr/bin/env python3
"""
模拟用户从源码 zip 冷启动：``install.py`` → ``cli.py se``。

用法（在已解压的项目根目录）::

    python devtools/quick_tools/smoke_fresh_install.py

CI 会先 ``git archive`` 解压到临时目录再调用本脚本。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from devtools.quick_tools._paths import REPO_ROOT

DEFAULT_STRATEGY = "demo/random/random_v1_null_baseline"


def _venv_python(root: Path) -> Path:
    if sys.platform == "win32":
        return root / "venv" / "Scripts" / "python.exe"
    return root / "venv" / "bin" / "python"


def _run(cmd: list[str], *, cwd: Path, label: str) -> int:
    print(f"[smoke] {label}: {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd, cwd=str(cwd))
    if proc.returncode != 0:
        print(f"[smoke] ❌ {label} 失败 (exit={proc.returncode})", flush=True)
    return int(proc.returncode)


def smoke_fresh_install(
    *,
    repo_root: Path,
    strategy: str = DEFAULT_STRATEGY,
    install_python: str | None = None,
) -> int:
    root = repo_root.resolve()
    if not (root / "install.py").is_file():
        print(f"[smoke] ❌ 不是项目根目录（缺少 install.py）: {root}", flush=True)
        return 1
    if not (root / "setup" / "init_data" / "data_demo.zip").is_file():
        print("[smoke] ❌ 缺少 setup/init_data/data_demo.zip", flush=True)
        return 1

    py = install_python or sys.executable
    code = _run([py, "install.py"], cwd=root, label="CLI 安装")
    if code != 0:
        return code

    vpy = _venv_python(root)
    cli_py = vpy if vpy.is_file() else Path(py)
    code = _run(
        [str(cli_py), "cli.py", "se", "--strategy", strategy],
        cwd=root,
        label=f"策略枚举 ({strategy})",
    )
    if code == 0:
        print("[smoke] ✅ 冷启动冒烟通过", flush=True)
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fresh install smoke (install.py → cli -se)")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="项目根目录（默认：本仓库根）",
    )
    parser.add_argument(
        "-s",
        "--strategy",
        default=DEFAULT_STRATEGY,
        help=f"枚举策略路径（默认 {DEFAULT_STRATEGY}）",
    )
    args = parser.parse_args(argv)
    return smoke_fresh_install(repo_root=args.repo_root, strategy=args.strategy)


if __name__ == "__main__":
    raise SystemExit(main())
