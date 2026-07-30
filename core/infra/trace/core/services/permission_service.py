"""Interactive permission prompt for Trace (CLI / TTY)."""

from __future__ import annotations

import sys

from .consent_service import TraceConsentService

_PROMPT_TITLE = (
    "是否分享匿名调试数据，帮助我们定位不同系统上的安装/运行错误？"
)
_PROMPT_DETAIL = (
    "仅包含：OS / Python 版本 / 架构 / NTQ 版本 / 错误码。"
    "不含策略、行情、IP、主机名。"
)
_PROMPT_HINT = "输入 y 同意；直接回车或其他键表示不同意（默认不同意）。"


class TracePermissionService:
    """
    Ensure a consent decision exists when an interactive terminal is available.

    Already decided → no-op.
    Non-TTY → leave undecided (UI / later CLI can ask).
    """

    @staticmethod
    def ask(*, source: str = "cli") -> bool:
        """
        Return whether tracing is currently granted after this call.

        Never raises for normal failures. ``KeyboardInterrupt`` from ``input``
        is re-raised so the caller can abort.
        """
        try:
            if TraceConsentService.is_decided():
                return TraceConsentService.is_granted()
        except Exception:
            return False

        if not TracePermissionService._can_prompt():
            return False

        print(flush=True)
        print(_PROMPT_TITLE, flush=True)
        print(_PROMPT_DETAIL, flush=True)
        print(_PROMPT_HINT, flush=True)
        try:
            ans = input("> ").strip().lower()
        except EOFError:
            print(flush=True)
            print("未收到输入，按不同意处理。", flush=True)
            TraceConsentService.set(False, source=source or "cli")
            return False
        except KeyboardInterrupt:
            print(flush=True)
            raise

        agreed = ans == "y"
        TraceConsentService.set(agreed, source=source or "cli")
        if agreed:
            print("已开启匿名调试数据分享。", flush=True)
        else:
            print("已跳过匿名调试数据分享。", flush=True)
        return agreed

    @staticmethod
    def needs_ask() -> bool:
        try:
            return not TraceConsentService.is_decided()
        except Exception:
            return True

    @staticmethod
    def _can_prompt() -> bool:
        try:
            return bool(sys.stdin.isatty() and sys.stdout.isatty())
        except Exception:
            return False
