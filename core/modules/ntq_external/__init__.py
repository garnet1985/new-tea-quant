"""NTQ 自己的官网客户端。导入时登记 trace 发送端。"""

from core.modules.ntq_external.track import register_trace_endpoint

register_trace_endpoint()

__all__ = ["register_trace_endpoint"]
