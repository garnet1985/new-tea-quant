"""Cross-platform CLI icons: emoji on UTF-8 terminals, ASCII on Windows GBK."""
from __future__ import annotations

import logging
import sys
from typing import Dict

logger = logging.getLogger(__name__)


class IconService:
    """跨平台图标服务：macOS/Linux 用 emoji，Windows GBK 用 ASCII 文本。"""

    ICONS: Dict[str, Dict[str, str]] = {
        # 结论类
        "info": {"emoji": "ℹ️", "ascii": "[INFO]"},
        "warning": {"emoji": "⚠️", "ascii": "[WARN]"},
        "error": {"emoji": "❌", "ascii": "[FAIL]"},
        "success": {"emoji": "✅", "ascii": "[OK]"},
        "ongoing": {"emoji": "🔄", "ascii": "[...]"},
        # 功能类
        "search": {"emoji": "🔍", "ascii": "[SEARCH]"},
        "calendar": {"emoji": "📅", "ascii": "[DATE]"},
        "bar_chart": {"emoji": "📊", "ascii": "[CHART]"},
        "line_chart": {"emoji": "📈", "ascii": "[UP]"},
        "downward_trend": {"emoji": "📉", "ascii": "[DOWN]"},
        "money": {"emoji": "💰", "ascii": "[MONEY]"},
        "rocket": {"emoji": "🚀", "ascii": "[START]"},
        "gear": {"emoji": "🔧", "ascii": "[CONFIG]"},
        "clock": {"emoji": "🕙", "ascii": "[TIME]"},
        "target": {"emoji": "🎯", "ascii": "[TARGET]"},
        "tag": {"emoji": "🏷️", "ascii": "[TAG]"},
        "clipboard": {"emoji": "📋", "ascii": "[LIST]"},
        "folder": {"emoji": "📁", "ascii": "[DIR]"},
        "memo": {"emoji": "📝", "ascii": "[NOTE]"},
        "tip": {"emoji": "💡", "ascii": "[TIP]"},
        "sparkle": {"emoji": "✨", "ascii": "[*]"},
        "star": {"emoji": "⭐", "ascii": "[*]"},
        "celebrate": {"emoji": "🎉", "ascii": "[DONE]"},
        "upload": {"emoji": "📤", "ascii": "[OUT]"},
        "download": {"emoji": "📥", "ascii": "[IN]"},
        "attach": {"emoji": "📎", "ascii": "[FILE]"},
        "pin": {"emoji": "📌", "ascii": "[PIN]"},
        "trash": {"emoji": "🗑️", "ascii": "[DEL]"},
        "play": {"emoji": "▶️", "ascii": "[RUN]"},
        "pause": {"emoji": "⏸️", "ascii": "[PAUSE]"},
        "skip": {"emoji": "⏭️", "ascii": "[SKIP]"},
        "numbers": {"emoji": "🔢", "ascii": "[NUM]"},
        "market": {"emoji": "💹", "ascii": "[MKT]"},
        "game": {"emoji": "🎮", "ascii": "[SIM]"},
        "triangle_up": {"emoji": "🔺", "ascii": "[UP]"},
        "triangle_down": {"emoji": "🔻", "ascii": "[DOWN]"},
        "timer": {"emoji": "⏱️", "ascii": "[TIME]"},
        "hourglass": {"emoji": "⌛", "ascii": "[WAIT]"},
        "ruler": {"emoji": "📏", "ascii": "[SIZE]"},
        "eyes": {"emoji": "👀", "ascii": "[SEE]"},
        "disk": {"emoji": "💾", "ascii": "[SAVE]"},
        # 状态点
        "green_dot": {"emoji": "🟢", "ascii": "[ON]"},
        "red_dot": {"emoji": "🔴", "ascii": "[OFF]"},
        "orange_dot": {"emoji": "🟠", "ascii": "[WARN]"},
        "yellow_dot": {"emoji": "🟡", "ascii": "[WAIT]"},
        "blue_dot": {"emoji": "🔵", "ascii": "[INFO]"},
        "purple_dot": {"emoji": "🟣", "ascii": "[INFO]"},
        "white_dot": {"emoji": "⚪", "ascii": "[INFO]"},
        "black_dot": {"emoji": "⚫", "ascii": "[INFO]"},
        "brown_dot": {"emoji": "🟤", "ascii": "[INFO]"},
    }

    ALIASES: Dict[str, str] = {
        "information": "info",
        "exclamation": "warning",
        "failed": "error",
        "err": "error",
        "cross": "error",
        "check": "success",
        "pass": "success",
        "ok": "success",
        "done": "success",
        "chart": "bar_chart",
        "upward_trend": "line_chart",
        "increase": "line_chart",
        "decrease": "downward_trend",
        "stock": "money",
        "dot": "green_dot",
        "label": "tag",
        "list": "clipboard",
        "dir": "folder",
        "note": "memo",
        "idea": "tip",
        "bulb": "tip",
        "party": "celebrate",
        "delete": "trash",
        "run": "play",
        "start": "rocket",
        "config": "gear",
        "critical": "red_dot",
        "high": "orange_dot",
        "medium": "yellow_dot",
        "low": "green_dot",
        "enumerate": "numbers",
        "sim": "game",
        "save": "disk",
        "watch": "eyes",
    }

    @staticmethod
    def supports_emoji() -> bool:
        """Detect whether the current stdout can print emoji safely."""
        if sys.platform == "win32":
            encoding = getattr(sys.stdout, "encoding", None)
            return str(encoding or "").lower() == "utf-8"
        return True

    @classmethod
    def get(cls, icon_name: str) -> str:
        """Return emoji (UTF-8) or ASCII fallback (Windows GBK)."""
        key = str(icon_name or "").lower()
        icon_key = cls.ALIASES.get(key, key)
        icon_def = cls.ICONS.get(icon_key)
        if not icon_def:
            logger.error("Unknown icon name: %s", icon_name)
            return ""
        if cls.supports_emoji():
            return icon_def["emoji"]
        return icon_def["ascii"]


class IconNamespace:
    """CmdLayout.icon namespace."""

    @staticmethod
    def get(icon_name: str) -> str:
        return IconService.get(icon_name)

    @staticmethod
    def i(icon_name: str) -> str:
        return IconService.get(icon_name)

    @staticmethod
    def supports_emoji() -> bool:
        return IconService.supports_emoji()


__all__ = ["IconNamespace", "IconService"]
