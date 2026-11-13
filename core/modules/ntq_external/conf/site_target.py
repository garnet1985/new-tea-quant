"""官网根地址：全应用只认这一个 ``base_url``。

来源（二选一）::
  1. ``userspace/system/config/membership.json`` 里的 ``base_url``
  2. 缺省则用 ``DEFAULT_BASE_URL``（生产官网）

其它路径（AI / profile / 注册页…）一律由 ``base_url()`` 拼出。
本机回环会规范成 ``127.0.0.1``（避免 ``localhost`` 走 IPv6 后 502）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlsplit, urlunsplit

from core.infra.project_context import ProjectContext

DEFAULT_BASE_URL = "https://www.new-tea.cn"
CONFIG_NAME = "membership.json"
CONFIG_KEY = "base_url"
_AI_SUFFIX = "/api/v1/ntq-ai"


def base_url() -> str:
    """当前官网根地址（无末尾 /）。"""
    configured = _clean_http(str(_read_config().get(CONFIG_KEY) or ""))
    return configured or DEFAULT_BASE_URL


def ai_base_url() -> str:
    """会员 AI 根地址：``{base_url}/api/v1/ntq-ai``。"""
    return f"{base_url()}{_AI_SUFFIX}"


def member_profile_url() -> str:
    return f"{base_url()}/api/v1/ntq-member/profile"


def install_demo_url() -> str:
    """公开演示安装包 zip（无需会员凭证）。"""
    return f"{base_url()}/api/v1/ntq-data/install/demo"


def install_demo_meta_url() -> str:
    """演示安装包元数据（sha256 / 日期窗等）。"""
    return f"{base_url()}/api/v1/ntq-data/install/demo/meta"


def install_member_meta_url() -> str:
    """会员安装包 manifest（需 Bearer 凭证）。"""
    return f"{base_url()}/api/v1/ntq-data/install/member/meta"


def install_member_part_url(part_index: int) -> str:
    """会员安装包分卷（需 Bearer 凭证；``part_index`` 从 1 起）。"""
    n = int(part_index)
    return f"{base_url()}/api/v1/ntq-data/install/member/part/{n}"


def register_url() -> str:
    return f"{base_url()}/zh-hans/user/register"


def feedback_url() -> str:
    return f"{base_url()}/api/v1/feedback"


def trace_url() -> str:
    return f"{base_url()}/api/v1/traces"


def contact_url() -> str:
    return f"{base_url()}/zh-hans/contact?from=ntq_app"


def docs_url() -> str:
    """文档总入口（主 nav 外链）。"""
    return f"{base_url()}/zh-hans/docs"


def disclaimer_url() -> str:
    return f"{base_url()}/zh-hans/disclaimer"


def license_url() -> str:
    return f"{base_url()}/zh-hans/ntq-license"


def doc_url(slug: str) -> str:
    return f"{base_url()}/zh-hans/{slug}"


def _config_path() -> Path:
    return ProjectContext.path.get_user_config_root() / CONFIG_NAME


def _read_config() -> Dict[str, Any]:
    path = _config_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _clean_http(value: str) -> str:
    text = str(value or "").strip().rstrip("/")
    if not (text.startswith("http://") or text.startswith("https://")):
        return ""
    return _prefer_ipv4_loopback(text)


def _prefer_ipv4_loopback(url: str) -> str:
    """``localhost`` / ``::1`` → ``127.0.0.1``。"""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if host not in ("localhost", "::1"):
        return url.rstrip("/")
    port = parts.port
    netloc = "127.0.0.1" if port is None else f"127.0.0.1:{port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment)).rstrip("/")
