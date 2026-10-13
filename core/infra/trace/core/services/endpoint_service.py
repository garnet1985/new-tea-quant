"""Trace 发送端。地址由外部模块登记；没登记就不发送。"""

from __future__ import annotations


class TraceEndpointService:
    """进程内登记一次。官网地址不写在 trace 里。"""

    _ensured = False
    _url = ""
    _setup_without_consent = False

    @staticmethod
    def ensure() -> None:
        if TraceEndpointService._ensured:
            return
        TraceEndpointService._ensured = True
        try:
            import core.modules.ntq_external  # noqa: F401
        except ImportError:
            return

    @staticmethod
    def register(url: str, *, setup_without_consent: bool = False) -> None:
        TraceEndpointService._url = str(url or "").strip()
        TraceEndpointService._setup_without_consent = bool(setup_without_consent)

    @staticmethod
    def url() -> str:
        return TraceEndpointService._url

    @staticmethod
    def setup_without_consent() -> bool:
        return TraceEndpointService._setup_without_consent

    @staticmethod
    def reset() -> None:
        """测试用：清掉登记，允许下一次 ensure 再导入。"""
        TraceEndpointService._ensured = False
        TraceEndpointService._url = ""
        TraceEndpointService._setup_without_consent = False
