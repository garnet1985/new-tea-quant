#!/usr/bin/env python3
"""
投资记录构建模块

负责从 opportunity 和 targets 数据构建 investment 记录
"""

from typing import Dict, Any, List
from .helpers import parse_yyyymmdd, get_annual_return


class InvestmentBuilder:
    """投资记录构建器"""

    @staticmethod
    def build_investment(
        opportunity_row: Dict[str, Any],
        targets_list: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        从 opportunity 和 targets 数据构建单个 investment 记录
        
        Args:
            opportunity_row: opportunity CSV 的一行数据
            targets_list: 该 opportunity 对应的 targets 列表
            
        Returns:
            investment 字典
        """
        trigger_date = opportunity_row.get("trigger_date", "")
        # 先使用切片内已完成目标推导结束日期；若无，再回退到 opportunity 字段
        exit_date = ""
        opp_id = str(opportunity_row.get("opportunity_id") or "").strip()

        # 解析基础字段
        try:
            trigger_price = float(opportunity_row.get("trigger_price") or 0.0)
        except ValueError:
            trigger_price = 0.0
        try:
            roi = float(opportunity_row.get("roi") or 0.0)
        except ValueError:
            roi = 0.0

        # 构造 completed_targets（targets 已由 DataLoader 严格按切片过滤）
        completed_targets = InvestmentBuilder._build_completed_targets(targets_list, trigger_price)
        total_sell_ratio = sum(
            float(t.get("sell_ratio") or 0.0)
            for t in completed_targets
        )
        is_completed_in_window = total_sell_ratio >= 1.0

        if completed_targets:
            exit_date = str(completed_targets[-1].get("sell_date") or "")
        else:
            exit_date = opportunity_row.get("sell_date") or opportunity_row.get("exit_date", "")

        # 切片口径下盈亏：优先用 weighted_profit 汇总；缺失时回退 trigger_price * roi。
        pnl = sum(float(t.get("weighted_profit") or 0.0) for t in completed_targets)
        if not completed_targets:
            pnl = trigger_price * roi

        # 切片口径 ROI：使用切片内加权收益；避免使用全量机会的 roi 导致失真。
        if trigger_price > 0:
            roi = pnl / trigger_price
        else:
            roi = 0.0

        # 计算持续天数（自然日）
        start_dt = parse_yyyymmdd(trigger_date)
        end_dt = parse_yyyymmdd(exit_date)
        if start_dt and end_dt:
            duration_in_days = max((end_dt - start_dt).days, 1)
        else:
            duration_in_days = 1

        # 构造 tracking
        tracking = InvestmentBuilder._build_tracking(opportunity_row, trigger_price, trigger_date, exit_date)

        # result 分类
        result = InvestmentBuilder._determine_result(is_completed_in_window, pnl)

        # 构造 investment 记录
        overall_annual_return = get_annual_return(roi, duration_in_days)
        investment = {
            "result": result,
            "start_date": trigger_date,
            "end_date": exit_date,
            "purchase_price": trigger_price,
            "duration_in_days": duration_in_days,
            "overall_profit": pnl,
            "roi": roi,
            "overall_annual_return": overall_annual_return,
            "tracking": tracking,
            "completed_targets": completed_targets,
            "is_completed_in_window": is_completed_in_window,
            "completion_status": "completed" if is_completed_in_window else "unfinished",
            "sell_ratio_in_window": round(min(total_sell_ratio, 1.0), 4),
            "opportunity_id": opp_id,
        }

        return investment

    @staticmethod
    def _build_tracking(
        opportunity_row: Dict[str, Any],
        trigger_price: float,
        trigger_date: str,
        exit_date: str,
    ) -> Dict[str, Any]:
        """构造 tracking 信息"""
        try:
            max_price = float(opportunity_row.get("max_price") or 0.0)
        except ValueError:
            max_price = 0.0
        try:
            min_price = float(opportunity_row.get("min_price") or 0.0)
        except ValueError:
            min_price = 0.0

        if trigger_price > 0:
            max_ratio = (max_price - trigger_price) / trigger_price if max_price > 0 else 0.0
            min_ratio = (min_price - trigger_price) / trigger_price if min_price > 0 else 0.0
        else:
            max_ratio = 0.0
            min_ratio = 0.0

        return {
            "max_close_reached": {
                "price": max_price if max_price > 0 else trigger_price,
                "date": exit_date,
                "ratio": max_ratio,
            },
            "min_close_reached": {
                "price": min_price if min_price > 0 else trigger_price,
                "date": trigger_date,
                "ratio": min_ratio,
            },
        }

    @staticmethod
    def _build_completed_targets(
        targets_list: List[Dict[str, Any]],
        trigger_price: float,
    ) -> List[Dict[str, Any]]:
        """构造 completed_targets 列表"""
        completed_targets: List[Dict[str, Any]] = []
        for t in targets_list:
            # 统一字段读取：优先使用统一后的字段名，其次兼容旧字段
            raw_price = t.get("sell_price")
            if raw_price in (None, ""):
                raw_price = t.get("price")
            if raw_price in (None, ""):
                raw_price = t.get("target_price")
            try:
                sell_price = float(raw_price or 0.0)
            except (TypeError, ValueError):
                sell_price = 0.0

            try:
                profit = float(t.get("profit") or 0.0)
            except (TypeError, ValueError):
                profit = 0.0
            try:
                weighted_profit = float(t.get("weighted_profit") or 0.0)
            except (TypeError, ValueError):
                weighted_profit = 0.0
            try:
                t_roi = float(t.get("roi") or 0.0)
            except (TypeError, ValueError):
                t_roi = 0.0
            try:
                sell_ratio = float(t.get("sell_ratio") or 0.0)
            except (TypeError, ValueError):
                sell_ratio = 0.0

            sell_date = t.get("date") or t.get("sell_date") or t.get("target_date") or ""
            reason = (t.get("reason") or "").lower()

            if "win" in reason:
                target_type = "take_profit"
                name = reason
            elif "loss" in reason:
                target_type = "stop_loss"
                name = reason
            elif "expiration" in reason:
                target_type = "expired"
                name = "expiration"
            else:
                target_type = "unknown"
                name = reason or "unknown"

            completed_targets.append(
                {
                    "name": name,
                    "target_type": target_type,
                    "sell_price": sell_price,
                    "sell_date": sell_date,
                    "sell_ratio": sell_ratio,
                    "profit": profit,
                    "weighted_profit": weighted_profit,
                    "profit_ratio": t_roi,
                    "target_price": trigger_price,
                    "extra_fields": {},
                }
            )
        return completed_targets

    @staticmethod
    def _determine_result(is_completed_in_window: bool, pnl: float) -> str:
        """确定 investment 的 result（严格按当前切片口径）。"""
        from core.modules.strategy.enums import OpportunityStatus

        if not is_completed_in_window:
            return OpportunityStatus.OPEN.value
        if pnl > 0:
            return OpportunityStatus.WIN.value
        if pnl < 0:
            return OpportunityStatus.LOSS.value
        return OpportunityStatus.OPEN.value


