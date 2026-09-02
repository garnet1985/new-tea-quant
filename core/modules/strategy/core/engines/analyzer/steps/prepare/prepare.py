"""分析 input 准备：读回测产物 → 转换 → 落盘 ``analysis/source.json``。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore

from ...consts import SCHEMA_VERSION


@dataclass(frozen=True)
class PrepareOutput:
    """Prepare 步产出 — 磁盘上的 ``analysis/source.json``。"""

    source_path: Path
    analysis_dir: Path
    entity_count: int
    investment_count: int
    step: str
    version_id: str

    @classmethod
    def from_payload(
        cls,
        *,
        source_path: Path,
        payload: Dict[str, Any],
    ) -> "PrepareOutput":
        entity_count = len(payload.get("entities") or [])
        investment_count = int(
            (payload.get("inputs") or {})
            .get("capture", {})
            .get("coverage", {})
            .get("investment_count", 0)
        )
        return cls(
            source_path=Path(source_path),
            analysis_dir=Path(source_path).parent,
            entity_count=entity_count,
            investment_count=investment_count,
            step=str(payload.get("step") or ""),
            version_id=str(payload.get("version_id") or ""),
        )


class PrepareStep:
    """收集、转换并持久化 analyze 步使用的 ``analysis/source.json``。"""

    def __init__(self, store: ArtifactStore) -> None:
        self.store = store
        self._runtime_raw = store.read_json("runtime_env")

    @classmethod
    def run(cls, store: ArtifactStore) -> PrepareOutput:
        payload = cls(store).build()
        body = dict(payload)
        body["collected_at"] = datetime.now().isoformat()
        source_path = store.write_json("analysis_source", body)
        return PrepareOutput.from_payload(source_path=source_path, payload=payload)

    def build(self) -> Dict[str, Any]:
        kind = self.store.kind
        if kind is SimulateKind.ENUMERATE:
            return self._collect_enumerate()
        if kind is SimulateKind.PRICE_FACTOR:
            return self._collect_price()
        if kind is SimulateKind.PORTFOLIO:
            return self._collect_portfolio()
        raise ValueError(f"unsupported prepare step: {kind!r}")

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
        trade_rows = _load_trade_rows(self.store)
        entities = self._collect_portfolio_entities(trade_rows, enum_store)
        capture_keys, with_snapshot, total = self._capture_stats(entities)
        open_buys = _count_open_buys(trade_rows)
        payload["inputs"]["portfolio_artifacts"] = {
            "trades_present": trades_path.is_file(),
            "equity_curve_present": equity_path.is_file(),
            "trade_count": len(trade_rows),
            "completed_lots": total,
            "open_buys": open_buys,
        }
        payload["inputs"]["capture"] = {
            "keys": capture_keys,
            "coverage": {
                "investment_count": total,
                "with_snapshot": with_snapshot,
            },
            "join": {
                "source_step": WorkbenchStep.ENUM.value,
                "join_key": "investment_id",
                "entity_key": "entity_id",
                "lot_key": "entity_id+investment_id",
            },
        }
        payload["entities"] = entities
        return payload

    def _collect_portfolio_entities(
        self,
        trade_rows: Sequence[Dict[str, Any]],
        enum_store: Optional[EnumerateStore],
    ) -> List[Dict[str, Any]]:
        buys, sells = _split_trades(trade_rows)
        by_entity: Dict[str, List[Dict[str, Any]]] = {}
        snapshot_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for sell in sells:
            entity_id = str(sell.get("entity_id") or "").strip()
            inv_id = str(sell.get("investment_id") or "").strip()
            if not entity_id or not inv_id:
                continue
            buy = buys.get(_lot_key(entity_id, inv_id))
            if buy is None:
                continue
            if entity_id not in snapshot_cache:
                snapshot_cache[entity_id] = {}
                if enum_store is not None and enum_store.has_investments(entity_id):
                    snapshot_cache[entity_id] = _snapshot_index(
                        enum_store.snapshots(entity_id).rows
                    )
            capture = snapshot_cache[entity_id].get(inv_id, {})
            by_entity.setdefault(entity_id, []).append(
                _join_portfolio_investment(buy=buy, sell=sell, capture=capture)
            )
        return [
            {"entity_id": entity_id, "investments": rows}
            for entity_id, rows in sorted(by_entity.items())
            if rows
        ]

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
        archive = VersionMetaStore.read_archive_context(
            self.store.output_dir.parent.parent, self.store.version_id
        )
        effective = settings_raw.get("effective_settings")
        if not isinstance(effective, dict) or not effective:
            effective = (
                archive.get("effective_settings")
                or self.store.runtime.settings_snapshot.effective_settings
            )

        workbench_step = WorkbenchStep.from_simulate_kind(self.store.kind)
        if workbench_step is None:
            raise ValueError(f"unsupported prepare step: {self.store.kind!r}")

        payload: Dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "strategy_key": str(raw.get("strategy_key") or self.store.runtime.strategy_key or "").strip(),
            "strategy_path": str(raw.get("strategy_path") or self.store.runtime.strategy_path or "").strip(),
            "step": workbench_step.value,
            "version_id": str(self.store.version_id),
            "output_dir": str(self.store.output_dir.resolve()),
            "fingerprints": {
                "execute": str(
                    archive.get("execute_fp")
                    or fps.get("execute")
                    or raw.get("execute_fp")
                    or ""
                ).strip(),
                "env": str(
                    archive.get("env_fp")
                    or fps.get("env")
                    or raw.get("env_fp")
                    or ""
                ).strip(),
            },
            "period": {
                "start_date": str(
                    period.get("start_date")
                    or archive.get("start_date")
                    or self.store.start_date
                    or ""
                ).strip(),
                "end_date": str(
                    period.get("end_date")
                    or archive.get("end_date")
                    or self.store.end_date
                    or ""
                ).strip(),
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
            raise TypeError("enumerate prepare requires EnumerateStore")
        return self.store

    def _as_price_store(self) -> PriceFactorStore:
        if not isinstance(self.store, PriceFactorStore):
            raise TypeError("price prepare requires PriceFactorStore")
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


def _join_portfolio_investment(
    *,
    buy: Dict[str, Any],
    sell: Dict[str, Any],
    capture: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "investment_id": str(sell.get("investment_id") or "").strip(),
        "engine": _serialize_portfolio_engine(buy=buy, sell=sell),
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


def _serialize_portfolio_engine(
    *,
    buy: Dict[str, Any],
    sell: Dict[str, Any],
) -> Dict[str, Any]:
    buy_amount = _as_float(buy.get("amount"))
    profit = _as_float(sell.get("profit"))
    roi = None
    if profit is not None and buy_amount is not None and buy_amount > 0:
        roi = profit / buy_amount
    result = ""
    if roi is not None:
        result = "win" if roi > 0 else "loss"
    return {
        "buy_date": str(buy.get("date") or "").strip(),
        "sell_date": str(sell.get("date") or "").strip(),
        "buy_price": _as_float(buy.get("price")),
        "sell_price": _as_float(sell.get("price")),
        "shares": int(float(sell.get("shares") or 0) or 0),
        "buy_amount": buy_amount,
        "sell_amount": _as_float(sell.get("amount")),
        "buy_fees": _as_float(buy.get("fees")),
        "sell_fees": _as_float(sell.get("fees")),
        "profit": profit,
        "roi": roi,
        "result": result,
        "lifecycle": "complete",
    }


def _load_trade_rows(store: ArtifactStore) -> List[Dict[str, Any]]:
    path = store.file("trades")
    if not path.is_file():
        return []
    raw = store.read_json("trades")
    if isinstance(raw, list):
        return [row for row in raw if isinstance(row, dict)]
    if isinstance(raw, dict):
        trades = raw.get("trades")
        if isinstance(trades, list):
            return [row for row in trades if isinstance(row, dict)]
    return []


def _split_trades(
    trade_rows: Sequence[Dict[str, Any]],
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    buys: Dict[str, Dict[str, Any]] = {}
    sells: List[Dict[str, Any]] = []
    for row in trade_rows:
        entity_id = str(row.get("entity_id") or "").strip()
        inv_id = str(row.get("investment_id") or "").strip()
        side = str(row.get("side") or "").strip().lower()
        if not entity_id or not inv_id:
            continue
        if side == "buy":
            buys[_lot_key(entity_id, inv_id)] = row
        elif side == "sell":
            sells.append(row)
    return buys, sells


def _count_open_buys(trade_rows: Sequence[Dict[str, Any]]) -> int:
    buys, sells = _split_trades(trade_rows)
    sold = {
        _lot_key(str(row.get("entity_id") or "").strip(), str(row.get("investment_id") or "").strip())
        for row in sells
    }
    return sum(1 for key in buys if key not in sold)


def _lot_key(entity_id: str, investment_id: str) -> str:
    return f"{entity_id}\t{investment_id}"


def _as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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


__all__ = ["PrepareOutput", "PrepareStep"]
