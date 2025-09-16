#!/usr/bin/env python3
"""
Simulator Entity Builder

Provides standard constructors for simulator entities to ensure
uniform structure across strategies while allowing non-breaking
extensions via the `extra` parameter.

Scope (excludes opportunity building – strategy/domain-specific):
- to_investment
- to_settled_investment
- to_stock_summary
- to_session_summary
"""

from typing import Dict, Any, Optional
from datetime import datetime
from .simulator_enum import InvestmentResult

# ========================================================
# Main entity builder APIs:
# ========================================================

def to_investment(
    stock: Dict[str, Any],
    start_date: str,
    purchase_price: float,
    targets: Optional[Dict[str, Any]] = None,
    # tracking: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Construct a standard investment entity (unsettled/base).

    Required fields: stock, start_date, purchase_price, targets.completed
    Optional fields: tracking, extra
    """
    entity: Dict[str, Any] = {
        'stock': stock or {},
        'start_date': start_date,
        'purchase_price': purchase_price,
        'targets': _ensure_targets_schema(targets),
    }
    # if tracking:
    #     entity['tracking'] = tracking
    return _merge_extra(entity, extra)

def to_settled_investment(
    investment: Dict[str, Any],
    end_date: str,
    result: Any,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Construct a standard settled investment entity.

    Computes settlement metrics internally from the base investment:
    - overall_profit = sum(weighted_profit) over targets.completed
      (fallback: profit * profit_contribution or profit * sell_ratio)
    - overall_profit_rate = overall_profit / purchase_price
    - invest_duration_days = days between start_date and end_date (YYYYMMDD)

    Inherits required base fields from the investment and does not mutate it.
    """
    # normalize result string if enum provided
    result_value = getattr(result, 'value', result)

    purchase_price = float(investment.get('purchase_price') or 0.0)
    targets = _ensure_targets_schema(investment.get('targets'))
    completed = targets.get('completed') or []

    overall_profit = 0.0
    for stage in completed:
        if isinstance(stage, dict):
            if 'weighted_profit' in stage and isinstance(stage['weighted_profit'], (int, float)):
                overall_profit += float(stage['weighted_profit'])
            elif 'profit' in stage:
                profit = float(stage.get('profit') or 0.0)
                if 'profit_contribution' in stage:
                    overall_profit += profit * float(stage.get('profit_contribution') or 0.0)
                elif 'sell_ratio' in stage:
                    overall_profit += profit * float(stage.get('sell_ratio') or 0.0)

    overall_profit_rate = (overall_profit / purchase_price) if purchase_price > 0 else 0.0

    # compute duration days
    def _parse(d: Optional[str]) -> Optional[datetime]:
        if not d:
            return None
        try:
            return datetime.strptime(str(d), '%Y%m%d')
        except Exception:
            return None

    start_dt = _parse(investment.get('start_date'))
    end_dt = _parse(end_date)
    invest_duration_days = (end_dt - start_dt).days if start_dt and end_dt else 0

    base = {
        'stock': investment.get('stock', {}),
        'start_date': investment.get('start_date'),
        'purchase_price': purchase_price,
        'targets': targets,
    }
    if 'tracking' in investment:
        base['tracking'] = investment['tracking']

    settled = {
        **base,
        'result': result_value,
        'end_date': end_date,
        'overall_profit': overall_profit,
        'overall_profit_rate': overall_profit_rate,
        'invest_duration_days': invest_duration_days,
    }
    return _merge_extra(settled, extra)

def to_stock_summary(
    stock_id: str,
    summary_core: Dict[str, Any],
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Construct a standard stock summary wrapper.

    Expected summary_core keys (at minimum):
    - total_investments, current_investments, win_rate,
      avg_roi, avg_annual_return, avg_duration_days,
      profit_ratio, loss_ratio, small_profit_ratio, small_loss_ratio,
      win_count, loss_count, small_profit_count, small_loss_count
    """
    summary: Dict[str, Any] = dict(summary_core or {})
    summary = _merge_extra(summary, extra)
    return {
        'stock_id': stock_id,
        'summary': summary,
    }


def to_session_summary(
    summary_core: Dict[str, Any],
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Construct a standard session summary."""
    summary: Dict[str, Any] = dict(summary_core or {})
    return _merge_extra(summary, extra)


# ========================================================
# Internal helper functions:
# ========================================================

def _merge_extra(base: Dict[str, Any], extra: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if extra and isinstance(extra, dict):
        for k, v in extra.items():
            # avoid overwriting standard keys
            if k not in base:
                base[k] = v
    return base


def _ensure_targets_schema(targets: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    normalized = targets.copy() if isinstance(targets, dict) else {}
    completed = normalized.get('completed')
    if not isinstance(completed, list):
        normalized['completed'] = []
    return normalized







