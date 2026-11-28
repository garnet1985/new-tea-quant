"""NTQ 自己的官网客户端。导入时登记 trace 发送端。"""

from .ntq_external import register_trace_endpoint, site_urls

register_trace_endpoint()

__all__ = ["register_trace_endpoint", "site_urls"]