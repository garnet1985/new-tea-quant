"""磁盘仿真 version 索引：按 settings_fp + env_fp 命中 step 产物。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import ArtifactStore, RUNTIME_ENV_FILE
from core.modules.strategy.core.services.artifacts.version_meta import (
    VersionMetaStore,
)
from core.modules.strategy.core.services.simulation_cache.fingerprints import (
    FingerprintResult,
)

logger = logging.getLogger(__name__)

_KIND_VALUE = {
    SimulateKind.ENUMERATE: "enumerate",
    SimulateKind.PRICE_FACTOR: "price_factor",
    SimulateKind.PORTFOLIO: "portfolio",
}


class SimulationVersionStore:
    """按磁盘 version meta + 产物目录查 simulate cache。"""

    @classmethod
    def find_enum_version(
        cls,
        strategy_folder: Union[str, Path],
        fps: FingerprintResult,
    ) -> Optional[str]:
        root = ArtifactStore.simulations_root(strategy_folder)
        vid = VersionMetaStore.find_version_by_fingerprints(
            root,
            str(fps.settings_fp or ""),
            str(fps.env_fp or ""),
        )
        if not vid:
            cls._log_env_invalid_on_settings_match(root, fps)
            return None
        enum_dir = root / vid / ArtifactStore.step_dir_name(SimulateKind.ENUMERATE)
        if not cls._step_artifacts_present(enum_dir):
            return None
        return vid

    @classmethod
    def get_cache(
        cls,
        strategy_folder: Union[str, Path],
        fps: FingerprintResult,
        kind: SimulateKind,
    ) -> Optional[Dict[str, Any]]:
        root = ArtifactStore.simulations_root(strategy_folder)
        vid = VersionMetaStore.find_version_by_fingerprints(
            root,
            str(fps.settings_fp or ""),
            str(fps.env_fp or ""),
        )
        if not vid:
            cls._log_env_invalid_on_settings_match(root, fps)
            return None
        try:
            store = ArtifactStore.resolve(
                strategy_folder, kind=kind, version_id=vid
            )
        except FileNotFoundError:
            return None
        if not cls._step_artifacts_present(store.output_dir):
            logger.warning(
                "disk simulate cache miss (artifacts missing): kind=%s version=%s dir=%s",
                kind.value,
                vid,
                store.output_dir,
            )
            return None
        payload = cls._build_step_payload(store, kind)
        if payload is None:
            return None
        return {_KIND_VALUE[kind]: payload}

    @classmethod
    def _log_env_invalid_on_settings_match(
        cls,
        simulations_root: Path,
        fps: FingerprintResult,
    ) -> None:
        alt = VersionMetaStore.find_version_by_settings_fp(
            simulations_root,
            str(fps.settings_fp or ""),
        )
        if not alt:
            return
        entry = VersionMetaStore.get_registry_entry(simulations_root, alt)
        if VersionMetaStore.is_env_invalid(entry, str(fps.env_fp or "")):
            logger.info(
                "simulate cache miss: 环境已失效 version=%s（配置相同，当前环境不可复用）",
                alt,
            )

    @classmethod
    def record_step_complete(
        cls,
        strategy_folder: Union[str, Path],
        *,
        version_id: Union[str, int],
        kind: SimulateKind,
        fps: FingerprintResult,
        output_dir: Union[str, Path],
        entity_ids: Optional[list] = None,
        strategy_name: str = "",
    ) -> None:
        from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
            StrategySettings,
        )

        root = ArtifactStore.simulations_root(strategy_folder)
        vid = str(version_id or "").strip()
        semantic = StrategySettings.extract_effective_settings(fps.effective_settings)
        VersionMetaStore.register_version(
            root,
            vid,
            settings_fp=str(fps.settings_fp or ""),
            env_fp=str(fps.env_fp or ""),
        )
        VersionMetaStore.write_effective_settings(
            root,
            vid,
            settings=semantic,
            entity_ids=list(entity_ids or fps.entity_ids or []),
        )

    @classmethod
    def get_cache_by_version_id(
        cls,
        strategy_folder: Union[str, Path],
        version_id: str,
        kind: SimulateKind,
    ) -> Optional[Dict[str, Any]]:
        """vid → step 产物（与双指纹命中等价，不要求当前 env/settings 匹配）。"""
        root = ArtifactStore.simulations_root(strategy_folder)
        vid = str(version_id or "").strip()
        if not vid or VersionMetaStore.resolve_version(root, vid) is None:
            return None
        if not VersionMetaStore.step_has_artifacts(root, vid, kind):
            return None
        try:
            store = ArtifactStore.resolve(strategy_folder, kind=kind, version_id=vid)
        except FileNotFoundError:
            return None
        payload = cls._build_step_payload(store, kind)
        if payload is None:
            return None
        return {_KIND_VALUE[kind]: payload}

    @staticmethod
    def _step_artifacts_present(output_dir: Path) -> bool:
        path = Path(output_dir)
        return path.is_dir() and (path / RUNTIME_ENV_FILE).is_file()

    @classmethod
    def _build_step_payload(
        cls, store: ArtifactStore, kind: SimulateKind
    ) -> Optional[Dict[str, Any]]:
        output_dir = store.output_dir
        payload: Dict[str, Any] = {
            "success": True,
            "output_dir": str(output_dir),
            "version_id": store.version_id,
        }
        try:
            store._ensure_runtime()
            payload["strategy_key"] = store.runtime.strategy_key
        except Exception:
            pass

        ui = cls._load_ui_dict(output_dir, kind)
        if ui:
            payload.update(ui)
        return payload

    @staticmethod
    def _load_ui_dict(output_dir: Path, kind: SimulateKind) -> Optional[Dict[str, Any]]:
        try:
            if kind is SimulateKind.ENUMERATE:
                from core.modules.strategy.core.engines.enumerator.common.report_manager.overall_report import (
                    OverallReport,
                )
            elif kind is SimulateKind.PRICE_FACTOR:
                from core.modules.strategy.core.engines.price_factor.report_manager.overall_report import (
                    OverallReport,
                )
            else:
                from core.modules.strategy.core.engines.portfolio.report_manager.overall_report import (
                    OverallReport,
                )
            return OverallReport.load(output_dir).to_ui_dict()
        except Exception:
            return None


__all__ = ["SimulationVersionStore"]
