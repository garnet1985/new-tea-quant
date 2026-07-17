"""资金/组合结果缓存（按 settings_fp + env_fp）。"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PortfolioCacheManager:
    """portfolio / capital_allocation 步骤缓存。

    边界:
    - 负责: 按双指纹查找 / 写入 capital_allocation slot（当前 stub）
    - 不负责: 算指纹、跑 portfolio 引擎
    - 调用方: Strategy.portfolio / simulate
    """

    @staticmethod
    def lookup(*, settings_fp: str, env_fp: str) -> Optional[Dict[str, Any]]:
        _ = (settings_fp, env_fp)
        return None

    @staticmethod
    def store(
        *,
        settings_fp: str,
        env_fp: str,
        results: Dict[str, Any],
    ) -> None:
        _ = (settings_fp, env_fp, results)
        logger.debug(
            "PortfolioCacheManager.store stub: settings_fp=%s env_fp=%s",
            settings_fp[:12] if settings_fp else "",
            env_fp[:12] if env_fp else "",
        )


__all__ = ["PortfolioCacheManager"]
