"""把官网下载能力接到 Setup（入口组装；setup 本身不 import 本模块）。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from core.infra.setup.core.shared.package_fetch import (
    PACKAGE_FETCHER_ENV,
    ProgressCallback,
    set_package_fetcher,
)

# install.py / 子进程步骤默认加载本 callable。
FETCHER_SPEC = "core.modules.ntq_external.setup_bridge:fetch_package"


def fetch_package(
    kind: str,
    dest_dir: Path,
    *,
    force: bool = False,
    on_progress: Optional[ProgressCallback] = None,
) -> Path:
    """``PackageFetcher``：demo / member 走官网下载实现。"""
    key = str(kind or "demo").strip().lower() or "demo"
    dest = Path(dest_dir)
    if key == "member":
        from core.modules.ntq_external.install_member import download_install_member

        return download_install_member(
            dest, force=force, on_progress=on_progress
        )
    from core.modules.ntq_external.install_demo import download_install_demo

    return download_install_demo(dest, force=force, on_progress=on_progress)


def wire_setup_package_fetcher() -> None:
    """进程内注入；并写入环境变量供安装子进程继承。"""
    os.environ.setdefault(PACKAGE_FETCHER_ENV, FETCHER_SPEC)
    set_package_fetcher(fetch_package)
