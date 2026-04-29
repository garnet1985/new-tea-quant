#!/usr/bin/env python3
"""Simulator summary statistics helper."""

from datetime import datetime
from typing import Any, Dict, List

from core.modules.strategy.enums import OpportunityStatus


class SimulatorStatisticsHelper:
    @staticmethod
    def _closed_metrics(closed_opps: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not closed_opps:
            return {}
        metrics = {
            "win_rate": sum(
                1 for o in closed_opps if o.get("price_return", 0) > 0
            ) / len(closed_opps),
            "avg_price_return": sum(
                o.get("price_return", 0) for o in closed_opps
            ) / len(closed_opps),
            "avg_holding_days": sum(
                o.get("holding_days", 0) for o in closed_opps
            ) / len(closed_opps),
        }
        return metrics

    @staticmethod
    def calculate_summary(opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not opportunities:
            return {}

        closed_opps = [
            o for o in opportunities if o.get("status") == OpportunityStatus.CLOSED.value
        ]
        summary = {
            "total_opportunities": len(opportunities),
            "total_closed": len(closed_opps),
        }
        if closed_opps:
            summary.update(SimulatorStatisticsHelper._closed_metrics(closed_opps))
            summary["max_return"] = max(o.get("price_return", 0) for o in closed_opps)
            summary["max_loss"] = min(o.get("price_return", 0) for o in closed_opps)
            if summary["avg_holding_days"] > 0:
                summary["annual_return"] = summary["avg_price_return"] * (
                    250 / summary["avg_holding_days"]
                )
        return summary

    @staticmethod
    def generate_simulate_summary(
        strategy_name: str,
        session_id: str,
        opportunities: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        closed_opps = [
            o for o in opportunities if o.get("status") == OpportunityStatus.CLOSED.value
        ]
        summary = {
            "session_id": session_id,
            "session_date": datetime.now().strftime("%Y-%m-%d"),
            "strategy_name": strategy_name,
            "total_opportunities": len(opportunities),
            "total_closed": len(closed_opps),
        }
        if closed_opps:
            summary.update(SimulatorStatisticsHelper._closed_metrics(closed_opps))
        return summary


__all__ = ["SimulatorStatisticsHelper"]
