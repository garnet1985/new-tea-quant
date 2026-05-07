"""枚举会话级 ``enumMetrics``（分位、区间桶、节奏指标）的来源说明与入口。

- **主路径**：各 worker 在内存中带回 ``enumeration_report_bundle``，
  ``OpportunityEnumeratorFlowImpl.aggregate_job_results`` 填入 ``_enumeration_bundles_by_id``；
  使用 ``EnumeratorReport.from_per_stock_bundles`` 与每股 CSV **无关**，不在此之后再扫磁盘汇总。
- **指标计算**：落在 ``EnumeratorReport``（``data_classes/report.py``）：``percentileValues``、
  ``opportunityCountLabels`` / ``opportunityCountStockCounts`` 等均在该类内完成。
- **本模块**：提供 ``materialize_enum_report``，在 ``save_metadata`` 中与写 ``0_report_enum.json``
  共用同一 ``EnumeratorReport`` 实例；``build_result_report`` 直接使用内存中的 ``to_bff_payload()``，
  避免「先写盘再读 JSON 合并」失败导致前端缺字段。

仅当 bundle 缺失时才退回 ``from_output_dir``（读各股 ``*_opportunities.csv``），用于异常/旧目录兜底。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from core.modules.strategy.engines.simulator.enumerator.data_classes.report import EnumeratorReport


def materialize_enum_report(
    *,
    bundles_by_stock: Optional[Dict[str, Dict[str, Any]]],
    stock_universe: List[str],
    output_dir: Path,
) -> EnumeratorReport:
    """构建本轮 ``EnumeratorReport``：优先内存 bundle，否则扫描 ``output_dir`` 下 CSV（兜底）。"""
    if bundles_by_stock and stock_universe:
        return EnumeratorReport.from_per_stock_bundles(
            bundles_by_stock,
            stock_universe=list(stock_universe),
        )
    hint = len(stock_universe) if stock_universe else None
    return EnumeratorReport.from_output_dir(output_dir, total_stocks_hint=hint)


__all__ = ["materialize_enum_report"]
