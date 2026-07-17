"""枚举结果缓存（按 settings_fp + env_fp）。"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class EnumCacheManager:
    """枚举步骤缓存。

    边界:
    - 负责: 按双指纹查找 / 写入 enum slot（当前 stub，无持久化）
    - 不负责: 算指纹、跑 EnumeratorPipeline
    - 调用方: Strategy.enumerate / simulate；EnumeratorPipeline 写回
    """

    @staticmethod
    def lookup(*, settings_fp: str, env_fp: str) -> Optional[Dict[str, Any]]:
        _ = (settings_fp, env_fp)
        # TODO: 接 DB / 磁盘 snapshot（legacy SimulatorResDbCache enum slot）
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
            "EnumCacheManager.store stub: settings_fp=%s env_fp=%s keys=%s",
            settings_fp[:12] if settings_fp else "",
            env_fp[:12] if env_fp else "",
            sorted(results.keys()),
        )


__all__ = ["EnumCacheManager"]
