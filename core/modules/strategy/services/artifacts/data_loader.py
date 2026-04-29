#!/usr/bin/env python3
"""
Data Loader - 统一数据加载器
"""

from collections import defaultdict
import csv
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .event import SimulationEvent

logger = logging.getLogger(__name__)


class DataLoader:
    """统一数据加载器（实例方法，支持缓存）"""

    def __init__(self, strategy_name: str, cache_enabled: bool = True):
        self.strategy_name = strategy_name
        self.cache_enabled = cache_enabled
        self._cache: Dict[str, Any] = {}

    def clear_cache(self) -> None:
        self._cache.clear()
        logger.debug("[DataLoader] 已清空缓存: strategy=%s", self.strategy_name)

    def load_opportunities(
        self,
        output_version_dir: Path,
        stock_id: Optional[str] = None,
        start_date: str = "",
        end_date: str = "",
    ) -> List[Dict[str, Any]]:
        if stock_id:
            opportunities_path = output_version_dir / f"{stock_id}_opportunities.csv"
            if not opportunities_path.exists():
                logger.warning("[DataLoader] opportunities 文件不存在: %s", opportunities_path)
                return []
            return self._load_opportunities_from_file(opportunities_path, start_date, end_date)

        opportunities: List[Dict[str, Any]] = []
        for entry in output_version_dir.iterdir():
            if entry.is_file() and entry.name.endswith("_opportunities.csv"):
                opportunities.extend(
                    self._load_opportunities_from_file(entry, start_date, end_date)
                )
        return opportunities

    def load_targets(
        self,
        output_version_dir: Path,
        stock_id: Optional[str] = None,
        opportunity_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if stock_id:
            targets_path = output_version_dir / f"{stock_id}_targets.csv"
            if not targets_path.exists():
                return []
            return self._load_targets_from_file(targets_path, opportunity_id)

        targets: List[Dict[str, Any]] = []
        for entry in output_version_dir.iterdir():
            if entry.is_file() and entry.name.endswith("_targets.csv"):
                targets.extend(self._load_targets_from_file(entry, opportunity_id))
        return targets

    def load_opportunities_and_targets(
        self,
        output_version_dir: Path,
        stock_id: Optional[str] = None,
        start_date: str = "",
        end_date: str = "",
    ) -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
        cache_key = f"{output_version_dir.name}_{stock_id or 'all'}_{start_date}_{end_date}"
        if self.cache_enabled and cache_key in self._cache:
            logger.debug("[DataLoader] 使用缓存: strategy=%s, key=%s", self.strategy_name, cache_key)
            return self._cache[cache_key]

        if stock_id:
            opportunities_path = output_version_dir / f"{stock_id}_opportunities.csv"
            targets_path = output_version_dir / f"{stock_id}_targets.csv"
            opportunities, targets_map = self._load_from_files(
                opportunities_path, targets_path, start_date, end_date
            )
        else:
            opportunities = []
            targets_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            for entry in output_version_dir.iterdir():
                if not entry.is_file() or not entry.name.endswith("_opportunities.csv"):
                    continue
                stock_id_from_file = entry.name[: -len("_opportunities.csv")]
                targets_path = output_version_dir / f"{stock_id_from_file}_targets.csv"
                stock_opps, stock_targets_map = self._load_from_files(
                    entry, targets_path, start_date, end_date
                )
                opportunities.extend(stock_opps)
                targets_map.update(stock_targets_map)

        result = (opportunities, targets_map)
        if self.cache_enabled:
            self._cache[cache_key] = result
            logger.debug(
                "[DataLoader] 已缓存: strategy=%s, key=%s, opportunities=%s",
                self.strategy_name,
                cache_key,
                len(opportunities),
            )
        return result

    def build_event_stream(
        self,
        output_version_dir: Path,
        start_date: str = "",
        end_date: str = "",
    ) -> List[SimulationEvent]:
        events: List[SimulationEvent] = []
        for entry in output_version_dir.iterdir():
            if not entry.is_file() or not entry.name.endswith("_opportunities.csv"):
                continue

            stock_id = entry.name[: -len("_opportunities.csv")]
            opportunities_path = entry
            targets_path = output_version_dir / f"{stock_id}_targets.csv"

            opp_rows, target_rows, targets_index = self.load_rows_for_stock(
                opportunities_path=opportunities_path,
                targets_path=targets_path,
                start_date=start_date,
                end_date=end_date,
            )
            if not opp_rows:
                continue

            for opportunity in opp_rows:
                opp_id = str(opportunity.get("opportunity_id") or "").strip()
                trigger_date = opportunity.get("trigger_date") or ""
                if not opp_id or not trigger_date:
                    continue

                events.append(
                    SimulationEvent(
                        event_type="trigger",
                        date=trigger_date,
                        stock_id=stock_id,
                        opportunity_id=opp_id,
                        opportunity=opportunity,
                        target=None,
                    )
                )

                for t_idx in targets_index.get(opp_id, []):
                    if t_idx < 0 or t_idx >= len(target_rows):
                        continue
                    target_row = target_rows[t_idx]
                    target_date = (
                        target_row.get("date")
                        or target_row.get("target_date")
                        or ""
                    )
                    if not target_date:
                        continue
                    events.append(
                        SimulationEvent(
                            event_type="target",
                            date=target_date,
                            stock_id=stock_id,
                            opportunity_id=opp_id,
                            opportunity=opportunity,
                            target=target_row,
                        )
                    )

        events.sort(key=lambda e: (e.date, e.stock_id, e.opportunity_id, e.event_type))
        return events

    def load_rows_for_stock(
        self,
        opportunities_path: Path,
        targets_path: Path,
        start_date: str = "",
        end_date: str = "",
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, List[int]]]:
        target_rows: List[Dict[str, Any]] = []
        targets_index: Dict[str, List[int]] = defaultdict(list)

        if targets_path.exists():
            with targets_path.open("r", encoding="utf-8") as f_t:
                reader = csv.DictReader(f_t)
                for opp_id, row in self._iter_normalized_target_rows(
                    reader, start_date=start_date, end_date=end_date
                ):
                    target_rows.append(row)
                    targets_index[opp_id].append(len(target_rows) - 1)

        opp_rows: List[Dict[str, Any]] = []
        if opportunities_path.exists():
            with opportunities_path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    trigger_date = row.get("trigger_date") or ""
                    if start_date and trigger_date < start_date:
                        continue
                    if end_date and trigger_date > end_date:
                        continue
                    opp_rows.append(row)
        else:
            logger.warning("[DataLoader] opportunities 文件不存在: %s", opportunities_path)

        return opp_rows, target_rows, targets_index

    def _load_from_files(
        self,
        opportunities_path: Path,
        targets_path: Path,
        start_date: str = "",
        end_date: str = "",
    ) -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
        targets_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        if targets_path.exists():
            with targets_path.open("r", encoding="utf-8") as f_t:
                t_reader = csv.DictReader(f_t)
                for opp_id, row in self._iter_normalized_target_rows(
                    t_reader, start_date=start_date, end_date=end_date
                ):
                    targets_map[opp_id].append(row)

        opportunities: List[Dict[str, Any]] = []
        if not opportunities_path.exists():
            logger.warning("[DataLoader] opportunities 文件不存在: %s", opportunities_path)
            return opportunities, targets_map
        with opportunities_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trigger_date = row.get("trigger_date") or ""
                if start_date and trigger_date < start_date:
                    continue
                if end_date and trigger_date > end_date:
                    continue
                opportunities.append(row)
        return opportunities, targets_map

    def _load_opportunities_from_file(
        self,
        opportunities_path: Path,
        start_date: str = "",
        end_date: str = "",
    ) -> List[Dict[str, Any]]:
        opportunities: List[Dict[str, Any]] = []
        if not opportunities_path.exists():
            return opportunities
        with opportunities_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trigger_date = row.get("trigger_date") or ""
                if start_date and trigger_date < start_date:
                    continue
                if end_date and trigger_date > end_date:
                    continue
                opportunities.append(row)
        return opportunities

    def _load_targets_from_file(
        self,
        targets_path: Path,
        opportunity_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        targets: List[Dict[str, Any]] = []
        if not targets_path.exists():
            return targets
        with targets_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for opp_id, row in self._iter_normalized_target_rows(
                reader, start_date="", end_date=""
            ):
                if opportunity_id and opp_id != opportunity_id:
                    continue
                targets.append(row)
        return targets

    @staticmethod
    def _coerce_float(value: Any) -> float:
        try:
            return float(value or 0.0)
        except (ValueError, TypeError):
            return 0.0

    def _normalize_target_row(
        self,
        row: Dict[str, Any],
        *,
        start_date: str,
        end_date: str,
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        opp_id = str(row.get("opportunity_id") or "").strip()
        if not opp_id:
            return None, None
        target_date = (
            row.get("date")
            or row.get("sell_date")
            or row.get("target_date")
            or ""
        )
        if start_date and target_date and target_date < start_date:
            return None, None
        if end_date and target_date and target_date > end_date:
            return None, None

        normalized = dict(row)
        raw_sell_price = (
            normalized.get("sell_price")
            or normalized.get("price")
            or normalized.get("target_price")
            or 0.0
        )
        normalized["sell_price"] = self._coerce_float(raw_sell_price)
        normalized["sell_ratio"] = self._coerce_float(normalized.get("sell_ratio"))
        normalized["profit"] = self._coerce_float(normalized.get("profit"))
        normalized["weighted_profit"] = self._coerce_float(normalized.get("weighted_profit"))
        return opp_id, normalized

    def _iter_normalized_target_rows(
        self,
        rows: csv.DictReader,
        *,
        start_date: str,
        end_date: str,
    ):
        for row in rows:
            opp_id, normalized = self._normalize_target_row(
                row, start_date=start_date, end_date=end_date
            )
            if opp_id and normalized is not None:
                yield opp_id, normalized
