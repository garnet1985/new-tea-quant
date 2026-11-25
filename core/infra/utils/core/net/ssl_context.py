"""HTTPS 校验：优先用 certifi CA（规避 macOS 官方 Python 缺系统证书）。"""

from __future__ import annotations

import ssl
import urllib.request
from functools import lru_cache
from typing import Any, Optional


@lru_cache(maxsize=1)
def https_context() -> ssl.SSLContext:
    """返回带 CA 的默认上下文；无 certifi 时退回系统默认。"""
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def urlopen_https(req: urllib.request.Request, *, timeout: Optional[float] = None, **kwargs: Any):
    """``urllib.request.urlopen``，HTTPS 一律挂上 ``https_context()``。"""
    if "context" not in kwargs:
        kwargs["context"] = https_context()
    return urllib.request.urlopen(req, timeout=timeout, **kwargs)
