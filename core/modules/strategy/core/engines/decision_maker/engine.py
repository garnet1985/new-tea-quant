"""决策者会话状态机。

本文件:
- DecisionEngine: start / pick / done / reset / next / holdings / info / 终局 finalize
  边界: 人只改选谁和股数；时钟只在抉择日暂停；不把日净值写入存档
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
from core.modules.strategy.core.services.fingerprint import FingerprintCalculator

logger = logging.getLogger(__name__)

PHASE_PICKING = "picking"
PHASE_CONFIRMING = "confirming"
PHASE_COMPLETED = "completed"
_KLINE_LRU = 16


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
            stock_list = GlobalEntityCache.get_stock_list()
            fp_res = FingerprintCalculator.calculate_fingerprints(
                info,
                None,
                entity_ids=stock_list,
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
            )
            self.open_lots[lot_key(lot.entity_id, lot.investment_id)] = lot
        self.trades = [
            Trade.from_dict(item)
            for item in (payload.get("trades") or [])
            if isinstance(item, dict)
        ]
        self.draft = {}
        for key, value in dict(payload.get("draft") or {}).items():
            try:
                self.draft[int(key)] = int(value)
            except (TypeError, ValueError):
                continue
        self.completed_count = int(payload.get("completed_count") or 0)
        self.win_count = int(payload.get("win_count") or 0)
        if self.status == STATUS_COMPLETED:
            self.phase = PHASE_COMPLETED

    # ------------------------------------------------------------------ 查询

    @property
    def is_completed(self) -> bool:
        return self.status == STATUS_COMPLETED or self.phase == PHASE_COMPLETED

    def opportunities(self) -> List[DayOpportunity]:
        if self.is_completed or not self.current_date:
            return []
        return self.timeline.opportunities_on(
            self.current_date, name_lookup=self._name_lookup
        )

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

    def set_pick(self, local_id: int, shares: int) -> Tuple[DayOpportunity, int, float]:
        if self.is_completed:
            raise DecisionError("本局已结束，只能查看报告")
        if self.phase == PHASE_CONFIRMING:
            raise DecisionError("请输入 next 继续推进，或 reset 重新下单")
        opp = self.opportunity_by_local(int(local_id))
        if opp is None:
            raise DecisionError(f"没有编号 [{local_id}]")
        if int(shares) <= 0:
            self.draft.pop(int(local_id), None)
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
        )
        if err is not None or preview is None:
            raise DecisionError(err.message if err else "无法买入")
        self.draft[int(local_id)] = int(preview.shares)
        self.phase = PHASE_PICKING
        self.save()
        return opp, preview.shares, preview.notional

    def done(self) -> List[Tuple[DayOpportunity, int, float]]:
        if self.is_completed:
            raise DecisionError("本局已结束，只能查看报告")
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

    def reset(self) -> None:
        if self.is_completed:
            raise DecisionError("本局已结束，只能查看报告")
        self.draft = {}
        self.phase = PHASE_PICKING
        self.save()

    def next(self) -> AdvanceResult:
        if self.is_completed:
            raise DecisionError("本局已结束，只能查看报告")
        if self.phase != PHASE_CONFIRMING:
            raise DecisionError("请先输入 done 确认选择")
        logs = self._commit_draft()
        self.draft = {}
        more = self._walk_to_next_decision(
            after_date=self.current_date,
            include_sells_on_after=True,
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
            close = self._close_on(lot.entity_id, self.current_date)
            unrealized = None
            if close is not None:
                unrealized = (float(close) - float(lot.buy_price)) * float(lot.shares)
            rows.append(
                HoldingRow(
                    entity_id=lot.entity_id,
                    name=self._name(lot.entity_id),
                    shares=int(lot.shares),
                    buy_date=str(lot.buy_date),
                    buy_price=float(lot.buy_price),
                    hold_days=_hold_days(lot.buy_date, self.current_date),
                    close=close,
                    unrealized=unrealized,
                    goals=self._goal_lines(lot),
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
            "name": self._name(entity_id),
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
        logs: List[ExitNotice] = []
        if include_sells_on_after and after_date:
            logs.extend(self._apply_sells(after_date))
        dates = self.timeline.dates_after(after_date)
        for date in dates:
            logs.extend(self._apply_sells(date))
            if self.timeline.buys_on(date):
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
            trade, skip = self.broker.apply_sell(event, self.account, self.open_lots)
            if skip or trade is None:
                continue
            self.trades.append(trade)
            if before and lot_key(event.entity_id, event.investment_id) not in self.open_lots:
                self.completed_count += 1
                if float(trade.profit or 0.0) > 0:
                    self.win_count += 1
            goals, reason = self.timeline.exit_label(event.entity_id, event.investment_id)
            notices.append(
                ExitNotice(
                    date=str(event.date or date),
                    entity_id=str(event.entity_id or ""),
                    name=self._name(str(event.entity_id or "")),
                    shares=int(trade.shares),
                    profit=float(trade.profit or 0.0),
                    goal_names=goals,
                    reason=reason,
                )
            )
        return notices

    def _complete(self) -> None:
        self.status = STATUS_COMPLETED
        self.phase = PHASE_COMPLETED
        self.draft = {}
        if not self.current_date:
            self.current_date = self.timeline.end_date or self.timeline.first_buy_date()
        try:
            self.finalize()
        except Exception as exc:
            logger.exception("决策者终局报告写入失败 dm_id=%s: %s", self.dm_id, exc)

    def _goal_lines(self, lot: OpenLot) -> List[str]:
        goal = self.settings.goal
        basis = float(lot.entry_price_hfq or 0.0) or float(lot.buy_price or 0.0)
        lines: List[str] = []
        for stage in goal.take_profit_stages:
            lines.append(_stage_line("止盈", stage, basis, goal.exit_price))
        for stage in goal.stop_loss_stages:
            lines.append(_stage_line("止损", stage, basis, goal.exit_price))
        protect = goal.protect_loss
        if protect is not None:
            lines.append(f"保护 {protect.name}: {protect.ratio:+.1%}")
        exp = goal.expiration
        if exp is not None:
            lines.append(f"到期 {exp.window_days} {exp.mode}")
        return [item for item in lines if item]

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

    def _name(self, entity_id: str) -> str:
        try:
            return str(self._name_lookup(entity_id) or "").strip()
        except Exception as exc:
            logger.debug("证券名称不可用 %s: %s", entity_id, exc)
            return ""

    def _prune_kline_cache(self) -> None:
        keep = {lot.entity_id for lot in self.open_lots.values()}
        if self._last_info_entity:
            keep.add(self._last_info_entity)
        for key in list(self._kline_cache):
            if key not in keep:
                self._kline_cache.pop(key, None)


def _stage_line(
    kind: str,
    stage: Any,
    basis: float,
    exit_price_fn: Any,
) -> str:
    name = str(getattr(stage, "name", "") or getattr(stage, "stage_id", "") or kind)
    if getattr(stage, "custom", None) or getattr(stage, "ratio", None) is None:
        return f"{kind} {name}"
    ratio = float(stage.ratio)
    price = None
    if basis > 0:
        try:
            price = float(exit_price_fn(stage, basis))
        except (TypeError, ValueError, KeyError) as exc:
            logger.debug("目标价不可用 %s: %s", name, exc)
            price = None
    if price is None:
        return f"{kind} {name}: {ratio:+.1%}"
    return f"{kind} {name}: {ratio:+.1%} → {price:.2f}"


def _hold_days(buy_date: str, current: str) -> int:
    a = _parse_ymd(buy_date)
    b = _parse_ymd(current)
    if a is None or b is None:
        return 0
    return max(0, (b - a).days)


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
            return str(info.get("name") or "").strip()
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
    "HoldingRow",
    "PHASE_COMPLETED",
    "PHASE_CONFIRMING",
    "PHASE_PICKING",
]
