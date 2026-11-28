"""跨平台 CLI 图标：UTF-8 终端用 emoji，Windows GBK 用 ASCII。"""

from __future__ import annotations

import logging
import sys
from typing import Dict

logger = logging.getLogger(__name__)


class IconService:
    """跨平台图标：按名称取 emoji 或 ASCII 回退。"""

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

    @staticmethod
    def supports_emoji() -> bool:
        """当前 stdout 是否适合输出 emoji。"""
        if sys.platform == "win32":
            encoding = getattr(sys.stdout, "encoding", None)
            return str(encoding or "").lower() == "utf-8"
        return True

    @classmethod
    def get(cls, icon_name: str) -> str:
        """按正式名取图标；未知名返回空串。"""
        key = str(icon_name or "").strip().lower()
        icon_def = cls.ICONS.get(key)
        if not icon_def:
            logger.error("Unknown icon name: %s", icon_name)
            return ""
        if cls.supports_emoji():
            return icon_def["emoji"]
        return icon_def["ascii"]


class IconNamespace:
    """CmdLayout.icon 命名空间。"""

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
