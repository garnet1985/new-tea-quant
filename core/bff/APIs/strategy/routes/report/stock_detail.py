"""BFF single-stock detail (V2-07c): K-line + step markers.

NEW artifacts only:
- enum: ``entities/{id}.json``
- price: ``entities/{id}_investments.csv`` + 分档卖出 ``*_goal_achievements.csv``
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.modules.data_manager import DataManager
from core.modules.indicator import Indicator
from core.modules.strategy import Strategy
from core.modules.strategy.contracts import WorkbenchStep
from core.infra.utils import Utils
from core.modules.strategy.core.engines.shared.data_class.investment.enums import (
    Lifecycle,
)
from core.modules.strategy.core.engines.shared.enum_result_contract import (
    EnumResult,
    EnumResultsManager,
)
from core.modules.strategy.core.services.artifacts import (
    ArtifactStore,
    GoalAchievementRow,
    PriceFactorStore,
    PriceInvestmentRow,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings import (
    StrategySettings,
)
from core.bff.APIs.strategy.helpers.indicator_chart_catalog import (
    apply_render_fields,
    format_indicator_label,
    next_indicator_color,
    resolve_indicator_render,
    should_skip_chart_series,
)
from core.bff.APIs.strategy.helpers.chart_layer_catalog import (
    VIZ_EVENT_PINS,
    VIZ_LINKED_OHLCV,
    VIZ_MACRO_STEP,
    VIZ_STATE_LANE,
    date_to_quarter,
    layer_envelope,
    layer_label,
    quarter_to_end_date,
    resolve_viz_role,
)
from core.bff.APIs.strategy.helpers.workbench_snapshots import WorkbenchSnapshots

logger = logging.getLogger(__name__)


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
        chart_layers = cls._load_chart_layers(
            sid, settings, backtest_period, strategy_name=strategy_name
        )
        markers = cls._enum_markers(investments, candles)
        enum_metrics = cls._enum_metrics_for_stock(investments)
        market_profile = cls._market_profile_id(settings)

        return {
            **common,
            "step_ready": True,
            "detail_available": bool(candles),
            "message": "" if candles else "K 线数据为空，请检查数据导入与回测区间",
            "stock_name": stock_name,
            "market_profile": market_profile,
            "backtest_period": backtest_period,
            "kline_params": kline_params,
            "candles": candles,
            "markers": markers,
            "indicator_series": indicator_series,
            "chart_layers": chart_layers,
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

        investments = PriceFactorStore.at(output_dir).investments(sid)
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
        chart_layers = cls._load_chart_layers(
            sid, settings, backtest_period, strategy_name=strategy_name
        )
        goal_rows = cls._load_price_completed_goals(
            price_dir=output_dir,
            entity_id=sid,
            investments=investments,
            strategy_name=strategy_name,
            snapshot_row=row,
            version=version,
        )
        markers = cls._price_markers(
            investments, candles, goal_rows=goal_rows, settings=settings
        )
        market_profile = cls._market_profile_id(settings)

        return {
            **common,
            "step_ready": True,
            "detail_available": bool(candles),
            "message": "" if candles else "K 线数据为空，请检查数据导入与回测区间",
            "stock_name": stock_name,
            "market_profile": market_profile,
            "backtest_period": backtest_period,
            "kline_params": kline_params,
            "candles": candles,
            "markers": markers,
            "indicator_series": indicator_series,
            "chart_layers": chart_layers,
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
            "chart_layers": [],
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
        for output_dir in Strategy.resolve_simulation_output_dirs(
            strategy_name,
            step=step,
            slot=slot,
            workbench_version=version,
        ):
            if not output_dir.is_dir():
                continue
            store = ArtifactStore.for_kind(step).at(output_dir)
            if store.has_investments(entity_id):
                return output_dir
        return None

    @staticmethod
    def _load_enum_investments(
        output_dir: Path, entity_id: str
    ) -> List[EnumResult]:
        try:
            rows = list(EnumResultsManager.at(output_dir).results(entity_id))
        except Exception:
            logger.exception(
                "读取枚举结果失败: %s %s", output_dir, entity_id
            )
            return []
        return [
            row
            for row in rows
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

    @staticmethod
    def _market_profile_id(settings: Optional[StrategySettings]) -> str:
        if settings is None:
            return "china_a_stock"
        raw = settings.raw_settings if isinstance(settings.raw_settings, dict) else {}
        key = str(raw.get("market_profile") or "").strip()
        return key or "china_a_stock"

    @classmethod
    def _planned_goal_levels(
        cls,
        settings: Optional[StrategySettings],
        entry_price: float,
    ) -> List[Dict[str, Any]]:
        """买入图钉价 × (1+ratio) 的计划止盈/止损线（忽略 custom / protect / dynamic）。"""
        basis = float(entry_price or 0.0)
        if settings is None or not math.isfinite(basis) or basis <= 0:
            return []
        out: List[Dict[str, Any]] = []
        try:
            goal = settings.goal
        except Exception:
            return []
        for stage in list(goal.take_profit_stages or ()):
            ratio = getattr(stage, "ratio", None)
            if ratio is None or getattr(stage, "custom", None):
                continue
            try:
                price = float(goal.exit_price(stage, basis))
            except Exception:
                continue
            if not math.isfinite(price):
                continue
            out.append(
                {
                    "kind": "take_profit",
                    "ratio": float(ratio),
                    "price": cls._round_price(price),
                    "label": str(getattr(stage, "name", "") or "").strip() or "止盈",
                }
            )
        for stage in list(goal.stop_loss_stages or ()):
            ratio = getattr(stage, "ratio", None)
            if ratio is None or getattr(stage, "custom", None):
                continue
            try:
                price = float(goal.exit_price(stage, basis))
            except Exception:
                continue
            if not math.isfinite(price):
                continue
            out.append(
                {
                    "kind": "stop_loss",
                    "ratio": float(ratio),
                    "price": cls._round_price(price),
                    "label": str(getattr(stage, "name", "") or "").strip() or "止损",
                }
            )
        return out

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
        indicators_cfg = (
            base.get("indicators") if isinstance(base.get("indicators"), dict) else {}
        )

        try:
            kline_svc = DataManager().stock.kline
            rows = list(
                kline_svc.load_qfq_split(
                    stock_id, term=term, start_date=start, end_date=end
                )
                or []
            )
        except Exception:
            logger.exception("加载单股 K 线失败: %s", stock_id)
            return [], [], {
                "data_id": data_key,
                "term": term,
            }

        candles = [c for row in rows if (c := cls._api_candle_row(row)) is not None]
        indicator_series = cls._compute_indicator_series(rows, indicators_cfg)
        return candles, indicator_series, {
            "data_id": data_key,
            "term": term,
        }

    @classmethod
    def _load_chart_layers(
        cls,
        stock_id: str,
        settings: Optional[StrategySettings],
        backtest_period: Dict[str, str],
        *,
        strategy_name: str = "",
    ) -> List[Dict[str, Any]]:
        """按 settings.data.required 装载分层数据（失败单层跳过，不拖垮主图）。"""
        start = str(backtest_period.get("start_date") or "").strip()
        end = str(backtest_period.get("end_date") or "").strip()
        if not start or not end:
            return []

        settings, required = cls._settings_and_required_for_layers(
            settings, strategy_name=strategy_name
        )
        if settings is None or not required:
            return []

        layers: List[Dict[str, Any]] = []
        for raw in required:
            if not isinstance(raw, dict):
                continue
            try:
                item = settings.data.normalize_declaration_item(raw)
            except ValueError:
                continue
            data_key = str(item.get("data_key") or "").strip()
            role = resolve_viz_role(data_key)
            if not role:
                continue
            try:
                layer = cls._build_one_chart_layer(
                    stock_id=stock_id,
                    data_key=data_key,
                    role=role,
                    start=start,
                    end=end,
                    indicators_cfg=item.get("indicators") or {},
                )
            except Exception:
                logger.exception("加载 chart layer 失败: %s %s", stock_id, data_key)
                continue
            if layer:
                layers.append(layer)
        return layers

    @classmethod
    def _settings_and_required_for_layers(
        cls,
        settings: Optional[StrategySettings],
        *,
        strategy_name: str,
    ) -> Tuple[Optional[StrategySettings], List[Any]]:
        """优先 snapshot；若无 required 则回退磁盘 settings.py（方便试分层）。"""
        required: List[Any] = []
        if settings is not None:
            try:
                required = list(settings.data.data.get("required") or [])
            except Exception:
                required = []
        if required:
            return settings, required

        name = str(strategy_name or "").strip()
        if not name:
            return settings, []
        try:
            info = Strategy.find(name)
            if isinstance(info, dict):
                raw = dict(info.get("settings") or {})
            else:
                raw = dict(getattr(info, "settings", None) or {})
            if not raw:
                return settings, []
            live = StrategySettings.from_dict(raw)
            live_required = list(live.data.data.get("required") or [])
            if live_required:
                return live, live_required
        except Exception:
            logger.debug("磁盘 settings 回退失败: %s", name, exc_info=True)
        return settings, []

    @classmethod
    def _build_one_chart_layer(
        cls,
        *,
        stock_id: str,
        data_key: str,
        role: str,
        start: str,
        end: str,
        indicators_cfg: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        label = layer_label(data_key)
        dm = DataManager()

        if role == VIZ_LINKED_OHLCV:
            term = data_key.rsplit(".", 1)[-1] or "weekly"
            rows = list(
                dm.stock.kline.load_qfq_split(
                    stock_id, term=term, start_date=start, end_date=end
                )
                or []
            )
            points = []
            for row in rows:
                date = Utils.date.normalize_str(str(row.get("date") or "")) or ""
                close = cls._round_price(cls._float_or_none(row.get("close")))
                if not date or close is None:
                    continue
                points.append({"date": date, "close": close})
            if not points:
                return None
            return layer_envelope(
                role=role,
                data_key=data_key,
                label=label,
                points=points,
            )

        if role == VIZ_MACRO_STEP:
            return cls._layer_macro_step(dm, data_key=data_key, start=start, end=end)

        if role == VIZ_STATE_LANE and data_key == "stock.st_periods":
            grouped = dm.stock.st.load_overlapping(
                [stock_id], period_start=start, period_end=end
            )
            periods = list(grouped.get(stock_id) or [])
            segments = []
            for row in periods:
                seg_start = Utils.date.normalize_str(str(row.get("start_date") or "")) or ""
                seg_end = Utils.date.normalize_str(str(row.get("end_date") or "")) or end
                if not seg_start:
                    continue
                if seg_start > end or (seg_end and seg_end < start):
                    continue
                segments.append(
                    {
                        "start": max(seg_start, start),
                        "end": min(seg_end or end, end),
                        "level": str(row.get("level") or "ST"),
                    }
                )
            if not segments:
                return None
            return layer_envelope(
                role=role,
                data_key=data_key,
                label=label,
                lanes=[
                    {
                        "key": "st",
                        "label": "ST",
                        "color": "#EF9A9A",
                        "segments": segments,
                    }
                ],
            )

        if role == VIZ_EVENT_PINS and data_key == "stock.finance.quarterly":
            q_start = date_to_quarter(start)
            q_end = date_to_quarter(end)
            if not q_start or not q_end:
                return None
            # 略放宽季度窗，避免公告日滞后丢首尾
            rows = list(
                dm.stock.corporate_finance.load_trend(
                    stock_id,
                    q_start,
                    q_end,
                    indicators=[
                        "ann_date",
                        "quarter",
                        "roe",
                        "eps",
                        "gross_profit_margin",
                        "or_yoy",
                        "netprofit_yoy",
                        "pe_ttm",
                    ],
                )
                or []
            )
            events = []
            for row in rows:
                ann = Utils.date.normalize_str(str(row.get("ann_date") or "")) or ""
                if not ann or ann < start or ann > end:
                    continue
                events.append(
                    {
                        "date": ann,
                        "label": "财报",
                        "quarter": str(row.get("quarter") or "").strip(),
                        "snapshot": {
                            "roe": cls._float_or_none(row.get("roe")),
                            "eps": cls._float_or_none(row.get("eps")),
                            "gross_profit_margin": cls._float_or_none(
                                row.get("gross_profit_margin")
                            ),
                            "or_yoy": cls._float_or_none(row.get("or_yoy")),
                            "netprofit_yoy": cls._float_or_none(row.get("netprofit_yoy")),
                            "pe_ttm": cls._float_or_none(row.get("pe_ttm")),
                        },
                    }
                )
            if not events:
                return None
            return layer_envelope(
                role=role,
                data_key=data_key,
                label=label,
                events=events,
            )

        return None

    @classmethod
    def _layer_macro_step(
        cls,
        dm: DataManager,
        *,
        data_key: str,
        start: str,
        end: str,
    ) -> Optional[Dict[str, Any]]:
        if data_key != "macro.gdp":
            # v1：先打通 GDP；其它宏观同形后续补 loader
            return None
        q_start = date_to_quarter(start)
        q_end = date_to_quarter(end)
        rows = list(dm.macro.load_gdp(start_quarter=q_start or None, end_quarter=q_end or None) or [])
        points = []
        for row in rows:
            quarter = str(row.get("quarter") or "").strip()
            date = quarter_to_end_date(quarter)
            value = cls._float_or_none(row.get("gdp_yoy"))
            if not date or value is None:
                continue
            if date < start or date > end:
                # 发布日可能在窗外，仍保留窗前最近一点供阶梯起点
                if date > end:
                    continue
            points.append(
                {
                    "date": date,
                    "value": round(float(value), 2),
                    "quarter": quarter,
                }
            )
        if not points:
            return None
        points.sort(key=lambda p: p["date"])
        return layer_envelope(
            role=VIZ_MACRO_STEP,
            data_key=data_key,
            label=layer_label(data_key),
            points=points,
            unit="%",
        )

    @classmethod
    def _enum_markers(
        cls, investments: Sequence[EnumResult], candles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        by_date = cls._candle_index_by_date(candles)
        markers: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for inv in investments:
            trigger = Utils.date.normalize_str(str(inv.trigger_date or "")) or ""
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
    def _load_price_completed_goals(
        cls,
        *,
        price_dir: Path,
        entity_id: str,
        investments: List[PriceInvestmentRow],
        strategy_name: str,
        snapshot_row: Dict[str, Any],
        version: int,
    ) -> List[GoalAchievementRow]:
        """价格层已成交目标：优先本步 goal CSV（含跌停顺延后的成交日）。"""
        sid = str(entity_id or "").strip()
        try:
            price_goals = list(PriceFactorStore.at(price_dir).goals(sid) or [])
        except Exception:
            logger.exception("读取价格回测已成交目标失败: %s %s", price_dir, sid)
            price_goals = []
        if price_goals:
            return price_goals

        enum_dir = cls._resolve_output_dir(
            strategy_name,
            "enum",
            cls._slot(snapshot_row, "enum"),
            version,
            entity_id=sid,
        )
        if enum_dir is None:
            return []
        taken = {
            str(inv.opportunity_id or "").strip()
            for inv in investments
            if str(inv.opportunity_id or "").strip()
        }
        if not taken:
            return []
        try:
            enum_rows = EnumResultsManager.at(enum_dir).results(sid)
        except Exception:
            logger.exception("读取枚举已成交目标失败: %s %s", enum_dir, sid)
            return []
        out: List[GoalAchievementRow] = []
        for row in enum_rows:
            inv_id = str(row.investment_id or "").strip()
            if inv_id not in taken:
                continue
            for goal in row.completed_goals:
                day = str(goal.date or "").strip()
                name = str(goal.name or "").strip()
                reason = str(goal.reason or "").strip() or name or "exit"
                if not day or not name:
                    continue
                out.append(
                    GoalAchievementRow(
                        investment_id=inv_id,
                        goal_name=name,
                        date=day,
                        price=float(goal.price or 0.0),
                        price_raw=float(goal.price_raw or 0.0),
                        price_hfq=float(goal.price_hfq or 0.0),
                        exit_ratio=float(goal.exit_ratio or 0.0),
                        profit=float(goal.profit or 0.0),
                        weighted_profit=float(goal.weighted_profit or 0.0),
                        reason=reason,
                        roi=float(goal.roi or 0.0),
                    )
                )
        return out

    @classmethod
    def _price_markers(
        cls,
        investments: List[PriceInvestmentRow],
        candles: List[Dict[str, Any]],
        goal_rows: Optional[Sequence[GoalAchievementRow]] = None,
        settings: Optional[StrategySettings] = None,
    ) -> List[Dict[str, Any]]:
        by_date = cls._candle_index_by_date(candles)
        goals_by_inv = cls._index_completed_goals(goal_rows or [])
        markers: List[Dict[str, Any]] = []
        for inv in investments:
            enter = Utils.date.normalize_str(str(inv.enter_date or "")) or ""
            entry_price = cls._round_price(inv.enter_price)
            if enter and enter in by_date:
                bar = by_date[enter]
                detail: Dict[str, Any] = {
                    "opportunity_id": str(inv.opportunity_id or "").strip(),
                    "entry_date": enter,
                    "entry_price": entry_price,
                    "lifecycle": str(inv.lifecycle or "").strip(),
                    "result": str(inv.result or "").strip(),
                }
                planned = cls._planned_goal_levels(
                    settings, float(inv.enter_price or 0.0)
                )
                if planned:
                    detail["planned_levels"] = planned
                markers.append(
                    {
                        "date": enter,
                        "price": cls._round_price(cls._float_or_none(bar.get("low"))),
                        "type": "buy",
                        "label": "买入",
                        "detail": detail,
                    }
                )
            inv_id = str(inv.opportunity_id or "").strip()
            goals = list(goals_by_inv.get(inv_id) or [])
            exits: List[Dict[str, Any]] = []
            if goals:
                for goal in goals:
                    marker = cls._build_price_exit_marker(
                        inv=inv, candles_by_date=by_date, goal=goal
                    )
                    if marker is not None:
                        exits.append(marker)
            else:
                marker = cls._build_price_exit_marker(
                    inv=inv, candles_by_date=by_date, goal=None
                )
                if marker is not None:
                    exits.append(marker)
            cls._finalize_investment_exit_markers(exits, inv)
            markers.extend(exits)
        return markers

    @staticmethod
    def _index_completed_goals(
        goal_rows: Sequence[GoalAchievementRow],
    ) -> Dict[str, List[GoalAchievementRow]]:
        out: Dict[str, List[GoalAchievementRow]] = {}
        for row in goal_rows or []:
            inv_id = str(getattr(row, "investment_id", "") or "").strip()
            day = str(getattr(row, "date", "") or "").strip()
            if not inv_id or not day:
                continue
            out.setdefault(inv_id, []).append(row)
        for goals in out.values():
            goals.sort(key=lambda r: str(r.date or ""))
        return out

    @classmethod
    def _normalize_exit_reason(cls, reason: str) -> str:
        hint = str(reason or "").strip().lower()
        if not hint:
            return ""
        if "protect_loss" in hint or hint.startswith("protect"):
            return "protect_loss"
        if "dynamic_loss" in hint or hint.startswith("dynamic"):
            return "dynamic_loss"
        if "take_profit" in hint or hint.startswith("win"):
            return "take_profit"
        if "stop_loss" in hint or hint.startswith("loss"):
            return "stop_loss"
        if "expir" in hint:
            return "expired"
        if "simulate_end" in hint or hint == "simulate_end":
            return "simulate_end"
        if "period_end" in hint:
            return "period_end"
        return hint

    @classmethod
    def _exit_marker_type_label(cls, reason: str) -> Tuple[str, str]:
        key = cls._normalize_exit_reason(reason)
        mapping = {
            "take_profit": ("take_profit", "止盈"),
            "stop_loss": ("stop_loss", "止损"),
            "protect_loss": ("protect_loss", "保护止损"),
            "dynamic_loss": ("dynamic_loss", "动态止损"),
            "expired": ("expired", "到期"),
            "simulate_end": ("simulate_end", "回测结束"),
            "period_end": ("period_end", "换仓清仓"),
        }
        if key in mapping:
            return mapping[key]
        return ("period_end", "出场")

    @classmethod
    def _build_price_exit_marker(
        cls,
        *,
        inv: PriceInvestmentRow,
        candles_by_date: Dict[str, Dict[str, Any]],
        goal: Optional[GoalAchievementRow],
    ) -> Optional[Dict[str, Any]]:
        if goal is not None:
            exit_d = Utils.date.normalize_str(str(goal.date or "")) or ""
            exit_price = float(goal.price or 0.0)
            exit_reason = str(goal.reason or "").strip()
            roi = float(goal.roi or 0.0)
            goal_name = str(goal.goal_name or "").strip()
            exit_ratio = float(goal.exit_ratio or 0.0)
        else:
            exit_d = Utils.date.normalize_str(str(inv.exit_date or "")) or ""
            exit_price = float(inv.exit_price or 0.0)
            exit_reason = str(inv.exit_reason or "").strip()
            roi = float(inv.roi or 0.0)
            goal_name = ""
            exit_ratio = 0.0
        if not exit_d or exit_d not in candles_by_date:
            return None
        bar = candles_by_date[exit_d]
        marker_type, label = cls._exit_marker_type_label(exit_reason)
        detail: Dict[str, Any] = {
            "opportunity_id": str(inv.opportunity_id or "").strip(),
            "exit_date": exit_d,
            "exit_price": cls._round_price(
                exit_price or cls._float_or_none(bar.get("high"))
            ),
            "exit_reason": exit_reason,
            "roi": cls._round_price(roi),
            "lifecycle": str(inv.lifecycle or "").strip(),
            "result": str(inv.result or "").strip(),
        }
        if goal_name:
            detail["goal_name"] = goal_name
        if exit_ratio > 0:
            detail["exit_ratio"] = exit_ratio
        return {
            "date": exit_d,
            "price": cls._round_price(cls._float_or_none(bar.get("high"))),
            "type": marker_type,
            "label": label,
            "detail": detail,
        }

    @classmethod
    def _finalize_investment_exit_markers(
        cls,
        exits: List[Dict[str, Any]],
        inv: PriceInvestmentRow,
    ) -> None:
        """最后一笔：到期/边界保持中性；其余按整笔投资盈亏标红绿平仓。"""
        if not exits:
            return
        last = exits[-1]
        reason = cls._normalize_exit_reason(
            str((last.get("detail") or {}).get("exit_reason") or "")
        )
        detail = last.setdefault("detail", {})
        detail["is_final"] = True
        for earlier in exits[:-1]:
            earlier.setdefault("detail", {})["is_final"] = False
        if reason in ("expired", "simulate_end"):
            if reason == "expired":
                last["type"] = "expired"
                last["label"] = "到期"
            else:
                last["type"] = "simulate_end"
                last["label"] = "回测结束"
            return
        is_profit = cls._price_row_is_profit(inv)
        last["type"] = "exit_end"
        last["label"] = "平仓·盈" if is_profit else "平仓·亏"
        detail["is_profit"] = is_profit

    @staticmethod
    def _price_row_is_profit(inv: PriceInvestmentRow) -> bool:
        """平仓色：ROI≥0 或 result=win 算赚（0 算赚）。"""
        result = str(inv.result or "").strip().lower()
        if result == "win":
            return True
        if result == "loss":
            return False
        return float(inv.roi or 0.0) >= 0.0

    @staticmethod
    def _enum_metrics_for_stock(investments: Sequence[EnumResult]) -> Dict[str, Any]:
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
            except Exception as exc:
                from core.bff.shared.client_log import log_degraded

                log_degraded("report.stockDetail.displayName.entityList", exc, stock_id)
        try:
            rec = DataManager().service.stock.list.load_single(stock_id)
            if isinstance(rec, dict):
                nm = str(rec.get("name") or "").strip()
                if nm:
                    return nm
        except Exception as exc:
            from core.bff.shared.client_log import log_degraded

            log_degraded("report.stockDetail.displayName.stockList", exc, stock_id)
        return stock_id

    @staticmethod
    def _candle_index_by_date(
        candles: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for row in candles:
            key = Utils.date.normalize_str(str(row.get("date") or "")) or ""
            if key:
                out[key] = row
        return out

    @classmethod
    def _api_candle_row(cls, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        date_key = Utils.date.normalize_str(str(row.get("date") or ""))
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
        volume = cls._float_or_none(row.get("volume"))
        out: Dict[str, Any] = {
            "date": date_key,
            "open": open_,
            "close": close,
            "high": high,
            "low": low,
        }
        if volume is not None:
            out["volume"] = volume
        return out

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
            batch = Indicator.compute_batch(klines, indicators_cfg)
        except Exception:
            logger.exception("单股指标批量计算失败")
            return []

        for name, cfg, result in batch:
            if not isinstance(cfg, dict):
                cfg = {}
            if isinstance(result, list):
                field_key = cls._indicator_field_name(name, cfg)
                render = resolve_indicator_render(
                    name, field_key=field_key, params=cfg
                )
                row = {
                    "key": field_key,
                    "label": format_indicator_label(
                        name, field_key=field_key, params=cfg
                    ),
                    "color": next_indicator_color(color_idx),
                    "data": cls._align_indicator_values(result, len(klines)),
                }
                apply_render_fields(row, render)
                if render.get("signed") and row.get("kind") == "bar":
                    row["color"] = "signed"
                series_out.append(row)
                color_idx += 1
                continue
            if isinstance(result, dict):
                for sub_key, sub_values in result.items():
                    if not isinstance(sub_values, list):
                        continue
                    # 用 pandas-ta 列名作 key，避免 name+length 再拼一次变成 vtxp_1414
                    field_key = str(sub_key).strip().lower()
                    if should_skip_chart_series(
                        name=name, sub_key=str(sub_key), field_key=field_key
                    ):
                        continue
                    render = resolve_indicator_render(
                        name,
                        sub_key=str(sub_key),
                        field_key=field_key,
                        params=cfg,
                    )
                    row = {
                        "key": field_key,
                        "label": format_indicator_label(
                            name,
                            sub_key=str(sub_key),
                            field_key=field_key,
                            params=cfg,
                        ),
                        "color": next_indicator_color(color_idx),
                        "data": cls._align_indicator_values(
                            sub_values, len(klines)
                        ),
                    }
                    apply_render_fields(row, render)
                    if render.get("signed") and row.get("kind") == "bar":
                        row["color"] = "signed"
                    series_out.append(row)
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
                length_int = int(length)
            except (TypeError, ValueError):
                length_int = None
            if length_int is not None:
                return f"{name}{length_int}"
        parts = [name]
        for key in sorted(params.keys()):
            value = params[key]
            if isinstance(value, (int, float, str)):
                parts.append(f"{key}{value}")
        return "_".join(parts)

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
