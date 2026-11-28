"""安装包下载共用：原子写盘、HTTPS 拉取、zip/sha 校验。"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable, Dict, Mapping, Optional, Type
from urllib.error import HTTPError, URLError
from urllib.request import Request

from core.infra.utils import Utils

CHUNK_SIZE = 64 * 1024

# on_progress(read_bytes, total_or_none)
BytesProgress = Callable[[int, Optional[int]], None]


def atomic_write(path: Path, data: bytes) -> None:
    Utils.io.atomic_write_bytes(path, data)


def http_get_bytes(
    url: str,
    *,
    timeout_sec: float,
    headers: Optional[Mapping[str, str]] = None,
    on_progress: Optional[BytesProgress] = None,
    content_length_hint: Optional[int] = None,
    error_cls: Type[Exception] = RuntimeError,
    map_http_error: Optional[Callable[[HTTPError, str], Optional[Exception]]] = None,
) -> bytes:
    """GET 全文；失败抛 ``error_cls``（或 ``map_http_error`` 返回的异常）。"""
    req = Request(url, headers=dict(headers or {}))
    try:
        with Utils.net.urlopen_https(req, timeout=timeout_sec) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            if int(status) != 200:
                raise error_cls(f"HTTP {status}: {url}")
            header_len = resp.headers.get("Content-Length")
            total: Optional[int] = None
            if header_len and str(header_len).isdigit():
                total = int(header_len)
            elif content_length_hint and content_length_hint > 0:
                total = int(content_length_hint)

            chunks: list[bytes] = []
            read = 0
            while True:
                chunk = resp.read(CHUNK_SIZE)
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
        if map_http_error is not None:
            mapped = map_http_error(exc, url)
            if mapped is not None:
                raise mapped from exc
        raise error_cls(f"HTTP {exc.code}: {url}") from exc
    except URLError as exc:
        raise error_cls(f"网络不可达: {url} ({exc.reason})") from exc


def ensure_zip_payload(
    payload: bytes,
    *,
    error_cls: Type[Exception],
    not_zip_message: str,
    expected_sha: str = "",
    sha_mismatch_message: str = "",
) -> None:
    if not payload.startswith(b"PK"):
        raise error_cls(not_zip_message)
    sha = str(expected_sha or "").strip().lower()
    if not sha:
        return
    actual = hashlib.sha256(payload).hexdigest()
    if actual != sha:
        msg = sha_mismatch_message or (
            f"sha256 不匹配: expected={sha} actual={actual}"
        )
        raise error_cls(msg)


def default_user_agent(name: str) -> Dict[str, str]:
    return {"User-Agent": name}
