"""枚举 run 启动快照：合并 env + settings，落盘 entity_ids.txt / runtime_env.json。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, TYPE_CHECKING

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.enumerator.shared.report_manager.report_consts import (
    ENTITY_IDS_FILE,
    RUNTIME_ENV_FILE,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.system import get_version


@dataclass
class BacktestPeriod:
    start_date: str
    end_date: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "BacktestPeriod":
        data = raw or {}
        return cls(
            start_date=str(data.get("start_date") or ""),
            end_date=str(data.get("end_date") or ""),
        )


@dataclass
class SystemEnv:
    data: Dict[str, Any] = field(default_factory=dict)
    database_type: str = ""
    engine_version: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data": dict(self.data or {}),
            "database_type": self.database_type,
            "engine_version": self.engine_version,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "SystemEnv":
        data = raw or {}
        return cls(
            data=dict(data.get("data") or {}),
            database_type=str(data.get("database_type") or ""),
            engine_version=str(data.get("engine_version") or ""),
        )


@dataclass
class SettingsSnapshot:
    effective_settings: Dict[str, Any] = field(default_factory=dict)
    settings_diff: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "effective_settings": dict(self.effective_settings or {}),
            "settings_diff": dict(self.settings_diff or {}),
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "SettingsSnapshot":
        data = raw or {}
        return cls(
            effective_settings=dict(data.get("effective_settings") or {}),
            settings_diff=dict(data.get("settings_diff") or {}),
        )


@dataclass
class SavedRuntimeArtifacts:
    entity_ids_path: Path
    runtime_env_path: Path


@dataclass
class RuntimeSnapshot:
    """一次枚举 run 的全部运行时配置（env + settings 合并）。"""

    ENTITY_IDS_FILE = ENTITY_IDS_FILE
    RUNTIME_ENV_FILE = RUNTIME_ENV_FILE

    strategy_key: str
    version_id: int
    execution_mode: str
    market_profile: str
    entity_ids: List[str]
    settings_fp: str
    env_fp: str
    period: BacktestPeriod
    system: SystemEnv
    settings_snapshot: SettingsSnapshot
    created_at: str = ""

    @property
    def entity_count(self) -> int:
        return len(self.entity_ids)

    # ── 工厂 ──

    @classmethod
    def build(
        cls,
        *,
        strategy_key: str,
        version_id: int,
        entity_ids: List[str],
        settings_fp: str,
        env_fp: str,
        effective_settings: StrategySettings,
        settings_diff: Dict[str, Any],
        execution_mode: str,
        market_profile: str,
    ) -> "RuntimeSnapshot":
        return cls(
            strategy_key=strategy_key,
            version_id=int(version_id),
            execution_mode=str(execution_mode or "").strip(),
            market_profile=str(market_profile or "").strip(),
            entity_ids=cls._normalize_entity_ids(entity_ids),
            settings_fp=str(settings_fp or ""),
            env_fp=str(env_fp or ""),
            period=cls.resolve_period(effective_settings),
            system=cls._build_system_env(),
            settings_snapshot=SettingsSnapshot(
                effective_settings=effective_settings.to_dict(),
                settings_diff=dict(settings_diff or {}),
            ),
            created_at=datetime.now().isoformat(),
        )

    @classmethod
    def resolve_period(cls, effective_settings: StrategySettings) -> BacktestPeriod:
        from core.modules.strategy.core.engines.shared.services.entity_loader.global_entity_loader import (
            GlobalEntityCache,
        )

        sampling = effective_settings.raw_settings.get("sampling", {}) or {}
        start_date = str(sampling.get("start_date") or "").strip()
        end_date = str(sampling.get("end_date") or "").strip()

        if not end_date:
            end_date = GlobalEntityCache.load_latest_completed_trading_date()
        if not start_date:
            start_date = ProjectContext.config.get_default_start_date()

        return BacktestPeriod(start_date=start_date, end_date=end_date)

    @classmethod
    def _resolve_artifact_path(cls, output_dir: Path, filename: str, *, legacy: str) -> Path:
        path = output_dir / filename
        if path.is_file():
            return path
        legacy_path = output_dir / legacy
        if legacy_path.is_file():
            return legacy_path
        return path

    @classmethod
    def load(cls, output_dir: Path) -> "RuntimeSnapshot":
        runtime_env_path = cls._resolve_artifact_path(
            output_dir,
            cls.RUNTIME_ENV_FILE,
            legacy="runtime_env.json",
        )
        entity_ids_path = cls._resolve_artifact_path(
            output_dir,
            cls.ENTITY_IDS_FILE,
            legacy="entity_ids.txt",
        )
        payload = cls._read_json(runtime_env_path)
        entity_ids = cls._read_entity_ids(entity_ids_path)
        return cls.from_dict(payload, entity_ids=entity_ids)

    # ── 落盘 ──

    def save(self, output_dir: Path) -> SavedRuntimeArtifacts:
        output_dir.mkdir(parents=True, exist_ok=True)
        entity_ids_path = self._write_entity_ids(output_dir / self.ENTITY_IDS_FILE)
        runtime_env_path = self._write_json(output_dir / self.RUNTIME_ENV_FILE, self.to_dict())
        return SavedRuntimeArtifacts(
            entity_ids_path=entity_ids_path,
            runtime_env_path=runtime_env_path,
        )

    # ── 序列化 ──

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_key": self.strategy_key,
            "version_id": self.version_id,
            "execution_mode": self.execution_mode,
            "market_profile": self.market_profile,
            "entity_count": self.entity_count,
            "entity_ids_file": self.ENTITY_IDS_FILE,
            "fingerprints": {
                "settings": self.settings_fp,
                "env": self.env_fp,
            },
            "period": self.period.to_dict(),
            "system": self.system.to_dict(),
            "settings": self.settings_snapshot.to_dict(),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(
        cls,
        raw: Dict[str, Any],
        *,
        entity_ids: List[str] | None = None,
    ) -> "RuntimeSnapshot":
        data = raw or {}
        fingerprints = data.get("fingerprints") or {}
        settings_raw = data.get("settings") or {}
        if "effective_settings" not in settings_raw and "settings_snapshot" in data:
            settings_raw = data.get("settings_snapshot") or {}

        return cls(
            strategy_key=str(data.get("strategy_key") or ""),
            version_id=int(data.get("version_id") or 0),
            execution_mode=str(data.get("execution_mode") or ""),
            market_profile=str(data.get("market_profile") or ""),
            entity_ids=cls._normalize_entity_ids(
                entity_ids if entity_ids is not None else data.get("entity_ids") or []
            ),
            settings_fp=str(fingerprints.get("settings") or data.get("settings_fp") or ""),
            env_fp=str(fingerprints.get("env") or data.get("env_fp") or ""),
            period=BacktestPeriod.from_dict(data.get("period") or {}),
            system=SystemEnv.from_dict(data.get("system") or {}),
            settings_snapshot=SettingsSnapshot.from_dict(settings_raw),
            created_at=str(data.get("created_at") or ""),
        )

    # ── private ──

    @classmethod
    def _build_system_env(cls) -> SystemEnv:
        data_config = dict(ProjectContext.config.load_data_config() or {})
        try:
            db_config = ProjectContext.config.load_database_config()
            database_type = str(db_config.get("database_type") or "")
        except Exception:
            database_type = ""
        return SystemEnv(
            data=data_config,
            database_type=database_type,
            engine_version=str(get_version() or ""),
        )

    @staticmethod
    def _normalize_entity_ids(entity_ids: List[str]) -> List[str]:
        return sorted({str(item).strip() for item in entity_ids if str(item).strip()})

    @staticmethod
    def _write_entity_ids_file(path: Path, entity_ids: List[str]) -> Path:
        ids = RuntimeSnapshot._normalize_entity_ids(entity_ids)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(ids) + ("\n" if ids else ""),
            encoding="utf-8",
        )
        return path

    def _write_entity_ids(self, path: Path) -> Path:
        return self._write_entity_ids_file(path, self.entity_ids)

    @staticmethod
    def _read_entity_ids(path: Path) -> List[str]:
        if not path.is_file():
            return []
        return [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    @staticmethod
    def _write_json(path: Path, payload: Dict[str, Any]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))


class RuntimeReport:
    """ReportManager.runtime 门面：启动快照读写。"""

    def __init__(self, manager: "ReportManager") -> None:
        self._manager = manager

    @staticmethod
    def resolve_period(effective_settings: Any) -> BacktestPeriod:
        return RuntimeSnapshot.resolve_period(effective_settings)

    def save_begin(
        self,
        *,
        entity_ids: List[str],
        settings_fp: str,
        env_fp: str,
        effective_settings: StrategySettings,
        settings_diff: Dict[str, Any],
        execution_mode: str,
        market_profile: str,
    ) -> SavedRuntimeArtifacts:
        snapshot = RuntimeSnapshot.build(
            strategy_key=self._manager.strategy_key,
            version_id=self._manager.version_id,
            entity_ids=entity_ids,
            settings_fp=settings_fp,
            env_fp=env_fp,
            effective_settings=effective_settings,
            settings_diff=settings_diff,
            execution_mode=execution_mode,
            market_profile=market_profile,
        )
        return snapshot.save(self._manager.output_dir)

    def load(self) -> Dict[str, Any]:
        return RuntimeSnapshot.load(self._manager.output_dir).to_dict()

    @property
    def entity_count(self) -> int:
        return RuntimeSnapshot.load(self._manager.output_dir).entity_count


if TYPE_CHECKING:
    from core.modules.strategy.core.engines.enumerator.shared.report_manager.report_manager import (
        ReportManager,
    )


__all__ = [
    "RuntimeReport",
]
