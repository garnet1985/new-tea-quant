"""从官网公开接口拉取安装用演示数据包（无需会员凭证）。"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from core.modules.ntq_external.conf.site_target import (
    install_demo_meta_url,
    install_demo_url,
)
from core.modules.ntq_external.install_http import (
    atomic_write,
    ensure_zip_payload,
    http_get_bytes,
)

logger = logging.getLogger(__name__)

GIT_DATA_ZIP_NAME = "data_demo.zip"
_DEFAULT_TIMEOUT_SEC = 120
_USER_AGENT = "NTQ/install-demo"

ProgressCallback = Callable[[int, Optional[int]], None]


class InstallDemoError(RuntimeError):
    """演示安装包下载或校验失败。"""


def resolve_install_demo_url() -> str:
    """安装包 URL；可用环境变量 ``NTQ_INSTALL_DEMO_URL`` 覆盖（本地联调）。"""
    override = str(os.environ.get("NTQ_INSTALL_DEMO_URL") or "").strip()
    return override or install_demo_url()


def resolve_install_demo_meta_url() -> str:
    override = str(os.environ.get("NTQ_INSTALL_DEMO_META_URL") or "").strip()
    return override or install_demo_meta_url()


def fetch_install_demo_meta(*, timeout_sec: float = 30.0) -> Dict[str, Any]:
    """拉取 meta JSON；失败抛 ``InstallDemoError``。"""
    url = resolve_install_demo_meta_url()
    try:
        raw = http_get_bytes(
            url,
            timeout_sec=timeout_sec,
            headers={"User-Agent": _USER_AGENT},
            error_cls=InstallDemoError,
        )
    except InstallDemoError:
        raise
    except Exception as exc:
        raise InstallDemoError(f"无法读取演示包元数据: {url}") from exc
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InstallDemoError(f"演示包元数据不是合法 JSON: {url}") from exc
    if not isinstance(data, dict):
        raise InstallDemoError(f"演示包元数据格式错误: {url}")
    return data


def download_install_demo(
    dest_dir: Path,
    *,
    force: bool = False,
    timeout_sec: float = _DEFAULT_TIMEOUT_SEC,
    show_progress: Optional[bool] = None,
    on_progress: Optional[ProgressCallback] = None,
) -> Path:
    """
    确保 ``dest_dir/data_demo.zip`` 存在。

    已存在且 ``force=False`` 时直接返回现有路径；否则从官网下载并可选校验 sha256。
    ``show_progress`` 默认：stdout 为 TTY 时显示下载进度。
    ``on_progress(read, total)`` 可选；``total`` 可能为 ``None``。
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / GIT_DATA_ZIP_NAME
    if target.is_file() and not force:
        return target

    url = resolve_install_demo_url()
    meta: Optional[Dict[str, Any]] = None
    try:
        meta = fetch_install_demo_meta(timeout_sec=min(30.0, timeout_sec))
    except InstallDemoError as exc:
        logger.info("演示包 meta 不可用，继续下载 zip: %s", exc)

    expected_sha = ""
    expected_bytes: Optional[int] = None
    if isinstance(meta, dict):
        expected_sha = str(meta.get("sha256") or "").strip().lower()
        for key in ("bytes", "size", "size_bytes"):
            raw = meta.get(key)
            if raw is None or raw == "":
                continue
            try:
                expected_bytes = int(raw)
            except (TypeError, ValueError):
                expected_bytes = None
            if expected_bytes is not None and expected_bytes > 0:
                break

    if show_progress is None:
        show_progress = sys.stdout.isatty()
    progress_cbs: list[ProgressCallback] = []
    if show_progress:
        progress_cbs.append(_print_download_progress)
    if on_progress is not None:
        progress_cbs.append(on_progress)

    def _emit(read: int, total: Optional[int]) -> None:
        for cb in progress_cbs:
            cb(read, total)

    emit: Optional[ProgressCallback] = _emit if progress_cbs else None

    logger.info("下载演示安装包: %s → %s", url, target)
    if show_progress:
        size_hint = f"（约 {expected_bytes / (1024 * 1024):.1f} MB）" if expected_bytes else ""
        print(f"  正在下载演示数据包{size_hint}…", flush=True)
    if emit is not None and expected_bytes:
        emit(0, expected_bytes)

    try:
        payload = http_get_bytes(
            url,
            timeout_sec=timeout_sec,
            headers={"User-Agent": _USER_AGENT},
            on_progress=emit,
            content_length_hint=expected_bytes,
            error_cls=InstallDemoError,
        )
    except InstallDemoError:
        if show_progress:
            print(flush=True)
        raise
    except Exception as exc:
        if show_progress:
            print(flush=True)
        raise InstallDemoError(f"下载演示安装包失败: {url}") from exc

    if show_progress:
        print(flush=True)

    ensure_zip_payload(
        payload,
        error_cls=InstallDemoError,
        not_zip_message=f"演示安装包不是 zip: {url}",
        expected_sha=expected_sha,
    )

    atomic_write(target, payload)
    if isinstance(meta, dict):
        meta_path = dest_dir / "data_demo.meta.json"
        atomic_write(
            meta_path,
            (json.dumps(meta, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        )
    return target


def _print_download_progress(read: int, total: Optional[int]) -> None:
    mb = read / (1024 * 1024)
    if total and total > 0:
        pct = min(100, int(read * 100 / total))
        total_mb = total / (1024 * 1024)
        line = f"\r  下载进度: {mb:.1f}/{total_mb:.1f} MB ({pct}%)"
    else:
        line = f"\r  下载进度: {mb:.1f} MB"
    sys.stdout.write(line)
    sys.stdout.flush()
