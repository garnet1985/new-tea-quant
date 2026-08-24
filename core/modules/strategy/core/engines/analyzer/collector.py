"""归因 input 收集：join 产物表，不写统计。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from core.modules.strategy.core.enums import SimulateKind, WorkbenchStep
from core.modules.strategy.core.services.artifacts import (
    ENTITIES_SUBDIR,
    GOAL_ACHIEVEMENTS_SUFFIX,
    PRICE_INVESTMENTS_SUFFIX,
    SIGNAL_SNAPSHOTS_SUFFIX,
    STOCK_INVESTMENTS_SUFFIX,
    ArtifactStore,
    EnumerateStore,
    GoalAchievementRow,
    InvestmentRow,
    PriceFactorStore,
    PriceInvestmentRow,
)
from core.modules.strategy.core.services.artifacts.tables.signal_snapshots import (
    SignalSnapshotRow,
)

from .consts import SCHEMA_VERSION
from .step import step_value


class AttributionInputCollector:
    """从 ArtifactStore 句柄重组归因 input（无 IO 定位逻辑）。"""

    def __init__(self, store: ArtifactStore) -> None:
        self.store = store
        self._runtime_raw = store.read_json("runtime_env")

    def collect(self) -> Dict[str, Any]:
        kind = self.store.kind
        if kind is SimulateKind.ENUMERATE:
            return self._collect_enumerate()
        if kind is SimulateKind.PRICE_FACTOR:
            return self._collect_price()
        if kind is SimulateKind.PORTFOLIO:
            return self._collect_portfolio()
        raise ValueError(f"unsupported analysis step: {kind!r}")

    def _collect_enumerate(self) -> Dict[str, Any]:
        enum_store = self._as_enumerate_store()
        entities = self._collect_enum_entities(enum_store)
        capture_keys, with_snapshot, total = self._capture_stats(entities)
        payload = self._base_payload(
            artifact_paths={
                "runtime_env": "runtime_env.json",
                "investments": f"{ENTITIES_SUBDIR}/*{STOCK_INVESTMENTS_SUFFIX}",
                "goal_achievements": f"{ENTITIES_SUBDIR}/*{GOAL_ACHIEVEMENTS_SUFFIX}",
                "signal_snapshots": f"{ENTITIES_SUBDIR}/*{SIGNAL_SNAPSHOTS_SUFFIX}",
            },
        )
        payload["inputs"]["capture"] = {
            "keys": capture_keys,
            "coverage": {
                "investment_count": total,
                "with_snapshot": with_snapshot,
            },
        }
        payload["entities"] = entities
        return payload

    def _collect_price(self) -> Dict[str, Any]:
        price_store = self._as_price_store()
        enum_store = self._open_upstream_enum_store()
        entities = self._collect_price_entities(price_store, enum_store)
        capture_keys, with_snapshot, total = self._capture_stats(entities)
        payload = self._base_payload(
            artifact_paths={
                "runtime_env": "runtime_env.json",
                "investments": f"{ENTITIES_SUBDIR}/*{PRICE_INVESTMENTS_SUFFIX}",
            },
            upstream=self._upstream_block(enum_store),
        )
        payload["inputs"]["capture"] = {
            "keys": capture_keys,
            "coverage": {
                "investment_count": total,
                "with_snapshot": with_snapshot,
            },
            "join": {
                "source_step": WorkbenchStep.ENUM.value,
                "join_key": "investment_id",
                "price_field": "opportunity_id",
            },
        }
        payload["entities"] = entities
        return payload

    def _collect_portfolio(self) -> Dict[str, Any]:
        enum_store = self._open_upstream_enum_store()
        payload = self._base_payload(
            artifact_paths={
                "runtime_env": "runtime_env.json",
                "trades": "trades.json",
                "equity_curve": "equity_curve.json",
            },
            upstream=self._upstream_block(enum_store),
        )
        trades_path = self.store.file("trades")
        equity_path = self.store.file("equity_curve")
        payload["inputs"]["portfolio_artifacts"] = {
            "trades_present": trades_path.is_file(),
            "equity_curve_present": equity_path.is_file(),
        }
        if trades_path.is_file():
            trades = self.store.read_json("trades")
            trade_rows = trades.get("trades") if isinstance(trades, dict) else trades
            payload["inputs"]["portfolio_artifacts"]["trade_count"] = (
                len(trade_rows) if isinstance(trade_rows, list) else 0
            )
        payload["entities"] = []
        payload["inputs"]["capture"] = {
            "keys": [],
            "coverage": {"investment_count": 0, "with_snapshot": 0},
            "note": "portfolio layer defers per-trade join to a later phase",
        }
        return payload

    def _base_payload(
        self,
        *,
        artifact_paths: Dict[str, str],
        upstream: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raw = self._runtime_raw
        fps = raw.get("fingerprints") if isinstance(raw.get("fingerprints"), dict) else {}
        period = raw.get("period") if isinstance(raw.get("period"), dict) else {}
        settings_raw = raw.get("settings") if isinstance(raw.get("settings"), dict) else {}
        effective = settings_raw.get("effective_settings")
        if not isinstance(effective, dict):
            effective = self.store.runtime.settings_snapshot.effective_settings

        payload: Dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "strategy_key": str(raw.get("strategy_key") or self.store.runtime.strategy_key or "").strip(),
            "strategy_path": str(raw.get("strategy_path") or self.store.runtime.strategy_path or "").strip(),
            "step": step_value(self.store.kind),
            "version_id": str(self.store.version_id),
            "output_dir": str(self.store.output_dir.resolve()),
            "fingerprints": {
                "settings": str(fps.get("settings") or raw.get("settings_fp") or "").strip(),
                "env": str(fps.get("env") or raw.get("env_fp") or "").strip(),
            },
            "period": {
                "start_date": str(period.get("start_date") or self.store.start_date or "").strip(),
                "end_date": str(period.get("end_date") or self.store.end_date or "").strip(),
            },
            "inputs": {
                "artifact_paths": artifact_paths,
                "declared": _declared_manifest(effective),
            },
            "entities": [],
        }
        if upstream:
            payload["upstream"] = upstream
        return payload

    def _upstream_block(self, enum_store: Optional[EnumerateStore]) -> Dict[str, Any]:
        raw = self._runtime_raw
        enum_version_id = str(raw.get("enum_version_id") or "").strip()
        enum_output_dir = str(raw.get("enum_output_dir") or "").strip()
        if enum_store is not None:
            enum_version_id = enum_version_id or str(enum_store.version_id)
            enum_output_dir = enum_output_dir or str(enum_store.output_dir.resolve())
        block: Dict[str, Any] = {
            "enum_version_id": enum_version_id,
        }
        if enum_output_dir:
            block["enum_output_dir"] = enum_output_dir
        price_version_id = str(raw.get("price_version_id") or "").strip()
        price_output_dir = str(raw.get("price_output_dir") or "").strip()
        if price_version_id:
            block["price_version_id"] = price_version_id
        if price_output_dir:
            block["price_output_dir"] = price_output_dir
        return block

    def _collect_enum_entities(self, store: EnumerateStore) -> List[Dict[str, Any]]:
        entities: List[Dict[str, Any]] = []
        for entity_id in store.list_investment_entities():
            investments = store.investments(entity_id).rows
            if not investments:
                continue
            goals = store.goals(entity_id).rows
            snapshots = _snapshot_index(store.snapshots(entity_id).rows)
            goal_index = _goal_index(goals)
            rows = [
                _join_enum_investment(
                    row,
                    capture=snapshots.get(row.investment_id, {}),
                    goal_legs=goal_index.get(row.investment_id, []),
                )
                for row in investments
            ]
            entities.append({"entity_id": entity_id, "investments": rows})
        return entities

    def _collect_price_entities(
        self,
        store: PriceFactorStore,
        enum_store: Optional[EnumerateStore],
    ) -> List[Dict[str, Any]]:
        entities: List[Dict[str, Any]] = []
        entity_ids = store.entity_ids or _price_entity_ids(store)
        for entity_id in entity_ids:
            rows_raw = store.investments(entity_id)
            if not rows_raw:
                continue
            snapshots: Dict[str, Dict[str, Any]] = {}
            if enum_store is not None and enum_store.has_investments(entity_id):
                snapshots = _snapshot_index(enum_store.snapshots(entity_id).rows)
            rows = [
                _join_price_investment(
                    row,
                    capture=snapshots.get(row.opportunity_id, {}),
                )
                for row in rows_raw
            ]
            entities.append({"entity_id": entity_id, "investments": rows})
        return entities

    def _open_upstream_enum_store(self) -> Optional[EnumerateStore]:
        raw = self._runtime_raw
        enum_dir = str(raw.get("enum_output_dir") or "").strip()
        enum_version_id = str(raw.get("enum_version_id") or "").strip()
        if enum_dir:
            path = Path(enum_dir)
            if path.is_dir():
                return EnumerateStore.open(
                    path,
                    version_id=enum_version_id or path.name,
                )
        return None

    def _as_enumerate_store(self) -> EnumerateStore:
        if not isinstance(self.store, EnumerateStore):
            raise TypeError("enumerate collector requires EnumerateStore")
        return self.store

    def _as_price_store(self) -> PriceFactorStore:
        if not isinstance(self.store, PriceFactorStore):
            raise TypeError("price collector requires PriceFactorStore")
        return self.store

    @staticmethod
    def _capture_stats(
        entities: Sequence[Dict[str, Any]],
    ) -> Tuple[List[str], int, int]:
        keys: Set[str] = set()
        total = 0
        with_snapshot = 0
        for entity in entities:
            for investment in entity.get("investments") or []:
                if not isinstance(investment, dict):
                    continue
                total += 1
                capture = investment.get("capture")
                if isinstance(capture, dict) and capture:
                    with_snapshot += 1
                    keys.update(str(k) for k in capture.keys())
        return sorted(keys), with_snapshot, total


def _price_entity_ids(store: PriceFactorStore) -> List[str]:
    nested = store._scan_suffix(store.entities_dir(), PRICE_INVESTMENTS_SUFFIX)
    if nested:
        return nested
    return store._scan_suffix(store.output_dir, PRICE_INVESTMENTS_SUFFIX)


def _declared_manifest(effective_settings: Dict[str, Any]) -> Dict[str, Any]:
    simulation = effective_settings.get("simulation")
    if not isinstance(simulation, dict):
        simulation = {}
    return {
        "core": dict(effective_settings.get("core") or {}),
        "data": dict(effective_settings.get("data") or {}),
        "goal": dict(effective_settings.get("goal") or {}),
        "simulation": {
            "execution": dict(simulation.get("execution") or {}),
            "assumption": dict(simulation.get("assumption") or {}),
            "risk_control": dict(simulation.get("risk_control") or {}),
        },
        "portfolio": dict(effective_settings.get("portfolio") or {}),
    }


def _snapshot_index(rows: Sequence[SignalSnapshotRow]) -> Dict[str, Dict[str, Any]]:
    return {
        str(row.investment_id or "").strip(): dict(row.values or {})
        for row in rows
        if str(row.investment_id or "").strip()
    }


def _goal_index(rows: Sequence[GoalAchievementRow]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        inv_id = str(row.investment_id or "").strip()
        if not inv_id:
            continue
        out.setdefault(inv_id, []).append(_serialize_goal_leg(row))
    return out


def _join_enum_investment(
    row: InvestmentRow,
    *,
    capture: Dict[str, Any],
    goal_legs: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "investment_id": row.investment_id,
        "engine": _serialize_enum_engine(row),
        "goal_legs": list(goal_legs),
        "capture": dict(capture),
    }


def _join_price_investment(
    row: PriceInvestmentRow,
    *,
    capture: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "investment_id": row.opportunity_id,
        "engine": _serialize_price_engine(row),
        "capture": dict(capture),
    }


def _serialize_enum_engine(row: InvestmentRow) -> Dict[str, Any]:
    return {
        "trigger_date": row.trigger_date,
        "trigger_price": row.trigger_price,
        "entry_date": row.entry_date,
        "entry_price": row.entry_price,
        "exit_date": row.exit_date,
        "exit_price": row.exit_price,
        "exit_reason": row.exit_reason,
        "lifecycle": row.lifecycle,
        "result": row.result,
        "weighted_roi": row.weighted_roi,
        "holding_days": row.holding_days,
        "stock_status_at_trigger": list(row.stock_status_at_trigger),
    }


def _serialize_price_engine(row: PriceInvestmentRow) -> Dict[str, Any]:
    return {
        "enter_date": row.enter_date,
        "enter_price": row.enter_price,
        "exit_date": row.exit_date,
        "exit_price": row.exit_price,
        "exit_reason": row.exit_reason,
        "skip_reason": row.skip_reason,
        "lifecycle": row.lifecycle,
        "result": row.result,
        "roi": row.roi,
        "holding_days": row.holding_days,
        "holding_trading_days": row.holding_trading_days,
    }


def _serialize_goal_leg(row: GoalAchievementRow) -> Dict[str, Any]:
    return {
        "goal_name": row.goal_name,
        "date": row.date,
        "price": row.price,
        "exit_ratio": row.exit_ratio,
        "profit": row.profit,
        "weighted_profit": row.weighted_profit,
        "reason": row.reason,
        "roi": row.roi,
    }


__all__ = ["AttributionInputCollector"]
