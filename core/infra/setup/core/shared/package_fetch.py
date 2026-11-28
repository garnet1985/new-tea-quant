"""可选数据包拉取钩子（由入口注入；setup 不依赖 ntq_external）。"""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Callable, Optional, Protocol

# 环境变量：``module:callable``，子进程安装步骤可读（install.py / CLI 设置）。
PACKAGE_FETCHER_ENV = "NTQ_SETUP_PACKAGE_FETCHER"

ProgressCallback = Callable[..., None]


class PackageFetcher(Protocol):
    """拉取指定 kind 的包到 dest_dir，返回主 zip 或 member 目录。"""

    def __call__(
        self,
        kind: str,
        dest_dir: Path,
        *,
        force: bool = False,
        on_progress: Optional[ProgressCallback] = None,
    ) -> Path: ...


_fetcher: Optional[PackageFetcher] = None


def set_package_fetcher(fetcher: Optional[PackageFetcher]) -> None:
    """进程内注册拉取函数；传 ``None`` 清除。"""
    global _fetcher
    _fetcher = fetcher


def get_package_fetcher() -> Optional[PackageFetcher]:
    """已注入的 fetcher；若无则尝试从 ``NTQ_SETUP_PACKAGE_FETCHER`` 加载一次。"""
    global _fetcher
    if _fetcher is not None:
        return _fetcher
    loaded = _load_fetcher_from_env()
    if loaded is not None:
        _fetcher = loaded
    return _fetcher


def _load_fetcher_from_env() -> Optional[PackageFetcher]:
    spec = str(os.environ.get(PACKAGE_FETCHER_ENV) or "").strip()
    if not spec or ":" not in spec:
        return None
    mod_name, _, attr = spec.partition(":")
    mod_name = mod_name.strip()
    attr = attr.strip()
    if not mod_name or not attr:
        return None
    try:
        mod = importlib.import_module(mod_name)
        fn = getattr(mod, attr, None)
    except Exception:
        return None
    if not callable(fn):
        return None
    return fn  # type: ignore[return-value]


def missing_package_message(kind: str, data_dir: Path) -> str:
    return (
        f"本地没有可用的 {kind} 数据包：{data_dir}\n"
        "请先放入 zip，或由入口注册下载器后重试"
        f"（环境变量 {PACKAGE_FETCHER_ENV}=module:callable）。"
    )
