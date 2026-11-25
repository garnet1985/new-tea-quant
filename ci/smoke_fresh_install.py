#!/usr/bin/env python3
"""
模拟用户从源码 zip 冷启动：``install.py`` → ``cli.py se``。

由 GitHub Actions job ``smoke-fresh-install`` 调用：先 ``git archive`` 解压到临时目录，再执行本脚本。

默认不写死策略名：安装后 ``list strategies --json``，取第一个已启用的 ``meta.key``
（无已启用则取列表第一个），避免 demo 改名导致 CI 挂掉。可用 ``--strategy`` 覆盖。

本地复现（项目根）::

    python ci/smoke_fresh_install.py
    python ci/smoke_fresh_install.py --strategy dual_ma
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from core.infra.cmd_layout import i

REPO_ROOT = _REPO


def _venv_python(root: Path) -> Path:
    if sys.platform == "win32":
        return root / "venv" / "Scripts" / "python.exe"
    return root / "venv" / "bin" / "python"


def _run(cmd: list[str], *, cwd: Path, label: str) -> int:
    print(f"[smoke] {label}: {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd, cwd=str(cwd))
    if proc.returncode != 0:
        print(f"[smoke] {i('error')} {label} 失败 (exit={proc.returncode})", flush=True)
    return int(proc.returncode)


def _first_strategy_key(cli_py: Path, root: Path) -> str | None:
    """安装后解析第一个可用策略 key（优先 is_enabled）。"""
    cmd = [str(cli_py), "cli.py", "list", "strategies", "--json"]
    print(f"[smoke] 解析策略列表: {' '.join(cmd)}", flush=True)
    proc = subprocess.run(
        cmd,
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        print(
            f"[smoke] {i('error')} 列出策略失败 (exit={proc.returncode})"
            + (f": {err}" if err else ""),
            flush=True,
        )
        return None
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        print(f"[smoke] {i('error')} 策略列表 JSON 无法解析: {exc}", flush=True)
        return None
    rows = payload.get("strategies") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        print(f"[smoke] {i('error')} 策略列表格式异常", flush=True)
        return None
    enabled = [
        str(row.get("key") or "").strip()
        for row in rows
        if isinstance(row, dict)
        and row.get("is_enabled")
        and str(row.get("key") or "").strip()
    ]
    any_keys = [
        str(row.get("key") or "").strip()
        for row in rows
        if isinstance(row, dict) and str(row.get("key") or "").strip()
    ]
    pick = (enabled or any_keys)
    if not pick:
        print(f"[smoke] {i('error')} 未发现任何策略", flush=True)
        return None
    key = pick[0]
    print(
        f"[smoke] 选用策略: {key}"
        + ("（首个已启用）" if enabled else "（首个可用，无已启用）"),
        flush=True,
    )
    return key


def smoke_fresh_install(
    *,
    repo_root: Path,
    strategy: str | None = None,
    install_python: str | None = None,
) -> int:
    root = repo_root.resolve()
    if not (root / "install.py").is_file():
        print(f"[smoke] {i('error')} 不是项目根目录（缺少 install.py）: {root}", flush=True)
        return 1
    py = install_python or sys.executable
    code = _run(
        [py, "install.py", "--accept-license"],
        cwd=root,
        label="CLI 安装",
    )
    if code != 0:
        return code

    vpy = _venv_python(root)
    cli_py = vpy if vpy.is_file() else Path(py)
    chosen = (strategy or "").strip() or _first_strategy_key(cli_py, root)
    if not chosen:
        return 1
    code = _run(
        [str(cli_py), "cli.py", "se", "--strategy", chosen],
        cwd=root,
        label=f"策略枚举 ({chosen})",
    )
    if code == 0:
        print(f"[smoke] {i('success')} 冷启动冒烟通过", flush=True)
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
        default=None,
        help="枚举策略 meta.key 或路径；省略则安装后取第一个已启用策略",
    )
    args = parser.parse_args(argv)
    return smoke_fresh_install(repo_root=args.repo_root, strategy=args.strategy)


if __name__ == "__main__":
    raise SystemExit(main())
