"""把官网 trace 地址登记到 infra.trace。"""

from core.infra.trace.core.services.endpoint_service import TraceEndpointService
from core.modules.ntq_external.conf.site_target import trace_url


def register_trace_endpoint() -> None:
    """安装事件不看使用统计开关。其余事件仍由 trace 自己看同意。"""
    TraceEndpointService.register(trace_url(), setup_without_consent=True)


__all__ = ["register_trace_endpoint"]
