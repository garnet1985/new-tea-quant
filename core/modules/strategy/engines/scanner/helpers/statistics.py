#!/usr/bin/env python3
"""Scanner summary statistics helper."""

from typing import Any, Dict, List


class ScannerStatisticsHelper:
    @staticmethod
    def generate_scan_summary(
        strategy_name: str,
        date: str,
        strategy_version: str,
        total_stocks: int,
        opportunities: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        summary = {
            "scan_date": date,
            "strategy_name": strategy_name,
            "strategy_version": strategy_version,
            "total_stocks_scanned": total_stocks,
            "total_opportunities_found": len(opportunities),
            "opportunity_rate": len(opportunities) / total_stocks if total_stocks else 0,
        }
        if opportunities:
            summary["avg_expected_return"] = sum(
                o.get("expected_return", 0) for o in opportunities
            ) / len(opportunities)
            summary["avg_confidence"] = sum(
                o.get("confidence", 0) for o in opportunities
            ) / len(opportunities)
        return summary


__all__ = ["ScannerStatisticsHelper"]
