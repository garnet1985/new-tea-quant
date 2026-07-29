#!/usr/bin/env python3
"""HistoryLoader — 历史价格模拟结果加载器。

读取 NEW 布局：
- ``results/simulations/price/{version}/entities/{id}_investments.csv``
- ``results/simulations/price/{version}/overall_report.json``
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class HistoryLoader:
    """历史模拟结果加载器（price_factor NEW 产物）。"""

    @staticmethod
    def load_stock_history(
        strategy_name: str,
        stock_id: str,
    ) -> Optional[Dict[str, Any]]:
        """加载单只股票的历史模拟统计。

        Returns:
            统计信息字典，如果不存在返回 None::

                {
                    'win_rate': 0.65,
                    'avg_return': 0.05,
                    'total_investments': 10,
                    'win_count': 7,
                    'loss_count': 3,
                    'max_return': 0.15,
                    'min_return': -0.08,
                    'avg_holding_days': 5.2,
                }
        """
        try:
            version_dir = HistoryLoader._latest_price_version_dir(strategy_name)
            if version_dir is None:
                return None

            from core.modules.strategy.core.engines.price_factor.report_manager.investments import (
                EntityInvestments,
            )

            rows = EntityInvestments.load(version_dir, stock_id)
            if not rows:
                return None

            investments = [
                {
                    "roi": row.roi,
                    "result": row.result,
                    "duration_in_days": row.holding_days,
                }
                for row in rows
            ]
            return HistoryLoader._calculate_statistics(investments)

        except Exception as e:
            logger.debug(
                "[HistoryLoader] 加载股票历史失败: stock_id=%s, error=%s",
                stock_id,
                e,
            )
            return None

    @staticmethod
    def _calculate_statistics(investments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算投资统计信息。"""
        if not investments:
            return {}

        completed = [
            inv for inv in investments if inv.get("result") in ["win", "loss"]
        ]

        if not completed:
            return {
                "total_investments": len(investments),
                "completed_investments": 0,
                "win_rate": 0.0,
                "avg_return": 0.0,
                "win_count": 0,
                "loss_count": 0,
                "max_return": 0.0,
                "min_return": 0.0,
                "avg_holding_days": 0.0,
            }

        returns = []
        holding_days = []
        win_count = 0
        loss_count = 0

        for inv in completed:
            roi = inv.get("roi", 0.0)
            if not isinstance(roi, (int, float)):
                try:
                    roi = float(roi)
                except (ValueError, TypeError):
                    roi = 0.0

            returns.append(roi)

            result = inv.get("result", "")
            if result == "win":
                win_count += 1
            elif result == "loss":
                loss_count += 1
            elif roi > 0:
                win_count += 1
            elif roi < 0:
                loss_count += 1

            duration = inv.get("duration_in_days", 0)
            if not isinstance(duration, (int, float)):
                try:
                    duration = float(duration)
                except (ValueError, TypeError):
                    duration = 0.0

            if duration > 0:
                holding_days.append(duration)

        total = len(completed)
        win_rate = win_count / total if total > 0 else 0.0
        avg_return = sum(returns) / len(returns) if returns else 0.0
        max_return = max(returns) if returns else 0.0
        min_return = min(returns) if returns else 0.0
        avg_holding_days = (
            sum(holding_days) / len(holding_days) if holding_days else 0.0
        )

        return {
            "total_investments": len(investments),
            "completed_investments": total,
            "win_rate": win_rate,
            "avg_return": avg_return,
            "win_count": win_count,
            "loss_count": loss_count,
            "max_return": max_return,
            "min_return": min_return,
            "avg_holding_days": avg_holding_days,
        }

    @staticmethod
    def load_session_summary(strategy_name: str) -> Optional[Dict[str, Any]]:
        """加载最新 price_factor ``overall_report.json``。"""
        try:
            version_dir = HistoryLoader._latest_price_version_dir(strategy_name)
            if version_dir is None:
                return None

            from core.modules.strategy.core.engines.price_factor.report_manager.report_consts import (
                ReportPaths,
            )

            summary_file = ReportPaths.overall_report_path(version_dir)
            if not summary_file.is_file():
                return None

            return json.loads(summary_file.read_text(encoding="utf-8"))

        except Exception as e:
            logger.debug("[HistoryLoader] 加载会话汇总失败: %s", e)
            return None

    @staticmethod
    def _latest_price_version_dir(strategy_name: str) -> Optional[Path]:
        """Resolve latest ``results/simulations/price/{version}`` directory."""
        name = str(strategy_name or "").strip()
        if not name:
            return None

        from core.infra.project_context import ProjectContext

        root = ProjectContext.path.get_strategy_directory_simulation_price(name)
        meta_path = root / "meta.json"
        if not meta_path.is_file():
            return None
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            latest_id = int(meta.get("next_output_version") or 1) - 1
        except Exception:
            return None
        if latest_id <= 0:
            return None
        version_dir = root / str(latest_id)
        return version_dir if version_dir.is_dir() else None
