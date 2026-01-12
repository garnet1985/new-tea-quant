#!/usr/bin/env python3
"""
机会数据加载模块

负责从 CSV 文件加载 opportunities 和 targets 数据
"""

from pathlib import Path
from typing import Dict, Any, List, Tuple
from collections import defaultdict
import csv
import logging

logger = logging.getLogger(__name__)


class OpportunityLoader:
    """机会数据加载器"""

    @staticmethod
    def load_opportunities_and_targets(
        opportunities_path: Path,
        targets_path: Path,
        start_date: str = "",
        end_date: str = "",
    ) -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
        """
        从 CSV 文件加载 opportunities 和 targets 数据
        
        Args:
            opportunities_path: opportunities CSV 文件路径
            targets_path: targets CSV 文件路径
            start_date: 开始日期过滤（YYYYMMDD，可选）
            end_date: 结束日期过滤（YYYYMMDD，可选）
            
        Returns:
            (opportunities, targets_map): 
                - opportunities: 过滤后的机会列表
                - targets_map: 按 opportunity_id 分组的 targets 字典
        """
        # 1. 读取 targets，按 opportunity_id 分组
        targets_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        if targets_path.exists():
            with targets_path.open("r", encoding="utf-8") as f_t:
                t_reader = csv.DictReader(f_t)
                for row in t_reader:
                    opp_id = str(row.get("opportunity_id") or "").strip()
                    if not opp_id:
                        continue
                    # 规范化数值字段
                    try:
                        row["weighted_profit"] = float(row.get("weighted_profit") or 0.0)
                    except ValueError:
                        row["weighted_profit"] = 0.0
                    targets_map[opp_id].append(row)

        # 2. 读取所有机会并过滤
        opportunities: List[Dict[str, Any]] = []
        if not opportunities_path.exists():
            logger.warning(
                f"[OpportunityLoader] opportunities 文件不存在: {opportunities_path}"
            )
            return opportunities, targets_map

        with opportunities_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trigger_date = row.get("trigger_date") or ""

                # 时间窗口过滤（基于字符串比较，YYYYMMDD 形式）
                if start_date and trigger_date < start_date:
                    continue
                if end_date and trigger_date > end_date:
                    continue

                opportunities.append(row)

        return opportunities, targets_map
