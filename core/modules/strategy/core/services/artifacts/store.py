"""统一仿真产物入口：定位 version、读写表、prune、进程内缓存。"""
from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Sequence, Tuple, Union

from core.infra.project_context import ProjectContext
from core.infra.utils import Utils
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts.io import ArtifactIO
from core.modules.strategy.core.services.artifacts.layout import (
    ENTITY_IDS_FILE,
    ENTITY_LIST_FILE,
    EQUITY_CURVE_FILE,
    GOAL_ACHIEVEMENTS_SUFFIX,
    OVERALL_REPORT_FILE,
    PERFORMANCE_FILE,
    PRICE_INVESTMENTS_SUFFIX,
    RUNTIME_ENV_FILE,
    SIGNAL_SNAPSHOTS_SUFFIX,
    STOCK_INVESTMENTS_SUFFIX,
    TRADES_FILE,
    entities_dir,
    entity_file,
    named_file,
)
from core.modules.strategy.core.services.artifacts.tables.enum_investments import (
    EntityInvestmentCsv,
    GoalAchievementCsv,
    GoalAchievementRow,
    InvestmentRow,
)
from core.modules.strategy.core.services.artifacts.tables.price_investments import (
    PriceInvestmentRow,
)
from core.modules.strategy.core.services.artifacts.tables.signal_snapshots import (
    EntitySignalSnapshotCsv,
    SignalSnapshotRow,
)

logger = logging.getLogger(__name__)

_KindLike = Union[SimulateKind, str]

_KIND_ALIASES = {
    "enumerate": SimulateKind.ENUMERATE,
    "enum": SimulateKind.ENUMERATE,
    "price_factor": SimulateKind.PRICE_FACTOR,
    "price": SimulateKind.PRICE_FACTOR,
    "portfolio": SimulateKind.PORTFOLIO,
    "capital": SimulateKind.PORTFOLIO,
}

_NAMED_FILES = {
    "runtime_env": RUNTIME_ENV_FILE,
    "entity_ids": ENTITY_IDS_FILE,
    "overall_report": OVERALL_REPORT_FILE,
    "entity_list": ENTITY_LIST_FILE,
    "performance": PERFORMANCE_FILE,
    "trades": TRADES_FILE,
    "equity_curve": EQUITY_CURVE_FILE,
}


def _read_next_output_version(meta: Dict[str, Any]) -> int:
    try:
        return max(int(meta.get("next_output_version") or 1), 1)
    except (TypeError, ValueError):
        return 1


def _resolve_max_versions(max_versions: Optional[int] = None) -> int:
    if max_versions is not None:
        try:
            value = int(max_versions)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"max_versions 必须是正整数，收到: {max_versions!r}"
            ) from exc
        if value < 1:
            raise ValueError(f"max_versions 必须 >= 1，收到: {value}")
        return value
    return ProjectContext.config.get_simulation_results_max_versions()


@dataclass
class _SettingsView:
    effective_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ArtifactRuntime:
    """打开 version 后的 runtime 投影（供 P/O 组 job，不替代 RuntimeEnv 写模型）。"""

    strategy_key: str = ""
    strategy_path: str = ""
    market_profile: str = ""
    settings_snapshot: _SettingsView = field(default_factory=_SettingsView)


class ArtifactStore:
    """一次仿真 version 的产物句柄。

    读一次缓存；reporter / analyzer 共用同一实例。
    """

    SNAPSHOT_KEY: ClassVar[str] = "output_recorder"
    _CACHE: ClassVar[Dict[Tuple[str, str], "ArtifactStore"]] = {}

    def __init__(
        self,
        output_dir: Path,
        *,
        kind: SimulateKind,
        version_id: str,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.kind = kind
        self.version_id = str(version_id)
        self.runtime = ArtifactRuntime()
        self.start_date = ""
        self.end_date = ""
        self.entity_ids: List[str] = []
        self._runtime_loaded = False
        self._enum_investments: Dict[str, EntityInvestmentCsv] = {}
        self._enum_goals: Dict[str, GoalAchievementCsv] = {}
        self._enum_snapshots: Dict[str, EntitySignalSnapshotCsv] = {}
        self._price_investments: Dict[str, List[PriceInvestmentRow]] = {}

    # ── 定位 ──────────────────────────────────────────

    @classmethod
    def parse_kind(cls, kind: _KindLike) -> SimulateKind:
        if isinstance(kind, SimulateKind):
            if kind is SimulateKind.FULL:
                raise ValueError("ArtifactStore 不支持 kind=full")
            return kind
        mapped = _KIND_ALIASES.get(str(kind or "").strip().lower())
        if mapped is None:
            raise ValueError(
                f"unsupported simulation kind: {kind!r} "
                f"(expected enum/price/portfolio)"
            )
        return mapped

    @classmethod
    def simulation_root(cls, strategy_folder: Union[str, Path], kind: _KindLike) -> Path:
        folder = Path(strategy_folder)
        parsed = cls.parse_kind(kind)
        if parsed is SimulateKind.ENUMERATE:
            return ProjectContext.path.get_strategy_simulation_enum_directory(folder)
        if parsed is SimulateKind.PRICE_FACTOR:
            return ProjectContext.path.get_strategy_simulation_price_directory(folder)
        return ProjectContext.path.get_strategy_simulation_portfolio_directory(folder)

    @classmethod
    def allocate(
        cls,
        strategy_folder: Union[str, Path],
        kind: _KindLike,
        *,
        strategy_id: str = "",
        max_versions: Optional[int] = None,
    ) -> "ArtifactStore":
        parsed = cls.parse_kind(kind)
        root = cls.simulation_root(strategy_folder, parsed)
        output_dir, version_id = cls._allocate_version_dir(
            str(strategy_id or strategy_folder),
            root,
            max_versions=max_versions,
        )
        return cls.at(output_dir, kind=parsed, version_id=str(version_id))

    @classmethod
    def resolve(
        cls,
        strategy_folder: Union[str, Path],
        kind: _KindLike,
        version_id: str,
    ) -> "ArtifactStore":
        vid = str(version_id or "").strip()
        if not vid:
            raise ValueError("version_id 不能为空")
        output_dir = cls.simulation_root(strategy_folder, kind) / vid
        if not output_dir.is_dir():
            raise FileNotFoundError(f"仿真 version 目录不存在: {output_dir}")
        return cls.open(output_dir, kind=kind, version_id=vid)

    @classmethod
    def latest(
        cls,
        strategy_folder: Union[str, Path],
        kind: _KindLike,
    ) -> Optional["ArtifactStore"]:
        parsed = cls.parse_kind(kind)
        root = cls.simulation_root(strategy_folder, parsed)
        meta_path = root / "meta.json"
        if not meta_path.is_file():
            return None
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            latest_id = int(meta.get("next_output_version") or 1) - 1
        except Exception:
            return None
        if latest_id <= 0:
            return None
        output_dir = root / str(latest_id)
        if not output_dir.is_dir():
            return None
        return cls.at(output_dir, kind=parsed, version_id=str(latest_id))

    @classmethod
    def open(
        cls,
        output_dir: Union[str, Path],
        *,
        kind: _KindLike,
        version_id: Optional[str] = None,
    ) -> "ArtifactStore":
        store = cls.at(output_dir, kind=kind, version_id=version_id)
        store._ensure_runtime()
        return store

    @classmethod
    def at(
        cls,
        output_dir: Union[str, Path],
        *,
        kind: _KindLike,
        version_id: Optional[str] = None,
    ) -> "ArtifactStore":
        parsed = cls.parse_kind(kind)
        directory = Path(output_dir)
        vid = str(version_id or directory.name or "").strip() or "0"
        key = (parsed.value, str(directory.resolve()) if directory.exists() else str(directory))
        cached = cls._CACHE.get(key)
        if cached is not None:
            if version_id is not None and str(version_id).strip():
                cached.version_id = str(version_id).strip()
            return cached
        store = cls(directory, kind=parsed, version_id=vid)
        cls._CACHE[key] = store
        return store

    @classmethod
    def hydrate(
        cls,
        output_dir: Union[str, Path],
        *,
        kind: _KindLike = SimulateKind.ENUMERATE,
        version_id: str = "1",
        entity_ids: Optional[Sequence[str]] = None,
        start_date: str = "",
        end_date: str = "",
        strategy_key: str = "",
        strategy_path: str = "",
        market_profile: str = "",
        effective_settings: Optional[Dict[str, Any]] = None,
    ) -> "ArtifactStore":
        """测试用：不读盘，填 identity。"""
        store = cls.at(output_dir, kind=kind, version_id=version_id)
        store.entity_ids = [str(x).strip() for x in (entity_ids or []) if str(x).strip()]
        store.start_date = str(start_date or "").strip()
        store.end_date = str(end_date or "").strip()
        key = str(strategy_key or "").strip()
        store.runtime = ArtifactRuntime(
            strategy_key=key,
            strategy_path=str(strategy_path or key).strip(),
            market_profile=str(market_profile or "").strip(),
            settings_snapshot=_SettingsView(
                effective_settings=dict(effective_settings or {}),
            ),
        )
        store._runtime_loaded = True
        return store

    @classmethod
    def clear_cache(cls) -> None:
        cls._CACHE.clear()

    # ── prune / allocate internals ──────────────────────────────────────────

    @classmethod
    def prune(
        cls,
        strategy_folder: Union[str, Path],
        *,
        kind: Optional[_KindLike] = None,
        max_versions: Optional[int] = None,
    ) -> Dict[str, Any]:
        folder = Path(strategy_folder)
        if kind is None or str(kind).strip() == "":
            kinds = (
                SimulateKind.ENUMERATE,
                SimulateKind.PRICE_FACTOR,
                SimulateKind.PORTFOLIO,
            )
        else:
            kinds = (cls.parse_kind(kind),)
        per_kind: Dict[str, int] = {}
        total = 0
        for parsed in kinds:
            root = cls.simulation_root(folder, parsed)
            deleted = cls.prune_root(root, max_versions=max_versions)
            label = {
                SimulateKind.ENUMERATE: "enum",
                SimulateKind.PRICE_FACTOR: "price",
                SimulateKind.PORTFOLIO: "portfolio",
            }[parsed]
            per_kind[label] = deleted
            total += deleted
        return {
            "ok": True,
            "strategy_folder": str(folder),
            "deleted_count": total,
            "per_kind": per_kind,
        }

    @classmethod
    def prune_root(
        cls,
        simulation_root: Path,
        *,
        max_versions: Optional[int] = None,
    ) -> int:
        root = Path(simulation_root)
        if not root.is_dir():
            return 0
        cap = _resolve_max_versions(max_versions)
        version_dirs = [
            d for d in root.iterdir() if d.is_dir() and d.name.isdigit()
        ]
        if len(version_dirs) <= cap:
            return 0
        version_dirs.sort(key=lambda d: int(d.name), reverse=True)
        deleted = 0
        for old_dir in version_dirs[cap:]:
            try:
                shutil.rmtree(old_dir)
                deleted += 1
                logger.info("Pruned simulation version dir: %s", old_dir)
            except Exception:
                logger.exception("Failed to prune simulation version dir: %s", old_dir)
        cls.clear_cache()
        return deleted

    @classmethod
    def _allocate_version_dir(
        cls,
        strategy_id: str,
        simulation_root: Path,
        *,
        max_versions: Optional[int] = None,
    ) -> Tuple[Path, int]:
        simulation_root.mkdir(parents=True, exist_ok=True)
        meta_path = simulation_root / "meta.json"
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
        else:
            meta = {}
        version_id = _read_next_output_version(meta)
        version_dir = simulation_root / str(version_id)
        version_dir.mkdir(parents=True, exist_ok=True)
        meta["next_output_version"] = version_id + 1
        meta["last_updated"] = datetime.now().isoformat()
        meta["strategy_name"] = strategy_id
        meta_path.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Allocated simulation version: %s (id=%d)", version_dir, version_id)
        cls.prune_root(simulation_root, max_versions=max_versions)
        return version_dir, version_id

    def to_snapshot(self) -> Dict[str, Any]:
        return {
            "output_dir": str(self.output_dir),
            "kind": self.kind.value,
            "version_id": self.version_id,
            "strategy_id": self.runtime.strategy_key,
            "version_dir_name": self.version_id,
        }

    @classmethod
    def from_snapshot(cls, snapshot: Dict[str, Any]) -> "ArtifactStore":
        kind = snapshot.get("kind") or SimulateKind.ENUMERATE
        return cls.at(
            Path(str(snapshot["output_dir"])),
            kind=kind,
            version_id=str(snapshot.get("version_id") or ""),
        )

    def ensure_entities_dir(self) -> Path:
        path = entities_dir(self.output_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def file(self, name: str) -> Path:
        filename = _NAMED_FILES.get(str(name or "").strip())
        if not filename:
            raise ValueError(f"unknown artifact file: {name!r}")
        return named_file(self.output_dir, filename)

    def has_runtime_env(self) -> bool:
        return self.file("runtime_env").is_file()

    # ── json / text ──────────────────────────────────────────

    def read_json(self, name: str) -> Dict[str, Any]:
        path = self.file(name) if name in _NAMED_FILES else named_file(self.output_dir, name)
        return ArtifactIO.read_json(path)

    def write_json(self, name: str, payload: Any) -> Path:
        path = self.file(name) if name in _NAMED_FILES else named_file(self.output_dir, name)
        return ArtifactIO.write_json(path, payload)

    def read_text_lines(self, name: str) -> List[str]:
        path = self.file(name) if name in _NAMED_FILES else named_file(self.output_dir, name)
        return ArtifactIO.read_text_lines(path)

    def write_text_lines(self, name: str, lines: Sequence[str]) -> Path:
        path = self.file(name) if name in _NAMED_FILES else named_file(self.output_dir, name)
        return ArtifactIO.write_text_lines(path, lines)

    # ── runtime identity ──────────────────────────────────────────

    def _ensure_runtime(self) -> None:
        if self._runtime_loaded:
            return
        runtime_path = named_file(self.output_dir, RUNTIME_ENV_FILE)
        if not runtime_path.is_file():
            raise FileNotFoundError(f"缺少 {RUNTIME_ENV_FILE}: {self.output_dir}")
        raw = ArtifactIO.read_json(runtime_path)
        ids_path = named_file(self.output_dir, ENTITY_IDS_FILE)
        entity_ids = ArtifactIO.read_text_lines(ids_path)
        if not entity_ids:
            raw_ids = raw.get("entity_ids")
            if isinstance(raw_ids, list):
                entity_ids = [str(x).strip() for x in raw_ids if str(x).strip()]
        period = raw.get("period") if isinstance(raw.get("period"), dict) else {}
        settings_raw = raw.get("settings") if isinstance(raw.get("settings"), dict) else {}
        if "effective_settings" not in settings_raw and isinstance(
            raw.get("settings_snapshot"), dict
        ):
            settings_raw = raw.get("settings_snapshot") or {}
        key = str(raw.get("strategy_key") or "").strip()
        self.runtime = ArtifactRuntime(
            strategy_key=key,
            strategy_path=str(raw.get("strategy_path") or key).strip(),
            market_profile=str(raw.get("market_profile") or "").strip(),
            settings_snapshot=_SettingsView(
                effective_settings=dict(settings_raw.get("effective_settings") or {}),
            ),
        )
        self.start_date = str(period.get("start_date") or "").strip()
        self.end_date = str(period.get("end_date") or "").strip()
        self.entity_ids = entity_ids
        self._runtime_loaded = True

    # ── enum tables ──────────────────────────────────────────

    def enum_investments(self, entity_id: str) -> EntityInvestmentCsv:
        eid = str(entity_id or "").strip()
        cached = self._enum_investments.get(eid)
        if cached is not None:
            return cached
        path = entity_file(self.output_dir, eid, STOCK_INVESTMENTS_SUFFIX)
        table = EntityInvestmentCsv(
            entity_id=eid,
            rows=[
                InvestmentRow.from_csv_row(row)
                for row in Utils.io.read_csv_to_dicts(path)
            ],
        )
        self._enum_investments[eid] = table
        return table

    def enum_goals(self, entity_id: str) -> GoalAchievementCsv:
        eid = str(entity_id or "").strip()
        cached = self._enum_goals.get(eid)
        if cached is not None:
            return cached
        path = entity_file(self.output_dir, eid, GOAL_ACHIEVEMENTS_SUFFIX)
        table = GoalAchievementCsv(
            entity_id=eid,
            rows=[
                GoalAchievementRow.from_csv_row(row)
                for row in Utils.io.read_csv_to_dicts(path)
            ],
        )
        self._enum_goals[eid] = table
        return table

    def enum_snapshots(self, entity_id: str) -> EntitySignalSnapshotCsv:
        eid = str(entity_id or "").strip()
        cached = self._enum_snapshots.get(eid)
        if cached is not None:
            return cached
        path = entity_file(self.output_dir, eid, SIGNAL_SNAPSHOTS_SUFFIX)
        table = EntitySignalSnapshotCsv(
            entity_id=eid,
            rows=[
                SignalSnapshotRow.from_csv_row(row)
                for row in Utils.io.read_csv_to_dicts(path)
                if str(row.get(EntitySignalSnapshotCsv.JOIN_KEY) or "").strip()
            ],
        )
        self._enum_snapshots[eid] = table
        return table

    def list_enum_investment_entities(self) -> List[str]:
        nested = self._scan_suffix(entities_dir(self.output_dir), STOCK_INVESTMENTS_SUFFIX)
        if nested:
            return nested
        return self._scan_suffix(self.output_dir, STOCK_INVESTMENTS_SUFFIX)

    def load_all_enum_investments(self) -> Dict[str, List[InvestmentRow]]:
        out: Dict[str, List[InvestmentRow]] = {}
        for entity_id in self.list_enum_investment_entities():
            out[entity_id] = list(self.enum_investments(entity_id).rows)
        return out

    def has_enum_investments(self, entity_id: str) -> bool:
        path = entity_file(self.output_dir, entity_id, STOCK_INVESTMENTS_SUFFIX)
        return path.is_file()

    def write_enum_investments(
        self, table: EntityInvestmentCsv, *, append: bool = False
    ) -> Path:
        path = entity_file(self.output_dir, table.entity_id, STOCK_INVESTMENTS_SUFFIX)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [row.to_csv_row() for row in table.rows]
        if append and path.is_file():
            rows = Utils.io.read_csv_to_dicts(path) + rows
        Utils.io.write_dicts_to_csv(
            path, rows, preferred_order=list(EntityInvestmentCsv.COLUMNS)
        )
        self._enum_investments.pop(str(table.entity_id or "").strip(), None)
        return path

    def write_enum_goals(self, table: GoalAchievementCsv, *, append: bool = False) -> Path:
        path = entity_file(self.output_dir, table.entity_id, GOAL_ACHIEVEMENTS_SUFFIX)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [row.to_csv_row() for row in table.rows]
        if append and path.is_file():
            rows = Utils.io.read_csv_to_dicts(path) + rows
        Utils.io.write_dicts_to_csv(
            path, rows, preferred_order=list(GoalAchievementCsv.COLUMNS)
        )
        self._enum_goals.pop(str(table.entity_id or "").strip(), None)
        return path

    def write_enum_snapshots(
        self, table: EntitySignalSnapshotCsv, *, append: bool = False
    ) -> Path:
        path = entity_file(self.output_dir, table.entity_id, SIGNAL_SNAPSHOTS_SUFFIX)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [row.to_csv_row() for row in table.rows]
        if append and path.is_file():
            rows = Utils.io.read_csv_to_dicts(path) + rows
        if not rows:
            return path
        keys: set[str] = set()
        for row in rows:
            keys.update(str(k) for k in row.keys())
        keys.discard(EntitySignalSnapshotCsv.JOIN_KEY)
        preferred = [EntitySignalSnapshotCsv.JOIN_KEY] + sorted(keys)
        Utils.io.write_dicts_to_csv(path, rows, preferred_order=preferred)
        self._enum_snapshots.pop(str(table.entity_id or "").strip(), None)
        return path

    def append_enum_entity(
        self, entity_id: str, investments: Sequence[Dict[str, Any]]
    ) -> Dict[str, int]:
        stock = EntityInvestmentCsv.build(entity_id, investments)
        goals = GoalAchievementCsv.build(entity_id, investments)
        snapshots = EntitySignalSnapshotCsv.build(entity_id, investments)
        investment_files = 0
        goal_files = 0
        investment_rows = 0
        goal_rows = 0
        if stock.rows:
            self.write_enum_investments(stock, append=True)
            investment_files = 1
            investment_rows = len(stock.rows)
        if goals.rows:
            self.write_enum_goals(goals, append=True)
            goal_files = 1
            goal_rows = len(goals.rows)
        if snapshots.rows:
            self.write_enum_snapshots(snapshots, append=True)
        return {
            "investment_files": investment_files,
            "goal_files": goal_files,
            "investment_rows": investment_rows,
            "goal_rows": goal_rows,
        }

    # ── price tables ──────────────────────────────────────────

    def price_investments(self, entity_id: str) -> List[PriceInvestmentRow]:
        eid = str(entity_id or "").strip()
        cached = self._price_investments.get(eid)
        if cached is not None:
            return cached
        path = entity_file(self.output_dir, eid, PRICE_INVESTMENTS_SUFFIX)
        if not path.is_file():
            self._price_investments[eid] = []
            return []
        out: List[PriceInvestmentRow] = []
        for raw in Utils.io.read_csv_to_dicts(path):
            row = PriceInvestmentRow.from_dict(raw)
            if not row.opportunity_id and not row.enter_date:
                continue
            out.append(row)
        self._price_investments[eid] = out
        return out

    def load_all_price_investments(
        self, entity_ids: Sequence[str]
    ) -> Dict[str, List[PriceInvestmentRow]]:
        return {
            str(eid): self.price_investments(eid)
            for eid in entity_ids
            if str(eid or "").strip()
        }

    def has_price_investments(self, entity_id: str) -> bool:
        path = entity_file(self.output_dir, entity_id, PRICE_INVESTMENTS_SUFFIX)
        if not path.is_file():
            return False
        try:
            content = path.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]
            return len(lines) >= 2
        except OSError:
            return False

    def write_price_investments(
        self,
        entity_id: str,
        rows: Sequence[Union[PriceInvestmentRow, Dict[str, Any]]],
    ) -> Path:
        path = entity_file(self.output_dir, entity_id, PRICE_INVESTMENTS_SUFFIX)
        path.parent.mkdir(parents=True, exist_ok=True)
        payloads: List[Dict[str, Any]] = []
        for row in rows:
            if isinstance(row, PriceInvestmentRow):
                payloads.append(row.to_dict())
            else:
                payloads.append(dict(row or {}))
        if not payloads:
            payloads = [{name: "" for name in PriceInvestmentRow.COLUMN_ORDER}]
        Utils.io.write_dicts_to_csv(
            path, payloads, preferred_order=list(PriceInvestmentRow.COLUMN_ORDER)
        )
        self._price_investments.pop(str(entity_id or "").strip(), None)
        return path

    @staticmethod
    def _scan_suffix(directory: Path, suffix: str) -> List[str]:
        if not directory.is_dir():
            return []
        return sorted(
            entry.name[: -len(suffix)]
            for entry in directory.iterdir()
            if entry.is_file() and entry.name.endswith(suffix)
        )


__all__ = ["ArtifactRuntime", "ArtifactStore"]
