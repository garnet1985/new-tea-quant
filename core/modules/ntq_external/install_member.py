"""从官网拉取会员安装数据包（分卷；需本地会员凭证）。"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request

from core.modules.ntq_external.conf.site_target import (
    install_member_meta_url,
    install_member_part_url,
)
from core.infra.utils.core.net.ssl_context import urlopen_https

logger = logging.getLogger(__name__)

MEMBER_MANIFEST_NAME = "data_member_3y.manifest.json"
_DEFAULT_TIMEOUT_SEC = 180
_USER_AGENT = "NTQ/install-member"
_CHUNK_SIZE = 64 * 1024

# on_progress(done_bytes, total_bytes, *, parts_done=0, parts_total=0)
ProgressCallback = Callable[..., None]


class InstallMemberError(RuntimeError):
    """会员安装包下载或校验失败。"""


def resolve_install_member_meta_url() -> str:
    override = str(os.environ.get("NTQ_INSTALL_MEMBER_META_URL") or "").strip()
    return override or install_member_meta_url()


def resolve_install_member_part_url(part_index: int) -> str:
    template = str(os.environ.get("NTQ_INSTALL_MEMBER_PART_URL") or "").strip()
    if template:
        return template.format(n=int(part_index))
    return install_member_part_url(part_index)


def fetch_install_member_meta(*, timeout_sec: float = 30.0) -> Dict[str, Any]:
    """拉取会员包 manifest；401/失败抛 ``InstallMemberError``。"""
    url = resolve_install_member_meta_url()
    try:
        raw = _http_get_bytes(url, timeout_sec=timeout_sec, auth=True)
    except InstallMemberError:
        raise
    except Exception as exc:
        raise InstallMemberError(f"无法读取会员包元数据: {url}") from exc
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InstallMemberError(f"会员包元数据不是合法 JSON: {url}") from exc
    if not isinstance(data, dict):
        raise InstallMemberError(f"会员包元数据格式错误: {url}")
    parts = data.get("parts")
    if not isinstance(parts, list) or not parts:
        raise InstallMemberError("会员包元数据缺少 parts")
    return data


def list_member_part_files(dest_dir: Path, meta: Optional[Dict[str, Any]] = None) -> List[Path]:
    """按 manifest（或目录扫描）列出本地分卷。"""
    dest_dir = Path(dest_dir)
    if meta and isinstance(meta.get("parts"), list):
        out: List[Path] = []
        for part in meta["parts"]:
            if not isinstance(part, dict):
                continue
            name = str(part.get("file") or "").strip()
            if not name or "/" in name or "\\" in name or ".." in name:
                continue
            out.append(dest_dir / name)
        return out
    return sorted(dest_dir.glob("data_member_3y_part*.zip"))


def member_parts_complete(dest_dir: Path, meta: Optional[Dict[str, Any]] = None) -> bool:
    """本地分卷是否齐全且（有 sha 时）校验通过。"""
    dest_dir = Path(dest_dir)
    if meta is None:
        manifest = dest_dir / MEMBER_MANIFEST_NAME
        if not manifest.is_file():
            return False
        try:
            meta = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
    if not isinstance(meta, dict):
        return False
    parts = meta.get("parts")
    if not isinstance(parts, list) or not parts:
        return False
    for part in parts:
        if not isinstance(part, dict):
            return False
        name = str(part.get("file") or "").strip()
        path = dest_dir / name
        if not path.is_file():
            return False
        expected_sha = str(part.get("sha256") or "").strip().lower()
        expected_size = part.get("size_bytes")
        try:
            size = path.stat().st_size
        except OSError:
            return False
        if expected_size is not None:
            try:
                if size != int(expected_size):
                    return False
            except (TypeError, ValueError):
                pass
        if expected_sha:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected_sha:
                return False
    return True


def download_install_member(
    dest_dir: Path,
    *,
    force: bool = False,
    timeout_sec: float = _DEFAULT_TIMEOUT_SEC,
    on_progress: Optional[ProgressCallback] = None,
) -> Path:
    """
    确保 ``dest_dir`` 下会员分卷齐全。

    已齐全且 ``force=False`` 时直接返回目录；否则按 manifest 拉取缺失/校验失败的分卷。
    返回 ``dest_dir``。
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    meta = fetch_install_member_meta(timeout_sec=min(30.0, timeout_sec))
    manifest_path = dest_dir / MEMBER_MANIFEST_NAME
    _atomic_write(
        manifest_path,
        (json.dumps(meta, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )

    if not force and member_parts_complete(dest_dir, meta):
        logger.info("会员数据包本地已齐全: %s", dest_dir)
        return dest_dir

    parts = meta.get("parts") if isinstance(meta.get("parts"), list) else []
    parts_total = sum(1 for part in parts if isinstance(part, dict))
    total_bytes = 0
    for part in parts:
        if isinstance(part, dict):
            try:
                total_bytes += max(0, int(part.get("size_bytes") or 0))
            except (TypeError, ValueError):
                pass

    done_bytes = 0
    parts_done = 0

    def _emit(done: int, total: Optional[int], completed_parts: int) -> None:
        if on_progress is None:
            return
        on_progress(
            done,
            total,
            parts_done=completed_parts,
            parts_total=parts_total,
        )

    for part in parts:
        if not isinstance(part, dict):
            continue
        name = str(part.get("file") or "").strip()
        index = int(part.get("index") or 0)
        if not name or index < 1:
            raise InstallMemberError(f"会员包分卷声明无效: {part!r}")
        target = dest_dir / name
        expected_sha = str(part.get("sha256") or "").strip().lower()
        expected_size = 0
        try:
            expected_size = int(part.get("size_bytes") or 0)
        except (TypeError, ValueError):
            expected_size = 0

        if (
            not force
            and target.is_file()
            and (expected_size <= 0 or target.stat().st_size == expected_size)
            and (
                not expected_sha
                or hashlib.sha256(target.read_bytes()).hexdigest() == expected_sha
            )
        ):
            done_bytes += expected_size if expected_size > 0 else target.stat().st_size
            parts_done += 1
            _emit(done_bytes, total_bytes or None, parts_done)
            continue

        url = resolve_install_member_part_url(index)
        logger.info("下载会员分卷 %s → %s", name, target)

        def _part_progress(
            read: int,
            _total: Optional[int],
            *,
            base=done_bytes,
            completed=parts_done,
        ) -> None:
            _emit(base + read, total_bytes or None, completed)

        try:
            payload = _http_get_bytes(
                url,
                timeout_sec=timeout_sec,
                auth=True,
                on_progress=_part_progress,
                content_length_hint=expected_size or None,
            )
        except InstallMemberError:
            raise
        except Exception as exc:
            raise InstallMemberError(f"下载会员分卷失败: {url}") from exc

        if not payload.startswith(b"PK"):
            raise InstallMemberError(f"会员分卷不是 zip: {name}")
        if expected_sha:
            actual = hashlib.sha256(payload).hexdigest()
            if actual != expected_sha:
                raise InstallMemberError(
                    f"会员分卷校验失败（sha256）: {name}"
                )
        _atomic_write(target, payload)
        done_bytes += len(payload)
        parts_done += 1
        _emit(done_bytes, total_bytes or None, parts_done)

    if not member_parts_complete(dest_dir, meta):
        raise InstallMemberError("会员分卷下载后仍不完整，请重试")
    return dest_dir


def _auth_headers() -> Dict[str, str]:
    from core.infra.membership import Membership

    token = Membership.read()
    if not token:
        raise InstallMemberError(
            "未装载会员凭证。请先到「设置 → 会员」装载凭证后再导入全市场数据。"
        )
    return {
        "Authorization": f"Bearer {token}",
        "User-Agent": _USER_AGENT,
        "Accept": "*/*",
    }


def _http_get_bytes(
    url: str,
    *,
    timeout_sec: float,
    auth: bool = False,
    on_progress: Optional[ProgressCallback] = None,
    content_length_hint: Optional[int] = None,
) -> bytes:
    headers = _auth_headers() if auth else {"User-Agent": _USER_AGENT}
    req = Request(url, headers=headers)
    try:
        with urlopen_https(req, timeout=timeout_sec) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            if int(status) != 200:
                raise InstallMemberError(f"HTTP {status}: {url}")
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
        if exc.code == 401:
            raise InstallMemberError(
                "会员凭证无效或已过期。请到「设置 → 会员」重新装载官网通用凭证。"
            ) from exc
        if exc.code == 404:
            raise InstallMemberError("会员数据包尚未在官网部署，请稍后再试。") from exc
        if exc.code == 429:
            raise InstallMemberError("请求过于频繁，请稍后再试。") from exc
        raise InstallMemberError(f"HTTP {exc.code}: {url}") from exc
    except URLError as exc:
        raise InstallMemberError(f"网络不可达: {url} ({exc.reason})") from exc


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
