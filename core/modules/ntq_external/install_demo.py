"""从官网公开接口拉取安装用演示数据包（无需会员凭证）。"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from core.modules.ntq_external.conf.site_target import (
    install_demo_meta_url,
    install_demo_url,
)

logger = logging.getLogger(__name__)

GIT_DATA_ZIP_NAME = "data_demo.zip"
_DEFAULT_TIMEOUT_SEC = 120
_USER_AGENT = "NTQ/install-demo"
_CHUNK_SIZE = 64 * 1024

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
        raw = _http_get_bytes(url, timeout_sec=timeout_sec)
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
        payload = _http_get_bytes(
            url,
            timeout_sec=timeout_sec,
            on_progress=emit,
            content_length_hint=expected_bytes,
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

    if not payload.startswith(b"PK"):
        raise InstallDemoError(f"演示安装包不是 zip: {url}")

    if expected_sha:
        actual = hashlib.sha256(payload).hexdigest()
        if actual != expected_sha:
            raise InstallDemoError(
                f"演示安装包校验失败（sha256 不匹配）: expected={expected_sha} actual={actual}"
            )

    _atomic_write(target, payload)
    if isinstance(meta, dict):
        meta_path = dest_dir / "data_demo.meta.json"
        _atomic_write(
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


def _http_get_bytes(
    url: str,
    *,
    timeout_sec: float,
    on_progress: Optional[ProgressCallback] = None,
    content_length_hint: Optional[int] = None,
) -> bytes:
    req = Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urlopen(req, timeout=timeout_sec) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            if int(status) != 200:
                raise InstallDemoError(f"HTTP {status}: {url}")
            header_len = resp.headers.get("Content-Length")
            total: Optional[int] = None
            if header_len and str(header_len).isdigit():
                total = int(header_len)
            elif content_length_hint and content_length_hint > 0:
                total = int(content_length_hint)

            chunks: list[bytes] = []
            read = 0
            while True:
                chunk = resp.read(_CHUNK_SIZE)
                if not chunk:
                    break
                chunks.append(chunk)
                read += len(chunk)
                if on_progress is not None:
                    on_progress(read, total)
            if on_progress is not None and read == 0:
                on_progress(0, total)
            return b"".join(chunks)
    except HTTPError as exc:
        raise InstallDemoError(f"HTTP {exc.code}: {url}") from exc
    except URLError as exc:
        raise InstallDemoError(f"网络不可达: {url} ({exc.reason})") from exc


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
