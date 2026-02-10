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
        # 优先使用 SOT 中的 sell_date 字段；如果未来引入 exit_date，则兼容回退
        exit_date = opportunity_row.get("sell_date") or opportunity_row.get("exit_date", "")
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

        # 计算整体 PnL（1 股）
        # 说明：
        # - 当前 SOT targets CSV 只有 roi（收益率）而没有绝对 profit/weighted_profit，
        #   因此在 PriceFactorSimulator MVP 阶段，我们统一使用「1 股 × 触发价 × ROI」近似总盈亏。
        # - 等后续 SOT 增加绝对收益列或更细粒度的拆分时，再改为基于 targets_list 精细计算。
        pnl = trigger_price * roi

        # 计算持续天数（自然日）
        start_dt = parse_yyyymmdd(trigger_date)
        end_dt = parse_yyyymmdd(exit_date)
        if start_dt and end_dt:
            duration_in_days = max((end_dt - start_dt).days, 1)
        else:
            duration_in_days = 1

        # 构造 tracking
        tracking = InvestmentBuilder._build_tracking(opportunity_row, trigger_price, trigger_date, exit_date)

        # 构造 completed_targets
        completed_targets = InvestmentBuilder._build_completed_targets(targets_list, trigger_price)

        # result 分类
        result = InvestmentBuilder._determine_result(opportunity_row, pnl)

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
            sell_price = float(t.get("price") or 0.0)
            profit = float(t.get("profit") or 0.0)
            weighted_profit = float(t.get("weighted_profit") or 0.0)
            t_roi = float(t.get("roi") or 0.0)
            sell_ratio = float(t.get("sell_ratio") or 0.0)
            sell_date = t.get("date") or ""
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
    def _determine_result(opportunity_row: Dict[str, Any], pnl: float) -> str:
        """确定 investment 的 result（win/loss/open）"""
        from core.modules.strategy.enums import OpportunityStatus
        status = (opportunity_row.get("status") or "").lower()
        if status in (OpportunityStatus.WIN.value, OpportunityStatus.LOSS.value, OpportunityStatus.OPEN.value):
            return status
        else:
            if pnl > 0:
                return OpportunityStatus.WIN.value
            elif pnl < 0:
                return OpportunityStatus.LOSS.value
            else:
                return OpportunityStatus.OPEN.value


