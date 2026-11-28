"""NtqExternal 包根 Facade：公开面仅为页面地址与 trace 发送端登记。"""

from .site import site_urls
from .track import register_trace_endpoint

__all__ = ["register_trace_endpoint", "site_urls"]