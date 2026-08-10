"""策略结果摘要分析（Facade ``Strategy.analyze`` 委托）。

本文件:
- AnalyzeService: 读取启用策略下 price / portfolio 最新 version 并 present
  边界: 负责发现最新产物目录与调用 ReportManager.present；不负责跑模拟
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.services.discovery import DiscoveryService

logger = logging.getLogger(__name__)


class AnalyzeService:
    """读取并展示各启用策略最新模拟摘要。"""

    @staticmethod
    def analyze(*, session_id: Optional[str] = None) -> None:
        """读取各启用策略下 price / portfolio 最新 version 摘要并 present。

        ``session_id`` 预留，当前未使用。
        """
        _ = session_id

        enabled = DiscoveryService.get_enabled_strategies()
        if not enabled:
            logger.warning("没有启用的策略可分析")
            return

        found = False
        for info in enabled:
            sn = str(info.unique_relative_path or info.key or "").strip()
            if not sn:
                continue
            folder = info.resolved_folder()
            pf_root = ProjectContext.path.get_strategy_simulation_price_directory(
                folder
            )
            po_root = ProjectContext.path.get_strategy_simulation_portfolio_directory(
                folder
            )
            pf_latest = AnalyzeService._latest_version_dir(pf_root)
            po_latest = AnalyzeService._latest_version_dir(po_root)
            if not pf_latest and not po_latest:
                continue

            found = True
            logger.info("📊 strategy=%s", sn)

            if pf_latest:
                try:
                    from core.modules.strategy import Strategy
                    from core.modules.strategy.contracts import SimulateKind

                    Strategy.present_report(SimulateKind.PRICE_FACTOR, pf_latest)
                except Exception as exc:
                    logger.warning(
                        "   price_factor: version=%s present failed: %s",
                        pf_latest.name,
                        exc,
                    )

            if po_latest:
                try:
                    from core.modules.strategy import Strategy
                    from core.modules.strategy.contracts import SimulateKind

                    Strategy.present_report(SimulateKind.PORTFOLIO, po_latest)
                except Exception as exc:
                    logger.warning(
                        "   portfolio: version=%s present failed: %s",
                        po_latest.name,
                        exc,
                    )

        if not found:
            logger.warning(
                "未找到可分析的 simulations 结果（请先运行 strategy_price_factor / strategy_portfolio）"
            )

    @staticmethod
    def _latest_version_dir(root: Path) -> Optional[Path]:
        meta_path = root / "meta.json"
        if not meta_path.is_file():
            return None
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        try:
            latest_id = int(meta.get("next_output_version") or 1) - 1
        except (TypeError, ValueError):
            return None
        if latest_id <= 0:
            return None
        version_dir = root / str(latest_id)
        return version_dir if version_dir.is_dir() else None


__all__ = ["AnalyzeService"]
