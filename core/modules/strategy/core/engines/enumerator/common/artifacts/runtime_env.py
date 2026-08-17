"""枚举 version 运行环境（runtime_env.json + entity_ids）（enumerator 私有）。

本文件: SystemEnv / SettingsSnapshot / RuntimeEnv
边界: 负责 enum runtime 内容组装与读写；布局/IO 委托 services.artifacts
period 解析见 StrategySettings.resolve_period / BacktestPeriod
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.shared.services.strategy_settings import BacktestPeriod
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import (
    ENTITY_IDS_FILE,
    RUNTIME_ENV_FILE,
    ArtifactStore,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.system import get_version


@dataclass
class SystemEnv:
    """运行环境快照片段（data/db/engine_version）。"""

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
    """策略 settings 快照（effective + diff）。"""

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
class SavedRuntimeEnvPaths:
    """runtime_env / entity_ids 落盘路径。"""

    entity_ids_path: Path
    runtime_env_path: Path


@dataclass
class RuntimeEnv:
    """一次枚举 run 的运行环境描述（对应 runtime_env.json）。"""

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
    strategy_path: str = ""

    @property
    def entity_count(self) -> int:
        return len(self.entity_ids)

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
        strategy_path: str = "",
    ) -> "RuntimeEnv":
        return cls(
            strategy_key=strategy_key,
            version_id=int(version_id),
            execution_mode=str(execution_mode or "").strip(),
            market_profile=str(market_profile or "").strip(),
            entity_ids=cls._normalize_entity_ids(entity_ids),
            settings_fp=str(settings_fp or ""),
            env_fp=str(env_fp or ""),
            period=effective_settings.resolve_period(),
            system=cls._build_system_env(),
            settings_snapshot=SettingsSnapshot(
                effective_settings=effective_settings.to_dict(),
                settings_diff=dict(settings_diff or {}),
            ),
            created_at=datetime.now().isoformat(),
            strategy_path=str(strategy_path or strategy_key or "").strip(),
        )

    @classmethod
    def load(cls, output_dir: Path) -> "RuntimeEnv":
        store = ArtifactStore.at(output_dir, kind=SimulateKind.ENUMERATE)
        payload = store.read_json("runtime_env")
        entity_ids = store.read_text_lines("entity_ids")
        return cls.from_dict(payload, entity_ids=entity_ids)

    def save(self, output_dir: Path) -> SavedRuntimeEnvPaths:
        store = ArtifactStore.at(output_dir, kind=SimulateKind.ENUMERATE)
        entity_ids_path = store.write_text_lines("entity_ids", self.entity_ids)
        runtime_env_path = store.write_json("runtime_env", self.to_dict())
        return SavedRuntimeEnvPaths(
            entity_ids_path=entity_ids_path,
            runtime_env_path=runtime_env_path,
        )

    def to_entity_ids_txt(self) -> str:
        ids = self._normalize_entity_ids(self.entity_ids)
        return "\n".join(ids) + ("\n" if ids else "")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_key": self.strategy_key,
            "strategy_path": self.strategy_path or self.strategy_key,
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
    ) -> "RuntimeEnv":
        data = raw or {}
        fingerprints = data.get("fingerprints") or {}
        settings_raw = data.get("settings") or {}
        if "effective_settings" not in settings_raw and "settings_snapshot" in data:
            settings_raw = data.get("settings_snapshot") or {}
        strategy_key = str(data.get("strategy_key") or "")

        return cls(
            strategy_key=strategy_key,
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
            strategy_path=str(data.get("strategy_path") or strategy_key or ""),
        )

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


__all__ = [
    "BacktestPeriod",
    "SystemEnv",
    "SettingsSnapshot",
    "SavedRuntimeEnvPaths",
    "RuntimeEnv",
]
