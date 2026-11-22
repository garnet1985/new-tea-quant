"""HTTPS 校验：优先用 certifi CA（规避 macOS 官方 Python 缺系统证书）。"""

from __future__ import annotations

import ssl
from functools import lru_cache


@lru_cache(maxsize=1)
def https_context() -> ssl.SSLContext:
    """返回带 CA 的默认上下文；无 certifi 时退回系统默认。"""
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())
