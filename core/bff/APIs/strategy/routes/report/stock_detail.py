"""BFF single-stock detail (V2-07c): K-line + step markers.

NEW artifacts only:
- enum: ``entities/{id}_stock_investments.csv``
- price: ``entities/{id}_investments.csv``
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.infra.utils.date.date_utils import DateUtils
from core.modules.data_manager import DataManager
from core.modules.indicator import IndicatorService
from core.modules.strategy.core.enums import WorkbenchStep
from core.modules.strategy.core.engines.price_factor.report_manager.investments import (
    EntityInvestments,
    PriceInvestmentRow,
)
from core.modules.strategy.core.engines.shared.data_class.investment.enums import (
    Lifecycle,
)
from core.modules.strategy.core.engines.shared.services.simulation_output import (
    EntityInvestmentCsv,
    InvestmentRow,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings import (
    StrategySettings,
)
from core.bff.APIs.strategy.helpers.report_hydrate import resolve_simulation_output_dirs
from core.bff.APIs.strategy.helpers.workbench_snapshots import WorkbenchSnapshots

logger = logging.getLogger(__name__)

_OSCILLATOR_INDICATORS = frozenset(
    {"rsi", "stoch", "stochrsi", "willr", "mfi", "cmo", "cci", "uo", "aroon"}
)
_BBANDS_OVERLAY_PREFIXES = frozenset({"bbl", "bbm", "bbu"})
_INDICATOR_LINE_COLORS = (
    "#64B5F6",
    "#BA68C8",
    "#4DD0E1",
    "#AED581",
    "#FF8A65",
    "#F06292",
)


class WorkbenchStockDetail:
    """V2-07c single-stock K-line + markers for enum / price."""

    @classmethod
    def build(
        cls,
        *,
        strategy_name: str,
        normalized_step: str,
        version: int,
        stock_id: str,
    ) -> Optional[Dict[str, Any]]:
        name = str(strategy_name or "").strip()
        sid = str(stock_id or "").strip()
        if not name or version <= 0 or not sid:
            return None

        row = WorkbenchSnapshots.fetch_by_version(name, int(version))
        if not row:
            return None

        common = {
            "version_id": f"v{int(version)}",
            "strategy_name": name,
            "step": normalized_step,
            "stock_id": sid,
        }

        if normalized_step not in (
            WorkbenchStep.ENUM.value,
            WorkbenchStep.PRICE.value,
        ):
            return {
                **common,
                "step_ready": False,
                "detail_available": False,
                "message": "该步骤单股详情尚未开放（仅枚举与价格回测）",
                "stock_name": cls._stock_display_name(sid),
                "backtest_period": cls._backtest_period(row, step=normalized_step),
                "candles": [],
                "markers": [],
                "indicator_series": [],
                "report": {"placeholder": True, "message": "即将支持"},
            }

        if normalized_step == WorkbenchStep.PRICE.value:
            return cls._build_price(name, row, sid, common, int(version))
        return cls._build_enum(name, row, sid, common, int(version))

    # ── enum ──────────────────────────────────────────────────────────

    @classmethod
    def _build_enum(
        cls,
        strategy_name: str,
        row: Dict[str, Any],
        sid: str,
        common: Dict[str, Any],
        version: int,
    ) -> Dict[str, Any]:
        slot = cls._slot(row, "enum")
        backtest_period = cls._backtest_period(row, step="enum", slot=slot)
        output_dir = cls._resolve_output_dir(
            strategy_name, "enum", slot, version, entity_id=sid
        )
        stock_name = cls._stock_display_name(sid, output_dir=output_dir, step="enum")

        if output_dir is None:
            return cls._unavailable(
                common,
                stock_name,
                backtest_period,
                message="枚举产物目录不可用，请重新执行枚举",
            )

        investments = cls._load_enum_investments(output_dir, sid)
        if not investments:
            return cls._unavailable(
                common,
                stock_name,
                backtest_period,
                message="未找到该股的枚举投资记录，请重新执行枚举",
            )

        settings = cls._settings_from_row(row)
        candles, indicator_series, kline_params = cls._load_chart(
            sid, settings, backtest_period
        )
        markers = cls._enum_markers(investments, candles)
        enum_metrics = cls._enum_metrics_for_stock(investments)

        return {
            **common,
            "step_ready": True,
            "detail_available": bool(candles),
            "message": "" if candles else "K 线数据为空，请检查数据导入与回测区间",
            "stock_name": stock_name,
            "backtest_period": backtest_period,
            "kline_params": kline_params,
            "candles": candles,
            "markers": markers,
            "indicator_series": indicator_series,
            "report": {
                "available": bool(enum_metrics),
                "enumMetrics": enum_metrics,
            },
        }

    # ── price ─────────────────────────────────────────────────────────

    @classmethod
    def _build_price(
        cls,
        strategy_name: str,
        row: Dict[str, Any],
        sid: str,
        common: Dict[str, Any],
        version: int,
    ) -> Dict[str, Any]:
        slot = cls._slot(row, "price")
        backtest_period = cls._backtest_period(row, step="price", slot=slot)
        output_dir = cls._resolve_output_dir(
            strategy_name, "price", slot, version, entity_id=sid
        )
        stock_name = cls._stock_display_name(sid)

        if output_dir is None:
            return cls._unavailable(
                common,
                stock_name,
                backtest_period,
                message="价格回测产物目录不可用，请重新执行价格回测",
            )

        investments = EntityInvestments.load(output_dir, sid)
        if not investments:
            return cls._unavailable(
                common,
                stock_name,
                backtest_period,
                message="未找到该股的价格回测交易记录，请重新执行价格回测",
            )

        settings = cls._settings_from_row(row)
        candles, indicator_series, kline_params = cls._load_chart(
            sid, settings, backtest_period
        )
        markers = cls._price_markers(investments, candles)

        return {
            **common,
            "step_ready": True,
            "detail_available": bool(candles),
            "message": "" if candles else "K 线数据为空，请检查数据导入与回测区间",
            "stock_name": stock_name,
            "backtest_period": backtest_period,
            "kline_params": kline_params,
            "candles": candles,
            "markers": markers,
            "indicator_series": indicator_series,
            "report": {"available": False, "message": "价格回测单股指标报告即将支持"},
        }

    # ── shared helpers ────────────────────────────────────────────────

    @staticmethod
    def _unavailable(
        common: Dict[str, Any],
        stock_name: str,
        backtest_period: Dict[str, str],
        *,
        message: str,
    ) -> Dict[str, Any]:
        return {
            **common,
            "step_ready": True,
            "detail_available": False,
            "message": message,
            "stock_name": stock_name,
            "backtest_period": backtest_period,
            "candles": [],
            "markers": [],
            "indicator_series": [],
            "report": {"available": False, "message": message},
        }

    @staticmethod
    def _slot(row: Dict[str, Any], step: str) -> Dict[str, Any]:
        rr = dict(row.get("result_report") or {})
        parsed = WorkbenchStep.try_parse(step)
        key = parsed.report_slot if parsed is not None else ""
        raw = rr.get(key)
        return dict(raw) if isinstance(raw, dict) else {}

    @classmethod
    def _resolve_output_dir(
        cls,
        strategy_name: str,
        step: str,
        slot: Dict[str, Any],
        version: int,
        *,
        entity_id: str,
    ) -> Optional[Path]:
        for output_dir in resolve_simulation_output_dirs(
            strategy_name,
            step=step,
            slot=slot,
            workbench_version=version,
        ):
            if not output_dir.is_dir():
                continue
            if step == "enum":
                path = EntityInvestmentCsv.file_path(output_dir, entity_id)
            else:
                path = EntityInvestments.path(output_dir, entity_id)
            if path.is_file():
                return output_dir
        return None

    @staticmethod
    def _load_enum_investments(
        output_dir: Path, entity_id: str
    ) -> List[InvestmentRow]:
        path = EntityInvestmentCsv.file_path(output_dir, entity_id)
        if not path.is_file():
            return []
        try:
            loaded = EntityInvestmentCsv.load(output_dir, entity_id)
        except Exception:
            logger.exception("读取枚举投资 CSV 失败: %s", path)
            return []
        return [
            row
            for row in loaded.rows
            if row.investment_id or row.trigger_date or row.entry_date
        ]

    @classmethod
    def _backtest_period(
        cls,
        row: Dict[str, Any],
        *,
        step: str = "",
        slot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        if isinstance(slot, dict):
            bp = slot.get("backtest_period")
            if isinstance(bp, dict):
                start = str(bp.get("start_date") or "").strip()
                end = str(bp.get("end_date") or "").strip()
                if start and end:
                    return {"start_date": start, "end_date": end}

        settings = cls._settings_from_row(row)
        if settings is None:
            return {"start_date": "", "end_date": ""}
        try:
            return settings.resolve_period().to_dict()
        except Exception:
            logger.debug("resolve_period failed", exc_info=True)
            return {"start_date": "", "end_date": ""}

    @staticmethod
    def _settings_from_row(row: Dict[str, Any]) -> Optional[StrategySettings]:
        raw = row.get("settings_snapshot")
        if not isinstance(raw, dict) or not raw:
            return None
        try:
            return StrategySettings.from_dict(raw)
        except Exception:
            logger.debug("StrategySettings.from_dict failed", exc_info=True)
            return None

    @classmethod
    def _load_chart(
        cls,
        stock_id: str,
        settings: Optional[StrategySettings],
        backtest_period: Dict[str, str],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, str]]:
        start = str(backtest_period.get("start_date") or "").strip()
        end = str(backtest_period.get("end_date") or "").strip()
        if not start or not end or settings is None:
            return [], [], {}

        base = settings.data.normalize_base(settings.data.base)
        params = base.get("params") if isinstance(base.get("params"), dict) else {}
        data_key = str(base.get("data_key") or "stock.kline.daily")
        term = str(params.get("term") or data_key.rsplit(".", 1)[-1] or "daily").strip()
        adjust = str(params.get("adjust") or "qfq").strip().lower() or "qfq"
        indicators_cfg = (
            base.get("indicators") if isinstance(base.get("indicators"), dict) else {}
        )

        try:
            kline_svc = DataManager().stock.kline
            if adjust == "qfq":
                rows = list(
                    kline_svc.load_qfq_split(
                        stock_id, term=term, start_date=start, end_date=end
                    )
                    or []
                )
            else:
                rows = list(
                    kline_svc.load_raw(
                        stock_id, term=term, start_date=start, end_date=end
                    )
                    or []
                )
        except Exception:
            logger.exception("加载单股 K 线失败: %s", stock_id)
            return [], [], {
                "data_id": data_key,
                "term": term,
                "adjust": adjust,
            }

        candles = [c for row in rows if (c := cls._api_candle_row(row)) is not None]
        indicator_series = cls._compute_indicator_series(rows, indicators_cfg)
        return candles, indicator_series, {
            "data_id": data_key,
            "term": term,
            "adjust": adjust,
        }

    @classmethod
    def _enum_markers(
        cls, investments: List[InvestmentRow], candles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        by_date = cls._candle_index_by_date(candles)
        markers: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for inv in investments:
            trigger = DateUtils.normalize_str(str(inv.trigger_date or "")) or ""
            if not trigger or trigger in seen:
                continue
            seen.add(trigger)
            bar = by_date.get(trigger)
            chart_close = cls._round_price(cls._float_or_none(bar.get("close"))) if bar else None
            chart_high = cls._round_price(cls._float_or_none(bar.get("high"))) if bar else None
            marker_price = chart_high if chart_high is not None else chart_close
            if marker_price is None:
                continue
            markers.append(
                {
                    "date": trigger,
                    "price": marker_price,
                    "type": "opportunity",
                    "label": "机会",
                    "detail": {
                        "investment_id": str(inv.investment_id or "").strip(),
                        "trigger_date": trigger,
                        "chart_close": chart_close,
                        "engine_trigger_price": cls._round_price(inv.trigger_price),
                        "entry_date": str(inv.entry_date or "").strip(),
                        "exit_date": str(inv.exit_date or "").strip(),
                        "lifecycle": str(inv.lifecycle or "").strip(),
                        "result": str(inv.result or "").strip(),
                        "exit_reason": str(inv.exit_reason or "").strip(),
                    },
                }
            )
        return markers

    @classmethod
    def _price_markers(
        cls,
        investments: List[PriceInvestmentRow],
        candles: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        by_date = cls._candle_index_by_date(candles)
        markers: List[Dict[str, Any]] = []
        for inv in investments:
            enter = DateUtils.normalize_str(str(inv.enter_date or "")) or ""
            if enter and enter in by_date:
                bar = by_date[enter]
                markers.append(
                    {
                        "date": enter,
                        "price": cls._round_price(cls._float_or_none(bar.get("low"))),
                        "type": "buy",
                        "label": "买入",
                        "detail": {
                            "opportunity_id": str(inv.opportunity_id or "").strip(),
                            "entry_date": enter,
                            "entry_price": cls._round_price(inv.enter_price),
                            "lifecycle": str(inv.lifecycle or "").strip(),
                            "result": str(inv.result or "").strip(),
                        },
                    }
                )
            exit_d = DateUtils.normalize_str(str(inv.exit_date or "")) or ""
            if exit_d and exit_d in by_date:
                bar = by_date[exit_d]
                is_win = cls._price_row_is_win(inv)
                markers.append(
                    {
                        "date": exit_d,
                        "price": cls._round_price(cls._float_or_none(bar.get("high"))),
                        "type": "target_win" if is_win else "target_loss",
                        "label": "目标胜" if is_win else "目标负",
                        "detail": {
                            "opportunity_id": str(inv.opportunity_id or "").strip(),
                            "exit_date": exit_d,
                            "exit_price": cls._round_price(inv.exit_price),
                            "exit_reason": str(inv.exit_reason or "").strip(),
                            "roi": cls._round_price(inv.roi),
                            "lifecycle": str(inv.lifecycle or "").strip(),
                            "result": str(inv.result or "").strip(),
                        },
                    }
                )
        return markers

    @staticmethod
    def _price_row_is_win(inv: PriceInvestmentRow) -> bool:
        result = str(inv.result or "").strip().lower()
        if result == "win":
            return True
        if result == "loss":
            return False
        return float(inv.roi or 0.0) > 0

    @staticmethod
    def _enum_metrics_for_stock(investments: List[InvestmentRow]) -> Dict[str, Any]:
        total = len(investments)
        if total <= 0:
            return {}
        completed = [
            row
            for row in investments
            if str(row.lifecycle or "").strip() == Lifecycle.COMPLETE.value
        ]
        unfinished = total - len(completed)
        wins = 0
        losses = 0
        for row in completed:
            result = str(row.result or "").strip().lower()
            if result == "win" or (not result and row.weighted_roi > 0):
                wins += 1
            elif result == "loss" or (not result and row.weighted_roi < 0):
                losses += 1
        sample = wins + losses
        win_rate = round((wins / sample) * 100.0, 1) if sample else 0.0
        return {
            "totalOpportunities": total,
            "totalStocks": 1,
            "triggerStocks": 1 if total else 0,
            "triggerRatio": 100.0 if total else 0.0,
            "avgPerStock": float(total),
            "completedRatio": round((len(completed) / total) * 100.0, 1) if total else 0.0,
            "completedCount": len(completed),
            "unfinishedCount": unfinished,
            "winCount": wins,
            "lossCount": losses,
            "winRateSampleCount": sample,
            "winRate": win_rate,
        }

    @classmethod
    def _stock_display_name(
        cls,
        stock_id: str,
        *,
        output_dir: Optional[Path] = None,
        step: str = "",
    ) -> str:
        if output_dir is not None and step == "enum":
            try:
                from core.modules.strategy.core.engines.enumerator.common.report_manager.entity_list_report import (
                    EntityListReport,
                )

                ref = EntityListReport.load(output_dir).to_ui_dict()
                payload = ref.get(stock_id)
                if isinstance(payload, dict):
                    nm = str(payload.get("stock_name") or "").strip()
                    if nm and nm != stock_id:
                        return nm
            except Exception:
                pass
        try:
            rec = DataManager().service.stock.list.load_single(stock_id)
            if isinstance(rec, dict):
                nm = str(rec.get("name") or "").strip()
                if nm:
                    return nm
        except Exception:
            pass
        return stock_id

    @staticmethod
    def _candle_index_by_date(
        candles: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for row in candles:
            key = DateUtils.normalize_str(str(row.get("date") or "")) or ""
            if key:
                out[key] = row
        return out

    @classmethod
    def _api_candle_row(cls, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        date_key = DateUtils.normalize_str(str(row.get("date") or ""))
        if not date_key:
            return None
        open_ = cls._round_price(cls._float_or_none(row.get("open")))
        close = cls._round_price(cls._float_or_none(row.get("close")))
        if open_ is None or close is None:
            return None
        high = cls._round_price(cls._float_or_none(row.get("high")))
        low = cls._round_price(cls._float_or_none(row.get("low")))
        if high is None:
            high = close
        if low is None:
            low = close
        if high is not None and low is not None and high < low:
            high, low = low, high
        return {
            "date": date_key,
            "open": open_,
            "close": close,
            "high": high,
            "low": low,
        }

    @staticmethod
    def _float_or_none(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            fv = float(value)
        except (TypeError, ValueError):
            return None
        if math.isnan(fv) or math.isinf(fv):
            return None
        return fv

    @classmethod
    def _round_price(cls, value: Any) -> Optional[float]:
        fv = cls._float_or_none(value) if not isinstance(value, float) else value
        if fv is None:
            return None
        if math.isnan(fv) or math.isinf(fv):
            return None
        return round(float(fv), 2)

    @classmethod
    def _compute_indicator_series(
        cls,
        klines: List[Dict[str, Any]],
        indicators_cfg: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        if not klines or not indicators_cfg:
            return []
        series_out: List[Dict[str, Any]] = []
        color_idx = 0
        try:
            batch = IndicatorService.compute_batch(klines, indicators_cfg)
        except Exception:
            logger.exception("单股指标批量计算失败")
            return []

        for name, cfg, result in batch:
            if not isinstance(cfg, dict):
                cfg = {}
            if isinstance(result, list):
                series_out.append(
                    {
                        "key": cls._indicator_field_name(name, cfg),
                        "label": cls._indicator_label(name, cfg),
                        "panel": cls._indicator_panel(name),
                        "color": _INDICATOR_LINE_COLORS[
                            color_idx % len(_INDICATOR_LINE_COLORS)
                        ],
                        "data": cls._align_indicator_values(result, len(klines)),
                    }
                )
                color_idx += 1
                continue
            if isinstance(result, dict):
                for sub_key, sub_values in result.items():
                    if not isinstance(sub_values, list):
                        continue
                    series_out.append(
                        {
                            "key": cls._indicator_field_name(f"{name}_{sub_key}", cfg),
                            "label": cls._indicator_label(
                                name, cfg, suffix=str(sub_key)
                            ),
                            "panel": cls._indicator_panel_for_series(
                                name, sub_key=str(sub_key)
                            ),
                            "color": _INDICATOR_LINE_COLORS[
                                color_idx % len(_INDICATOR_LINE_COLORS)
                            ],
                            "data": cls._align_indicator_values(
                                sub_values, len(klines)
                            ),
                        }
                    )
                    color_idx += 1
        return [
            row for row in series_out if any(v is not None for v in row.get("data") or [])
        ]

    @staticmethod
    def _indicator_field_name(name: str, params: Dict[str, Any]) -> str:
        name = str(name or "").lower()
        length = params.get("length")
        if length is not None:
            try:
                return f"{name}{int(length)}"
            except (TypeError, ValueError):
                pass
        parts = [name]
        for key in sorted(params.keys()):
            value = params[key]
            if isinstance(value, (int, float, str)):
                parts.append(f"{key}{value}")
        return "_".join(parts)

    @staticmethod
    def _indicator_panel(name: str) -> str:
        base = str(name or "").lower().split("_")[0]
        return "oscillator" if base in _OSCILLATOR_INDICATORS else "overlay"

    @classmethod
    def _indicator_panel_for_series(cls, name: str, *, sub_key: str = "") -> str:
        base = str(name or "").lower()
        if base == "bbands" and sub_key:
            prefix = str(sub_key).lower().split("_")[0]
            return "overlay" if prefix in _BBANDS_OVERLAY_PREFIXES else "oscillator"
        return cls._indicator_panel(name)

    @staticmethod
    def _indicator_label(name: str, params: Dict[str, Any], *, suffix: str = "") -> str:
        base = str(name or "").upper()
        length = params.get("length")
        if suffix:
            return (
                f"{base} {suffix.upper()}({length})"
                if length is not None
                else f"{base} {suffix.upper()}"
            )
        return f"{base}({int(length)})" if length is not None else base

    @classmethod
    def _align_indicator_values(
        cls, values: List[Any], size: int
    ) -> List[Optional[float]]:
        out: List[Optional[float]] = []
        for idx in range(size):
            raw = values[idx] if idx < len(values) else None
            out.append(cls._round_price(cls._float_or_none(raw)))
        return out


__all__ = ["WorkbenchStockDetail"]
