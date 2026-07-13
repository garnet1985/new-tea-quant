"""Layer 2：进入 engine 前的策略上下文（settings diff + 指纹环境）。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import StrategySettings

from .discovered_strategy import DiscoveredStrategy


@dataclass
class StrategyContext(DiscoveredStrategy):
    """在 ``DiscoveredStrategy`` 之上绑定回测会话：有效 settings、diff、指纹、输出路径。"""

    userspace_root: Path
    effective_settings: StrategySettings
    settings_diff: Dict[str, Any]
    start_date: str
    end_date: str
    entity_ids: List[str]
    fingerprint_hash: str
    output_dir: Path
    version_id: int
    version_dir_name: str

    @property
    def strategy_name(self) -> str:
        return self.id

    @classmethod
    def from_discovered(
        cls,
        discovered: DiscoveredStrategy,
        *,
        userspace_root: Path,
        user_settings: Optional[Dict[str, Any]] = None,
    ) -> StrategyContext:
        from core.infra.project_context import ProjectContext
        from core.modules.strategy.core.services.data.params_resolver import BacktestParamsResolver
        from core.modules.strategy.core.services.data.simulation_output_recorder import (
            SimulationOutputRecorder,
        )

        effective_user = user_settings if user_settings is not None else discovered.disk_settings
        effective, settings_diff = StrategySettings.calculate_effective_settings(
            discovered.disk_settings,
            effective_user,
        )
        params = BacktestParamsResolver.resolve_all_params(
            discovered.folder,
            effective.raw_settings,
        )
        enum_root = ProjectContext.path.get_strategy_directory_simulation_enum(discovered.id)
        output_dir, version_id = SimulationOutputRecorder.allocate_version_dir(
            discovered.id,
            enum_root,
        )
        entity_ids = list(params["stock_list"])
        start_date = params["start_date"]
        end_date = params["end_date"]
        fingerprint_hash = effective.fingerprint_hash(
            settings_diff=settings_diff,
            entity_ids=entity_ids,
            start_date=start_date,
            end_date=end_date,
        )

        return cls(
            key=discovered.key,
            id=discovered.id,
            strategies_root=discovered.strategies_root,
            folder=discovered.folder,
            strategy_file=discovered.strategy_file,
            settings_file=discovered.settings_file,
            settings=discovered.settings,
            worker_class=discovered.worker_class,
            worker_module_path=discovered.worker_module_path,
            worker_class_name=discovered.worker_class_name,
            worker_file_path=discovered.worker_file_path,
            userspace_root=userspace_root,
            effective_settings=effective,
            settings_diff=settings_diff,
            start_date=start_date,
            end_date=end_date,
            entity_ids=entity_ids,
            fingerprint_hash=fingerprint_hash,
            output_dir=output_dir,
            version_id=version_id,
            version_dir_name=str(version_id),
        )

    @property
    def versions_root(self) -> Path:
        return self.userspace_root / self.id / "versions"


__all__ = ["StrategyContext"]
