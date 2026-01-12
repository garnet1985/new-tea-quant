#!/usr/bin/env python3
"""
事件流构建模块

从 SOT 结果构建全局事件流（trigger 和 target 事件）
"""

from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict
import logging

from app.core.modules.strategy.components.price_factor_simulator.opportunity_loader import OpportunityLoader

logger = logging.getLogger(__name__)


class EventBuilder:
    """事件流构建器"""

    @staticmethod
    def build_event_stream(
        sot_version_dir: Path,
        start_date: str = "",
        end_date: str = "",
    ) -> List[Dict[str, Any]]:
        """
        从 SOT 目录构建全局事件流
        
        Args:
            sot_version_dir: SOT 版本目录
            start_date: 开始日期过滤（YYYYMMDD，可选）
            end_date: 结束日期过滤（YYYYMMDD，可选）
            
        Returns:
            事件列表，按日期排序
        """
        events: List[Dict[str, Any]] = []

        # 扫描所有 opportunities 和 targets 文件
        for entry in sot_version_dir.iterdir():
            if not entry.is_file():
                continue

            name = entry.name
            if name.endswith("_opportunities.csv"):
                stock_id = name[: -len("_opportunities.csv")]
                targets_path = sot_version_dir / f"{stock_id}_targets.csv"

                # 加载机会和目标
                opportunities, targets_map = OpportunityLoader.load_opportunities_and_targets(
                    entry,
                    targets_path,
                    start_date=start_date,
                    end_date=end_date,
                )

                # 为每个机会创建 trigger 事件
                for opp in opportunities:
                    opp_id = str(opp.get("opportunity_id") or "").strip()
                    trigger_date = opp.get("trigger_date") or ""

                    if not opp_id or not trigger_date:
                        continue

                    events.append({
                        "event_type": "trigger",
                        "date": trigger_date,
                        "stock_id": stock_id,
                        "opportunity_id": opp_id,
                        "opportunity": opp,
                    })

                    # 为该机会的所有 targets 创建 target 事件
                    targets = targets_map.get(opp_id, [])
                    for target in targets:
                        target_date = target.get("date") or ""
                        if not target_date:
                            continue

                        events.append({
                            "event_type": "target",
                            "date": target_date,
                            "stock_id": stock_id,
                            "opportunity_id": opp_id,
                            "opportunity": opp,  # 包含完整的 opportunity 信息
                            "target": target,
                        })

        # 按日期排序，同日多事件按 (stock_id, opportunity_id, event_type) 排序
        events.sort(key=lambda e: (
            e.get("date", ""),
            e.get("stock_id", ""),
            e.get("opportunity_id", ""),
            e.get("event_type", ""),
        ))

        logger.info(
            f"[EventBuilder] 构建事件流: 共 {len(events)} 个事件 "
            f"(trigger={sum(1 for e in events if e['event_type'] == 'trigger')}, "
            f"target={sum(1 for e in events if e['event_type'] == 'target')})"
        )

        return events
