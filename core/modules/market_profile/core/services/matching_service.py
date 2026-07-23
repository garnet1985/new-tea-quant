#!/usr/bin/env python3
"""股票代码匹配服务（Matching Service）。"""

from typing import Any, Dict


class MatchingService:
    """股票代码匹配服务。

    为所有公有方法提供股票代码匹配功能。
    """

    @staticmethod
    def extract_stock_code(stock_id: str) -> str:
        """提取股票代码的数字部分。

        Args:
            stock_id: 股票ID（如 '000001.SZ', '688001.SH'）

        Returns:
            数字代码部分（如 '000001', '688001'）
        """
        raw = str(stock_id or "").strip().upper()
        if not raw:
            return ""
        head = raw.split(".", 1)[0]
        return "".join(ch for ch in head if ch.isdigit())

    @staticmethod
    def match_id_block(code: str, id_block: Dict[str, Any]) -> bool:
        """匹配股票代码块。

        Args:
            code: 股票数字代码
            id_block: ID匹配配置（如 {"start_with": ["688"], "relation": "or"}）

        Returns:
            True表示匹配成功
        """
        prefixes_raw = id_block.get("start_with")
        if not isinstance(prefixes_raw, list):
            return False

        prefixes = [str(p).strip() for p in prefixes_raw if str(p).strip()]
        if not prefixes or not code:
            return False

        hits = [code.startswith(p) for p in prefixes]
        relation = str(id_block.get("relation") or "or").strip().lower()

        if relation == "and":
            return all(hits)
        return any(hits)

    @staticmethod
    def match_stock_id(stock_id: str, matching: Dict[str, Any]) -> bool:
        """判断股票ID是否匹配配置。

        Args:
            stock_id: 股票ID（如 '000001.SZ'）
            matching: 匹配配置（如 {"id": {"start_with": ["688"]}}）

        Returns:
            True表示匹配成功
        """
        if not isinstance(matching, dict) or not matching:
            return False

        id_block = matching.get("id")
        if not isinstance(id_block, dict):
            return False

        code = MatchingService.extract_stock_code(stock_id)
        return MatchingService.match_id_block(code, id_block)

    @staticmethod
    def max_matching_prefix_len(matching: Dict[str, Any]) -> int:
        """计算匹配配置的最长前缀长度（用于排序优先级）。

        Args:
            matching: 匹配配置

        Returns:
            最长前缀长度（越长优先级越高）
        """
        if not isinstance(matching, dict):
            return 0

        id_block = matching.get("id")
        if not isinstance(id_block, dict):
            return 0

        prefixes = id_block.get("start_with")
        if not isinstance(prefixes, list):
            return 0

        lengths = [len(str(p).strip()) for p in prefixes if str(p).strip()]
        return max(lengths) if lengths else 0


__all__ = ["MatchingService"]