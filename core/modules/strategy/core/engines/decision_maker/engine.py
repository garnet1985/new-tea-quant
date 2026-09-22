"""决策者会话状态机。

本文件:
- DecisionEngine: start / pick / done / reset / next / holdings / info / 终局 finalize
  边界: 人只改选谁和股数；时钟在事件日暂停（机会或仓位变化）；不把日净值写入存档
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.modules.market_profile import MarketRulesProxy
from core.modules.strategy.core.engines.decision_maker.broker import DecisionBroker
from core.modules.strategy.core.engines.decision_maker.data_class import (
    AdvanceResult,
    ExitNotice,
    GoalChip,
    HoldingRow,
    LoadBars,
    LoadClose,
    NameLookup,
    ReportLoader,
)
from core.modules.strategy.core.engines.decision_maker.exceptions import (
    AmbiguousSessionsError,
    DecisionError,
)
from core.modules.strategy.core.engines.decision_maker.info import (
    default_load_bars,
    load_info_table,
    parse_info_args,
)
from core.modules.strategy.core.engines.decision_maker.report import (
    finalize_decision_report,
    write_runtime_env,
)
from core.modules.strategy.core.engines.decision_maker.store import (
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    DecisionStore,
)
from core.modules.strategy.core.engines.decision_maker.timeline import (
    DayOpportunity,
    DecisionTimeline,
    lot_key,
)
from core.modules.strategy.core.engines.portfolio.allocation_strategy import (
    AllocationStrategy,
)
from core.modules.strategy.core.engines.portfolio.data_class import (
    Account,
    PortfolioEvent,
    Position,
    Trade,
)
from core.modules.strategy.core.engines.portfolio.fee_calculator import FeeCalculator
from core.modules.strategy.core.engines.portfolio.pipeline import PortfolioPipeline
from core.modules.strategy.core.engines.portfolio.simulator import OpenLot, PortfolioSimResult
from core.modules.strategy.core.engines.shared.enum_result_contract.enum_result import (
    EnumResult,
)
from core.modules.strategy.core.engines.shared.enum_result_contract.enum_results_manager import (
    EnumResultsManager,
)
from core.modules.strategy.core.engines.shared.services.hfq_roi import HfqRoi
from core.modules.strategy.core.engines.shared.services.safe_values.safe_bar_value import (
    SafeBarValue,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.artifacts import (
    ArtifactStore,
    EnumerateStore,
    SimulationVersionStore,
)
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore
from core.modules.strategy.core.services.discovery import DiscoveryService
from core.modules.strategy.core.services.entity_loader.global_entity_loader import (
    GlobalEntityCache,
)
from core.modules.strategy.core.services.entity_loader.sample_list_resolver import (
    SampleListResolver,
)
from core.modules.strategy.core.services.fingerprint import FingerprintCalculator

logger = logging.getLogger(__name__)

PHASE_PICKING = "picking"
PHASE_CONFIRMING = "confirming"
PHASE_COMPLETED = "completed"
_KLINE_LRU = 16
_NOTE_MAX = 2000


def _note_text(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(text) > _NOTE_MAX:
        return text[:_NOTE_MAX]
    return text


class DecisionEngine:
    """一局决策者。"""

    def __init__(
        self,
        *,
        store: DecisionStore,
        dm_id: str,
        timeline: DecisionTimeline,
        settings: StrategySettings,
        allocation: AllocationStrategy,
        fee_calculator: FeeCalculator,
        strategy_key: str = "",
        version_id: str = "",
        enum_output_dir: str = "",
        market_profile: str = "",
        name_lookup: Optional[NameLookup] = None,
        load_bars: Optional[LoadBars] = None,
        load_close: Optional[LoadClose] = None,
        load_open_dates: Optional[ReportLoader] = None,
        load_hfq_closes: Optional[ReportLoader] = None,
        load_shibor_overnight: Optional[ReportLoader] = None,
    ) -> None:
        self.store = store
        self.dm_id = str(dm_id)
        self.timeline = timeline
        self.settings = settings
        self.allocation = allocation
        self.fee_calculator = fee_calculator
        self.broker = DecisionBroker(
            allocation=allocation, fee_calculator=fee_calculator
        )
        self.strategy_key = str(strategy_key or "").strip()
        self.version_id = str(version_id or "").strip()
        self.enum_output_dir = str(enum_output_dir or "").strip()
        self.market_profile = str(market_profile or "").strip() or "china_a_stock"
        self._name_lookup = name_lookup or _default_name
        self._load_bars = load_bars or default_load_bars
        self._load_close = load_close
        self._load_open_dates = load_open_dates
        self._load_hfq_closes = load_hfq_closes
        self._load_shibor_overnight = load_shibor_overnight
        self.account = Account(
            initial_cash=float(settings.portfolio.initial_capital),
            cash=float(settings.portfolio.initial_capital),
        )
        self.open_lots: Dict[str, OpenLot] = {}
        self.trades: List[Trade] = []
        self.draft: Dict[int, int] = {}
        self.draft_notes: Dict[int, str] = {}
        self.status = STATUS_IN_PROGRESS
        self.phase = PHASE_PICKING
        self.current_date = ""
        self.completed_count = 0
        self.win_count = 0
        self._kline_cache: OrderedDict[str, List[Dict[str, Any]]] = OrderedDict()
        self._last_info_entity = ""

    # ------------------------------------------------------------------ 打开会话

    @classmethod
    def open(
        cls,
        key_or_id: str,
        *,
        version_id: Optional[str] = None,
        session_id: Optional[str] = None,
        new_session: bool = False,
        name_lookup: Optional[NameLookup] = None,
        load_bars: Optional[LoadBars] = None,
        load_close: Optional[LoadClose] = None,
    ) -> "DecisionEngine":
        bundle = cls._load_version(key_or_id, version_id=version_id)
        store: DecisionStore = bundle["store"]
        dm_id = cls._pick_session(
            store,
            session_id=session_id,
            new_session=new_session,
        )
        engine = cls(
            store=store,
            dm_id=dm_id,
            timeline=bundle["timeline"],
            settings=bundle["settings"],
            allocation=bundle["allocation"],
            fee_calculator=bundle["fee_calculator"],
            strategy_key=bundle["strategy_key"],
            version_id=bundle["version_id"],
            enum_output_dir=bundle["enum_output_dir"],
            market_profile=bundle["market_profile"],
            name_lookup=name_lookup,
            load_bars=load_bars,
            load_close=load_close,
        )
        store.mark_last(dm_id)
        if store.exists(dm_id):
            engine._restore(store.load_session(dm_id))
            return engine
        write_runtime_env(
            store.session_dir(dm_id),
            strategy_key=engine.strategy_key,
            strategy_path=bundle.get("strategy_path") or engine.strategy_key,
            version_id=engine.version_id,
            enum_output_dir=engine.enum_output_dir,
            start_date=engine.timeline.start_date,
            end_date=engine.timeline.end_date,
            market_profile=engine.market_profile,
        )
        engine._walk_to_next_decision(after_date="", include_sells_on_after=False)
        engine.save()
        return engine

    @classmethod
    def list_sessions(
        cls,
        key_or_id: str,
        *,
        version_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        bundle = cls._load_version(key_or_id, version_id=version_id)
        store: DecisionStore = bundle["store"]
        return {
            "version_id": bundle["version_id"],
            "strategy_key": bundle["strategy_key"],
            "sessions": store.list_index(),
            "last_session_id": store.last_session_id(),
            "has_completed": any(
                str(row.get("status") or "") == STATUS_COMPLETED
                for row in store.list_index()
            ),
            "has_portfolio": (Path(bundle["version_dir"]) / "portfolio").is_dir(),
        }

    @classmethod
    def delete_session(
        cls,
        key_or_id: str,
        session_id: str,
        *,
        version_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        bundle = cls._load_version(key_or_id, version_id=version_id)
        store: DecisionStore = bundle["store"]
        dm_id = str(session_id or "").strip()
        if not dm_id:
            raise DecisionError("请指定 --session")
        ok = store.delete(dm_id)
        if not ok:
            raise DecisionError(f"会话不存在: {dm_id}")
        return {"ok": True, "dm_id": dm_id, "version_id": bundle["version_id"]}

    @classmethod
    def from_parts(
        cls,
        *,
        store: DecisionStore,
        dm_id: str,
        timeline: DecisionTimeline,
        settings: StrategySettings,
        allocation: AllocationStrategy,
        fee_calculator: Optional[FeeCalculator] = None,
        **kwargs: Any,
    ) -> "DecisionEngine":
        fees = fee_calculator or allocation.fee_calculator
        engine = cls(
            store=store,
            dm_id=dm_id,
            timeline=timeline,
            settings=settings,
            allocation=allocation,
            fee_calculator=fees,
            **kwargs,
        )
        store.mark_last(dm_id)
        if store.exists(dm_id):
            engine._restore(store.load_session(dm_id))
            return engine
        engine._walk_to_next_decision(after_date="", include_sells_on_after=False)
        engine.save()
        return engine

    @classmethod
    def _pick_session(
        cls,
        store: DecisionStore,
        *,
        session_id: Optional[str],
        new_session: bool,
    ) -> str:
        explicit = str(session_id or "").strip()
        if new_session:
            return store.allocate_id()
        if explicit:
            if not store.exists(explicit) and store.get_index(explicit) is None:
                raise DecisionError(f"会话不存在: {explicit}")
            return explicit
        unfinished = store.unfinished()
        if not unfinished:
            return store.allocate_id()
        if len(unfinished) == 1:
            return str(unfinished[0].get("dm_id") or "")
        raise AmbiguousSessionsError(unfinished)

    @classmethod
    def _load_version(
        cls,
        key_or_id: str,
        *,
        version_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        info = DiscoveryService.find_strategy(key_or_id)
        if info is None:
            raise DecisionError(f"当前策略不存在或未启用: {key_or_id}")
        folder = DiscoveryService.resolve_strategy_folder(key_or_id)
        vid = str(version_id or "").strip()
        if not vid:
            merged, _ = FingerprintCalculator.merge_settings(info, None)
            usable = StrategySettings.to_usable(merged)
            entity_ids = SampleListResolver.resolve(
                info,
                usable,
                universe=GlobalEntityCache.get_stock_list(),
            )
            fp_res = FingerprintCalculator.calculate_fingerprints(
                info,
                None,
                entity_ids=entity_ids,
            )
            found = SimulationVersionStore.find_enum_version(folder, fp_res)
            if not found:
                raise DecisionError("当前 settings 没有命中的枚举产物，请先运行策略的枚举程序")
            vid = str(found)
        try:
            enum_store = EnumerateStore.resolve(folder, version_id=vid)
        except FileNotFoundError as exc:
            raise DecisionError(f"枚举产物不存在（version {vid}），请先运行策略的枚举程序") from exc
        simulations = ArtifactStore.simulations_root(folder)
        settings_raw = VersionMetaStore.read_effective_settings(simulations, vid)
        if not settings_raw:
            settings_raw = VersionMetaStore.read_settings(simulations, vid) or {}
        settings = StrategySettings.from_dict(dict(settings_raw or {}))
        settings.apply_defaults()
        events, _opps = PortfolioPipeline.build_events(enum_store, settings=settings)
        manager = EnumResultsManager.at(enum_store.output_dir)
        rows: List[EnumResult] = []
        for eid in manager.list_entities() or enum_store.entity_ids:
            rows.extend(manager.results(str(eid)))
        timeline = DecisionTimeline.from_events(
            events,
            rows=rows,
            start_date=enum_store.start_date,
            end_date=enum_store.end_date,
        )
        market = (
            str(enum_store.runtime.market_profile or "").strip() or "china_a_stock"
        )
        fees = FeeCalculator.from_fees(settings)
        allocation = AllocationStrategy.create(
            settings=settings,
            market_rules=MarketRulesProxy.for_market(market),
            fee_calculator=fees,
        )
        strategy_key = str(getattr(info, "key", "") or key_or_id).strip()
        strategy_path = str(
            getattr(info, "unique_relative_path", "") or strategy_key
        ).strip()
        version_dir = ArtifactStore.simulations_root(folder) / vid
        return {
            "store": DecisionStore.at(version_dir),
            "timeline": timeline,
            "settings": settings,
            "allocation": allocation,
            "fee_calculator": fees,
            "strategy_key": strategy_key,
            "strategy_path": strategy_path,
            "version_id": vid,
            "version_dir": version_dir,
            "enum_output_dir": str(enum_store.output_dir),
            "market_profile": market,
        }

    # ------------------------------------------------------------------ 存档

    def save(self) -> None:
        self.store.save_session(self.dm_id, self._to_payload())

    def _to_payload(self) -> Dict[str, Any]:
        return {
            "schema": 1,
            "dm_id": self.dm_id,
            "version_id": self.version_id,
            "strategy_key": self.strategy_key,
            "status": self.status,
            "phase": self.phase,
            "current_date": self.current_date,
            "cash": float(self.account.cash),
            "initial_cash": float(self.account.initial_cash),
            "draft": {str(k): int(v) for k, v in self.draft.items()},
            "draft_notes": {
                str(k): str(v)
                for k, v in self.draft_notes.items()
                if int(k) in self.draft and str(v).strip()
            },
            "positions": [
                {
                    "entity_id": pos.entity_id,
                    "shares": int(pos.shares),
                    "average_cost": float(pos.average_cost),
                    "realized_profit": float(pos.realized_profit),
                    "current_investment_id": pos.current_investment_id,
                }
                for pos in self.account.positions.values()
                if pos.shares > 0
            ],
            "open_lots": [
                {
                    "investment_id": lot.investment_id,
                    "entity_id": lot.entity_id,
                    "shares": int(lot.shares),
                    "buy_price": float(lot.buy_price),
                    "buy_date": str(lot.buy_date),
                    "entry_price_hfq": float(lot.entry_price_hfq or 0.0),
                    "initial_shares": int(lot.initial_shares or lot.shares),
                    "fired_goal_names": list(lot.fired_goal_names or ()),
                }
                for lot in self.open_lots.values()
            ],
            "trades": [t.to_dict() for t in self.trades],
            "completed_count": int(self.completed_count),
            "win_count": int(self.win_count),
        }

    def _restore(self, payload: Dict[str, Any]) -> None:
        self.status = str(payload.get("status") or STATUS_IN_PROGRESS)
        self.phase = str(payload.get("phase") or PHASE_PICKING)
        self.current_date = str(payload.get("current_date") or "")
        initial = float(
            payload.get("initial_cash")
            or self.settings.portfolio.initial_capital
        )
        self.account = Account(
            initial_cash=initial,
            cash=float(payload.get("cash") or initial),
        )
        for raw in payload.get("positions") or []:
            if not isinstance(raw, dict):
                continue
            eid = str(raw.get("entity_id") or "").strip()
            if not eid:
                continue
            self.account.positions[eid] = Position(
                entity_id=eid,
                shares=int(raw.get("shares") or 0),
                average_cost=float(raw.get("average_cost") or 0.0),
                realized_profit=float(raw.get("realized_profit") or 0.0),
                current_investment_id=raw.get("current_investment_id"),
            )
        self.open_lots = {}
        for raw in payload.get("open_lots") or []:
            if not isinstance(raw, dict):
                continue
            lot = OpenLot(
                investment_id=str(raw.get("investment_id") or "").strip(),
                entity_id=str(raw.get("entity_id") or "").strip(),
                shares=int(raw.get("shares") or 0),
                buy_price=float(raw.get("buy_price") or 0.0),
                buy_date=str(raw.get("buy_date") or ""),
                entry_price_hfq=float(raw.get("entry_price_hfq") or 0.0),
                initial_shares=int(
                    raw.get("initial_shares") or raw.get("shares") or 0
                ),
                fired_goal_names=tuple(
                    str(item).strip()
                    for item in (raw.get("fired_goal_names") or ())
                    if str(item).strip()
                ),
            )
            self.open_lots[lot_key(lot.entity_id, lot.investment_id)] = lot
        self.trades = [
            Trade.from_dict(item)
            for item in (payload.get("trades") or [])
            if isinstance(item, dict)
        ]
        self.draft = {}
        self.draft_notes = {}
        for key, value in dict(payload.get("draft") or {}).items():
            try:
                self.draft[int(key)] = int(value)
            except (TypeError, ValueError):
                continue
        for key, value in dict(payload.get("draft_notes") or {}).items():
            try:
                lid = int(key)
            except (TypeError, ValueError):
                continue
            if lid not in self.draft:
                continue
            text = _note_text(value)
            if text:
                self.draft_notes[lid] = text
        self.completed_count = int(payload.get("completed_count") or 0)
        self.win_count = int(payload.get("win_count") or 0)
        if self.status == STATUS_COMPLETED:
            self.phase = PHASE_COMPLETED

    # ------------------------------------------------------------------ 查询

    @property
    def is_completed(self) -> bool:
        return self.status == STATUS_COMPLETED or self.phase == PHASE_COMPLETED

    def _held_entity_ids(self) -> Tuple[str, ...]:
        return tuple(
            str(lot.entity_id or "").strip()
            for lot in self.open_lots.values()
            if str(lot.entity_id or "").strip()
        )

    def opportunities(self) -> List[DayOpportunity]:
        if self.is_completed or not self.current_date:
            return []
        return self.timeline.opportunities_on(
            self.current_date,
            name_lookup=self._name_lookup,
            skip_entities=self._held_entity_ids(),
        )

    def calendar_journal(self) -> List[Dict[str, Any]]:
        """事件回溯：截止当天已发现的机会数 + 已成交买卖（不含佣金）。"""
        as_of = str(self.current_date or "").strip()
        if not as_of:
            return []
        opp_counts: Dict[str, int] = {}
        for date in self.timeline.buys_by_date:
            day = str(date or "").strip()
            if not day or day > as_of:
                continue
            count = len(self.timeline.unique_buys_on(day))
            if count:
                opp_counts[day] = count
        actions_by_date: Dict[str, List[Dict[str, Any]]] = {}
        for trade in self.trades:
            day = str(getattr(trade, "date", "") or "").strip()
            if not day or day > as_of:
                continue
            side = "sell" if trade.is_sell() else "buy"
            entity_id = str(getattr(trade, "entity_id", "") or "")
            inv_id = str(getattr(trade, "investment_id", "") or "")
            action = {
                "side": side,
                "entity_id": entity_id,
                "name": self._name(entity_id, inv_id),
                "shares": int(getattr(trade, "shares", 0) or 0),
                "amount": float(getattr(trade, "amount", 0.0) or 0.0),
            }
            if side == "buy":
                note = _note_text(getattr(trade, "note", ""))
                if note:
                    action["note"] = note
            actions_by_date.setdefault(day, []).append(action)
        days = sorted(set(opp_counts) | set(actions_by_date))
        return [
            {
                "date": day,
                "opp_count": int(opp_counts.get(day) or 0),
                "actions": list(actions_by_date.get(day) or []),
            }
            for day in days
        ]

    def opportunity_by_local(self, local_id: int) -> Optional[DayOpportunity]:
        for opp in self.opportunities():
            if opp.local_id == int(local_id):
                return opp
        return None

    def resolve_target(self, token: str) -> str:
        raw = str(token or "").strip()
        if raw.isdigit():
            opp = self.opportunity_by_local(int(raw))
            if opp is None:
                raise DecisionError(f"没有编号 [{raw}]")
            return opp.entity_id
        return raw

    # ------------------------------------------------------------------ 命令

    def set_pick(
        self, local_id: int, shares: int, *, note: Optional[str] = None
    ) -> Tuple[DayOpportunity, int, float]:
        if self.is_completed:
            raise DecisionError("本局已结束，只能查看报告")
        if self.phase == PHASE_CONFIRMING:
            self.phase = PHASE_PICKING
        opp = self.opportunity_by_local(int(local_id))
        if opp is None:
            raise DecisionError(f"没有编号 [{local_id}]")
        if int(shares) <= 0:
            self.draft.pop(int(local_id), None)
            self.draft_notes.pop(int(local_id), None)
            self.phase = PHASE_PICKING
            self.save()
            return opp, 0, 0.0
        event = self._buy_event(opp)
        other_ids = [i for i in self.draft if i != int(local_id)]
        other_entities = set()
        for lid in other_ids:
            other = self.opportunity_by_local(lid)
            if other is not None:
                other_entities.add(other.entity_id)
        extra = 0 if opp.entity_id in other_entities else 1
        preview, err = self.broker.preview_buy(
            event,
            int(shares),
            self.account,
            self.open_lots,
            extra_slots=extra + len(other_entities),
            draft_entities=other_entities,
            reserved_cash=self._reserved_draft_cash(exclude_local_id=int(local_id)),
        )
        if err is not None or preview is None:
            raise DecisionError(err.message if err else "无法买入")
        self.draft[int(local_id)] = int(preview.shares)
        if note is not None:
            text = _note_text(note)
            if text:
                self.draft_notes[int(local_id)] = text
            else:
                self.draft_notes.pop(int(local_id), None)
        self.phase = PHASE_PICKING
        self.save()
        return opp, preview.shares, preview.notional

    def set_pick_cash(
        self, local_id: int, cash: float, *, note: Optional[str] = None
    ) -> Tuple[DayOpportunity, int, float]:
        """UI 填金额：按成交价与市场手数折成可买股数。"""
        if self.is_completed:
            raise DecisionError("本局已结束，只能查看报告")
        if self.phase == PHASE_CONFIRMING:
            self.phase = PHASE_PICKING
        try:
            budget = float(cash)
        except (TypeError, ValueError):
            raise DecisionError("金额须为非负数") from None
        if budget <= 0:
            return self.set_pick(int(local_id), 0, note=note)
        opp = self.opportunity_by_local(int(local_id))
        if opp is None:
            raise DecisionError(f"没有编号 [{local_id}]")
        event = self._buy_event(opp)
        price = float(event.price or 0.0)
        shares = self.allocation.shares_from_cash(
            min(budget, float(self.account.cash)),
            price,
            opp.entity_id,
        )
        if shares <= 0:
            min_lot = self.allocation.min_buy_shares(opp.entity_id)
            need = float(min_lot) * price if price > 0 else 0.0
            raise DecisionError(
                f"金额不足一手（最小 {min_lot} 股，约 {need:.0f} 元）"
            )
        sized, tag = self.allocation.apply_participation(
            shares,
            bar_volume=event.bar_volume,
            entity_id=opp.entity_id,
        )
        if tag in (
            self.allocation.liquidity.TAG_SKIP,
            self.allocation.liquidity.TAG_CLIP_ZERO,
        ) or sized <= 0:
            raise DecisionError("超过当日流动性，下不成")
        return self.set_pick(int(local_id), int(sized), note=note)

    def done(self) -> List[Tuple[DayOpportunity, int, float]]:
        if self.is_completed:
            raise DecisionError("本局已结束，只能查看报告")
        self._assert_draft_affordable()
        bill: List[Tuple[DayOpportunity, int, float]] = []
        for lid in sorted(self.draft):
            opp = self.opportunity_by_local(int(lid))
            if opp is None:
                continue
            shares = int(self.draft[lid])
            bill.append((opp, shares, float(shares) * float(opp.entry_price_raw)))
        self.phase = PHASE_CONFIRMING
        self.save()
        return bill

    def reset(self, *, keep_draft: bool = False) -> None:
        if self.is_completed:
            raise DecisionError("本局已结束，只能查看报告")
        if not keep_draft:
            self.draft = {}
            self.draft_notes = {}
        self.phase = PHASE_PICKING
        self.save()

    def next(self) -> AdvanceResult:
        if self.is_completed:
            raise DecisionError("本局已结束，只能查看报告")
        if self.phase != PHASE_CONFIRMING:
            raise DecisionError("请先输入 done 确认选择")
        had_buys = bool(self.draft)
        try:
            logs = self._commit_draft()
        except DecisionError:
            self.phase = PHASE_PICKING
            self.save()
            raise
        self.draft = {}
        self.draft_notes = {}
        more = self._walk_to_next_decision(
            after_date=self.current_date,
            include_sells_on_after=had_buys,
        )
        logs.extend(more)
        self._prune_kline_cache()
        if self.is_completed:
            self.save()
            return AdvanceResult(
                completed=True,
                current_date=self.current_date,
                logs=logs,
                opportunities=[],
            )
        self.phase = PHASE_PICKING
        self.save()
        return AdvanceResult(
            completed=False,
            current_date=self.current_date,
            logs=logs,
            opportunities=self.opportunities(),
        )

    def holdings(self) -> List[HoldingRow]:
        rows: List[HoldingRow] = []
        for lot in self.open_lots.values():
            print_close = self._close_on(lot.entity_id, self.current_date)
            roi, unrealized, market_value = self._holding_mark(lot)
            held_days, held_unit = self._held_span(lot.buy_date, self.current_date)
            rows.append(
                HoldingRow(
                    entity_id=lot.entity_id,
                    name=self._name(lot.entity_id, lot.investment_id),
                    shares=int(lot.shares),
                    buy_date=str(lot.buy_date),
                    buy_price=float(lot.buy_price),
                    hold_days=held_days,
                    hold_unit=held_unit,
                    close=print_close,
                    unrealized=unrealized,
                    roi=roi,
                    market_value=market_value,
                    goals=self._goal_chips(lot),
                    status_tags=self._status_tags(lot.entity_id, lot.investment_id),
                    note=self._buy_note_for_lot(lot),
                )
            )
        rows.sort(key=lambda row: (row.entity_id, row.buy_date))
        return rows

    def info(self, tokens: Sequence[str]) -> Dict[str, Any]:
        target, n, keep = parse_info_args(tokens)
        entity_id = self.resolve_target(target)
        as_of = self.current_date or self.timeline.end_date
        indicators = dict(self.settings.data.base.get("indicators") or {})

        def _load(eid: str, cutoff: str, limit: int) -> List[Dict[str, Any]]:
            cached = self._kline_cache.get(eid)
            if cached is not None:
                self._kline_cache.move_to_end(eid)
                return list(cached)
            rows = list(self._load_bars(eid, cutoff, limit) or [])
            self._kline_cache[eid] = rows
            while len(self._kline_cache) > _KLINE_LRU:
                self._kline_cache.popitem(last=False)
            return rows

        cols, rows = load_info_table(
            entity_id=entity_id,
            as_of=as_of,
            n=n,
            keep=keep,
            indicators_cfg=indicators,
            load_bars=_load,
        )
        self._last_info_entity = entity_id
        return {
            "entity_id": entity_id,
            "name": self._name_for_entity(entity_id),
            "status_tags": list(self._status_tags_for_entity(entity_id)),
            "as_of": as_of,
            "stats": self.timeline.asof_stats(as_of).to_dict(),
            "ticker_stats": self.timeline.asof_stats(as_of, entity_id=entity_id).to_dict(),
            "columns": cols,
            "rows": rows,
        }

    def sim_result(self) -> PortfolioSimResult:
        return PortfolioSimResult(
            account=self.account,
            trades=list(self.trades),
            equity_curve=[],
            completed_count=int(self.completed_count),
            win_count=int(self.win_count),
        )

    def finalize(self, **kwargs: Any) -> Dict[str, Any]:
        if not self.is_completed:
            raise DecisionError("区间尚未走完，不出终局报告")
        extra = dict(kwargs)
        if self._load_open_dates is not None and "load_open_dates" not in extra:
            extra["load_open_dates"] = self._load_open_dates
        if self._load_hfq_closes is not None and "load_hfq_closes" not in extra:
            extra["load_hfq_closes"] = self._load_hfq_closes
        if self._load_shibor_overnight is not None and "load_shibor_overnight" not in extra:
            extra["load_shibor_overnight"] = self._load_shibor_overnight
        return finalize_decision_report(
            self.store.session_dir(self.dm_id),
            self.sim_result(),
            settings=self.settings,
            start_date=self.timeline.start_date,
            end_date=self.timeline.end_date,
            strategy_key=self.strategy_key,
            market_profile=self.market_profile,
            **extra,
        )

    # ------------------------------------------------------------------ 时钟

    def _buy_event(self, opp: DayOpportunity) -> PortfolioEvent:
        for event in self.timeline.buys_on(self.current_date):
            if (
                str(event.entity_id) == opp.entity_id
                and str(event.investment_id) == opp.investment_id
            ):
                return event
        raise DecisionError("当日机会已失效")

    def _reserved_draft_cash(self, *, exclude_local_id: Optional[int] = None) -> float:
        """当天其他草稿已经占用的现金（含费用）。"""
        before = float(self.account.cash)
        account = deepcopy(self.account)
        lots = deepcopy(self.open_lots)
        for lid, shares in sorted(self.draft.items()):
            if exclude_local_id is not None and int(lid) == int(exclude_local_id):
                continue
            opp = self.opportunity_by_local(int(lid))
            if opp is None:
                continue
            trade, err = self.broker.apply_buy(
                self._buy_event(opp),
                int(shares),
                account,
                lots,
            )
            if err is not None or trade is None:
                continue
        return max(before - float(account.cash), 0.0)

    def _assert_draft_affordable(self) -> None:
        """整单预演：多笔加起来也必须买得起，失败不改账户。"""
        account = deepcopy(self.account)
        lots = deepcopy(self.open_lots)
        for lid, shares in sorted(self.draft.items()):
            opp = self.opportunity_by_local(int(lid))
            if opp is None:
                raise DecisionError(f"没有编号 [{lid}]")
            trade, err = self.broker.apply_buy(
                self._buy_event(opp),
                int(shares),
                account,
                lots,
            )
            if err is not None or trade is None:
                raise DecisionError(err.message if err else "无法买入")

    def _commit_draft(self) -> List[ExitNotice]:
        """提交当天买单；失败则整单回滚。"""
        picks = sorted(self.draft.items())
        if not picks:
            return []
        saved_account = deepcopy(self.account)
        saved_lots = deepcopy(self.open_lots)
        saved_trades = list(self.trades)
        saved_completed = self.completed_count
        saved_wins = self.win_count
        try:
            for lid, shares in picks:
                opp = self.opportunity_by_local(int(lid))
                if opp is None:
                    raise DecisionError(f"没有编号 [{lid}]")
                trade, err = self.broker.apply_buy(
                    self._buy_event(opp),
                    int(shares),
                    self.account,
                    self.open_lots,
                )
                if err is not None or trade is None:
                    raise DecisionError(err.message if err else "无法买入")
                text = _note_text(self.draft_notes.get(int(lid), ""))
                if text:
                    trade.note = text
                self.trades.append(trade)
        except DecisionError:
            self.account = saved_account
            self.open_lots = saved_lots
            self.trades = saved_trades
            self.completed_count = saved_completed
            self.win_count = saved_wins
            raise
        return []

    def _walk_to_next_decision(
        self,
        *,
        after_date: str,
        include_sells_on_after: bool,
    ) -> List[ExitNotice]:
        """推进到下一事件日：仓位变化（成交的卖出）或新的可交易机会。"""
        logs: List[ExitNotice] = []
        if include_sells_on_after and after_date:
            logs.extend(self._apply_sells(after_date))
        dates = self.timeline.dates_after(after_date)
        for date in dates:
            day_logs = self._apply_sells(date)
            logs.extend(day_logs)
            if day_logs or self.timeline.unique_buys_on(
                date, skip_entities=self._held_entity_ids()
            ):
                self.current_date = date
                self.phase = PHASE_PICKING
                self.status = STATUS_IN_PROGRESS
                return logs
        self._complete()
        return logs

    def _apply_sells(self, date: str) -> List[ExitNotice]:
        notices: List[ExitNotice] = []
        for event in self.timeline.sells_on(date):
            before = lot_key(event.entity_id, event.investment_id) in self.open_lots
            trade, skip = self.broker.apply_sell(
                event,
                self.account,
                self.open_lots,
                is_last=self.timeline.is_last_sell(event, after_date=date),
            )
            if skip or trade is None:
                continue
            self.trades.append(trade)
            if before and lot_key(event.entity_id, event.investment_id) not in self.open_lots:
                self.completed_count += 1
                if float(trade.profit or 0.0) > 0:
                    self.win_count += 1
            goals, reason = self.timeline.exit_label_for_event(event)
            notices.append(
                ExitNotice(
                    date=str(event.date or date),
                    entity_id=str(event.entity_id or ""),
                    name=self._name(str(event.entity_id or ""), str(event.investment_id or "")),
                    shares=int(trade.shares),
                    profit=float(trade.profit or 0.0),
                    goal_names=goals,
                    reason=reason,
                    status_tags=self._status_tags(
                        str(event.entity_id or ""), str(event.investment_id or "")
                    ),
                )
            )
        return notices

    def _buy_note_for_lot(self, lot: OpenLot) -> str:
        entity_id = str(getattr(lot, "entity_id", "") or "")
        inv_id = str(getattr(lot, "investment_id", "") or "")
        for trade in reversed(self.trades):
            if (
                trade.is_buy()
                and str(trade.entity_id or "") == entity_id
                and str(trade.investment_id or "") == inv_id
            ):
                return _note_text(getattr(trade, "note", ""))
        return ""

    def _complete(self) -> None:
        self.status = STATUS_COMPLETED
        self.phase = PHASE_COMPLETED
        self.draft = {}
        self.draft_notes = {}
        if not self.current_date:
            self.current_date = self.timeline.end_date or self.timeline.first_buy_date()
        try:
            self.finalize()
        except Exception as exc:
            logger.exception("决策者终局报告写入失败 dm_id=%s: %s", self.dm_id, exc)

    def _goal_chips(self, lot: OpenLot) -> List[GoalChip]:
        fired = self._fired_goal_names(lot)
        goal = self.settings.goal
        chips: List[GoalChip] = []
        for stage in goal.take_profit_stages:
            chips.append(_stage_chip("take_profit", "止盈", stage, fired))
        for stage in goal.stop_loss_stages:
            chips.append(_stage_chip("stop_loss", "止损", stage, fired))
        protect = goal.protect_loss
        if protect is not None:
            chips.append(
                GoalChip(
                    text=f"保护 {protect.name}: {protect.ratio:+.1%}",
                    kind="protect",
                    done=str(protect.name or "") in fired,
                )
            )
        exp = goal.expiration
        if exp is not None:
            unit = _hold_unit_label(str(exp.mode or "natural_day"))
            chips.append(
                GoalChip(
                    text=f"到期 {exp.window_days} {unit}",
                    kind="expiry",
                    done="expiration" in fired,
                )
            )
        return [item for item in chips if item.text]

    def _fired_goal_names(self, lot: OpenLot) -> set:
        names = {str(item).strip() for item in (lot.fired_goal_names or ()) if str(item).strip()}
        row = self.timeline.row_for(lot.entity_id, lot.investment_id)
        if row is None:
            return names
        sold_dates = {
            str(getattr(trade, "date", "") or "").strip()
            for trade in self.trades
            if trade.is_sell()
            and str(trade.entity_id or "") == str(lot.entity_id or "")
            and str(trade.investment_id or "") == str(lot.investment_id or "")
        }
        as_of = str(self.current_date or "")
        for goal in getattr(row, "completed_goals", ()) or ():
            day = str(getattr(goal, "date", "") or "").strip()
            if not day or (as_of and day > as_of) or day not in sold_dates:
                continue
            name = str(getattr(goal, "name", "") or "").strip()
            if name:
                names.add(name)
        return names

    def _held_span(self, buy_date: str, current: str) -> Tuple[int, str]:
        """持有时长与到期用同一把尺子；日历不可用时退回自然日。"""
        exp = self.settings.goal.expiration
        mode = str(getattr(exp, "mode", "") or "").strip().lower()
        if mode in {"trading_day", "open_day"}:
            counted = self._inclusive_open_days(buy_date, current)
            if counted > 0:
                return counted, mode
        return _hold_days(buy_date, current), "natural_day"

    def _inclusive_open_days(self, start: str, end: str) -> int:
        begin = str(start or "").strip()
        stop = str(end or "").strip()
        if not begin or not stop or begin > stop:
            return 0
        loader = self._load_open_dates or _default_load_open_dates
        try:
            rows = loader(begin, stop) or []
        except Exception as exc:
            logger.debug("开市日不可用 %s–%s: %s", begin, stop, exc)
            return 0
        dates = sorted({str(item or "").strip() for item in rows if str(item or "").strip()})
        if begin not in dates or stop not in dates:
            return 0
        return sum(1 for item in dates if begin <= item <= stop)

    def _holding_mark(
        self, lot: OpenLot
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """浮动盈亏只走 hfq ROI；缺后复权价则不报百分比。"""
        bar = self._bar_on(lot.entity_id, self.current_date)
        hfq_close = (
            SafeBarValue.optional_float(bar, "close", use_hfq=True) if bar else None
        )
        entry_hfq = float(lot.entry_price_hfq or 0.0)
        if hfq_close is None or hfq_close <= 0 or entry_hfq <= 0:
            return None, None, None
        roi = HfqRoi.ratio(entry_hfq, hfq_close)
        shares = float(lot.shares)
        entry_raw = float(lot.buy_price)
        return (
            roi,
            HfqRoi.cash_profit(shares, entry_raw, roi),
            HfqRoi.mark_value(shares, entry_raw, roi),
        )

    def _bar_on(self, entity_id: str, date: str) -> Optional[Dict[str, Any]]:
        try:
            rows = self._load_bars(entity_id, date, 8)
        except Exception as exc:
            logger.debug("持仓 K 线失败 %s %s: %s", entity_id, date, exc)
            return None
        chosen: Optional[Dict[str, Any]] = None
        for row in rows or []:
            if str(row.get("date") or "") <= str(date or ""):
                chosen = row
        return chosen

    def _close_on(self, entity_id: str, date: str) -> Optional[float]:
        if self._load_close is not None:
            try:
                value = self._load_close(entity_id, date)
            except Exception as exc:
                logger.debug("收盘价回调失败 %s %s: %s", entity_id, date, exc)
                return None
            try:
                return float(value) if value is not None else None
            except (TypeError, ValueError):
                return None
        try:
            rows = self._load_bars(entity_id, date, 8)
        except Exception as exc:
            logger.debug("收盘价 K 线失败 %s %s: %s", entity_id, date, exc)
            return None
        close = None
        for row in rows or []:
            if str(row.get("date") or "") <= str(date or ""):
                try:
                    close = float(row.get("close"))
                except (TypeError, ValueError):
                    continue
        return close

    def _name(self, entity_id: str, investment_id: str = "") -> str:
        return self.timeline.display_name(
            entity_id,
            investment_id,
            name_lookup=self._name_lookup,
        )

    def _status_tags(self, entity_id: str, investment_id: str) -> Tuple[str, ...]:
        return self.timeline.status_tags(entity_id, investment_id)

    def _status_tags_for_entity(self, entity_id: str) -> Tuple[str, ...]:
        eid = str(entity_id or "").strip()
        for opp in self.opportunities():
            if opp.entity_id == eid:
                return tuple(opp.status_tags or ())
        for lot in self.open_lots.values():
            if str(lot.entity_id) == eid:
                return self._status_tags(lot.entity_id, lot.investment_id)
        return ()

    def _name_for_entity(self, entity_id: str) -> str:
        eid = str(entity_id or "").strip()
        for opp in self.opportunities():
            if opp.entity_id == eid:
                return str(opp.name or "").strip() or self._name(eid)
        for lot in self.open_lots.values():
            if str(lot.entity_id) == eid:
                return self._name(lot.entity_id, lot.investment_id)
        return self._name(eid)

    def _prune_kline_cache(self) -> None:
        keep = {lot.entity_id for lot in self.open_lots.values()}
        if self._last_info_entity:
            keep.add(self._last_info_entity)
        for key in list(self._kline_cache):
            if key not in keep:
                self._kline_cache.pop(key, None)


def _stage_chip(kind: str, label: str, stage: Any, fired: set) -> GoalChip:
    name = str(getattr(stage, "name", "") or getattr(stage, "stage_id", "") or label)
    return GoalChip(text=_stage_line(label, stage), kind=kind, done=name in fired)


def _stage_line(kind: str, stage: Any) -> str:
    name = str(getattr(stage, "name", "") or getattr(stage, "stage_id", "") or kind)
    if getattr(stage, "custom", None) or getattr(stage, "ratio", None) is None:
        return f"{kind} {name}"
    return f"{kind} {name}: {float(stage.ratio):+.1%}"


def _hold_days(buy_date: str, current: str) -> int:
    a = _parse_ymd(buy_date)
    b = _parse_ymd(current)
    if a is None or b is None:
        return 0
    return max(0, (b - a).days)


def _hold_unit_label(unit: str) -> str:
    key = str(unit or "").strip().lower()
    if key == "trading_day":
        return "个交易日"
    if key == "open_day":
        return "个开市日"
    return "个自然日"


def _default_load_open_dates(start: str, end: str) -> List[str]:
    try:
        from core.modules.data_manager import DataManager

        dm = DataManager()
        if getattr(dm, "_data_service", None) is None:
            dm.initialize()
        cal = getattr(getattr(dm, "service", None), "calendar", None)
        if cal is None or not callable(getattr(cal, "load_open_dates", None)):
            return []
        return list(cal.load_open_dates(start, end, market="SSE") or [])
    except Exception as exc:
        logger.debug("交易日历加载失败 %s–%s: %s", start, end, exc)
        return []


def _parse_ymd(value: str) -> Optional[datetime]:
    raw = str(value or "").strip()
    if len(raw) != 8 or not raw.isdigit():
        return None
    try:
        return datetime.strptime(raw, "%Y%m%d")
    except ValueError:
        return None


def _default_name(entity_id: str) -> str:
    try:
        from core.modules.data_manager import DataManager

        dm = DataManager()
        if getattr(dm, "_data_service", None) is None:
            dm.initialize()
        info = dm.stock.load_info(entity_id)
        if isinstance(info, dict):
            from core.tables.stock.stock_st_periods.st_period_rules import bare_stock_name

            return bare_stock_name(str(info.get("name") or ""))
    except Exception as exc:
        logger.debug("证券名称加载失败 %s: %s", entity_id, exc)
        return ""
    return ""


__all__ = [
    "AdvanceResult",
    "AmbiguousSessionsError",
    "DecisionEngine",
    "DecisionError",
    "ExitNotice",
    "GoalChip",
    "HoldingRow",
    "PHASE_COMPLETED",
    "PHASE_CONFIRMING",
    "PHASE_PICKING",
]
