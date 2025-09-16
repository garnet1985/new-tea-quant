#!/usr/bin/env python3
"""
Analyzer-level Entity Builder

Shared constructors for opportunity, investment, settled investment,
stock summary, and session summary. Strategies can extend entities via
the `extra` parameter without altering standard fields.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from app.analyzer.libs.enum.common_enum import InvestmentResult
from app.analyzer.analyzer_service import AnalyzerService

def to_opportunity(
    stock: Dict[str, Any],
    date: str,
    price: float,
    lower_bound: Optional[float] = None,
    upper_bound: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
    extra_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Construct a standard opportunity entity.

    Required fields: stock{id[,name?]}, date, price
    Optional fields: lower_bound, upper_bound, and extra (strategy-specific)
    """
    entity: Dict[str, Any] = {
        'stock': stock or {},
        'date': date,
        'price': price,
    }
    if lower_bound is not None:
        entity['lower_bound'] = lower_bound
    if upper_bound is not None:
        entity['upper_bound'] = upper_bound
    # prefer `extra` but keep compatibility with `extra_fields`
    merged_extra = extra if isinstance(extra, dict) else extra_fields
    return _merge_extra(entity, merged_extra)


def to_investment(
    stock: Dict[str, Any],
    start_date: str,
    purchase_price: float,
    targets: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
    extra_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Construct a standard investment entity (unsettled/base).

    Required fields: stock, start_date, purchase_price, targets.completed
    Optional fields: extra (strategy-specific fields like tracking/opportunity)
    """
    entity: Dict[str, Any] = {
        'stock': stock or {},
        'start_date': start_date,
        'purchase_price': purchase_price,
        'targets': _ensure_targets_schema(targets),
    }
    merged_extra = extra if isinstance(extra, dict) else extra_fields
    return _merge_extra(entity, merged_extra)


def to_settled_investment(
    investment: Dict[str, Any],
    end_date: str,
    result: Any,
    extra_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Construct a standard settled investment entity.

    Computes settlement metrics internally from the base investment:
    - overall_profit = sum(weighted_profit) over targets.completed
      (fallback: profit * profit_contribution or profit * sell_ratio)
    - overall_profit_rate = overall_profit / purchase_price
    - invest_duration_days = days between start_date and end_date (YYYYMMDD)
    """
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

    overall_profit_rate = AnalyzerService.to_ratio(overall_profit, purchase_price, 2)

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
    return _merge_extra(settled, extra_fields)


def to_stock_summary(
    stock_id: str,
    summary_core: Dict[str, Any],
    extra_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    summary: Dict[str, Any] = dict(summary_core or {})
    summary = _merge_extra(summary, extra_fields)
    return {
        'stock_id': stock_id,
        'summary': summary,
    }


def to_session_summary(
    summary_core: Dict[str, Any],
    extra_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    summary: Dict[str, Any] = dict(summary_core or {})
    return _merge_extra(summary, extra_fields)


# ========================================================
# Helper methods:
# ========================================================

def _merge_extra(base: Dict[str, Any], extra_fields: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if extra_fields and isinstance(extra_fields, dict):
        for k, v in extra_fields.items():
            if k not in base:
                base[k] = v
    return base


def _ensure_targets_schema(targets: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    normalized = targets.copy() if isinstance(targets, dict) else {}
    completed = normalized.get('completed')
    if not isinstance(completed, list):
        normalized['completed'] = []
    return normalized
