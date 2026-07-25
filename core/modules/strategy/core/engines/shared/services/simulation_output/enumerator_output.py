"""枚举 version 目录定位与边界读取（无内容 schema）。

消费者: price_factor, portfolio
边界: 解析目录位置、读出 json/dict 与 entity_ids 文本行；业务解析由各引擎完成
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.shared.services.simulation_output.io import ArtifactIO
from core.modules.strategy.core.engines.shared.services.simulation_output.file_names import (
    RUNTIME_ENV_FILE,
)
from core.modules.strategy.core.engines.shared.services.simulation_output.paths import (
    ArtifactPaths,
)


@dataclass(frozen=True)
class EnumOutput:
    """一次枚举 version 目录的布局句柄（不含业务 dataclass）。"""

    output_dir: Path
    version_id: str

    @classmethod
    def open(cls, output_dir: Path, version_id: str) -> "EnumOutput":
        """打开已存在的枚举 version 目录布局。"""
        return cls(output_dir=Path(output_dir), version_id=str(version_id))

    @classmethod
    def resolve_dir(cls, strategy_path: str, version_id: str) -> Path:
        """``simulation/enum/{strategy_path}/{version_id}``。"""
        path_id = str(strategy_path or "").strip()
        vid = str(version_id or "").strip()
        if not path_id:
            raise ValueError("strategy_path 不能为空")
        if not vid:
            raise ValueError("enum version_id 不能为空")
        root = ProjectContext.path.get_strategy_directory_simulation_enum(path_id)
        output_dir = root / vid
        if not output_dir.is_dir():
            raise FileNotFoundError(f"枚举 version 目录不存在: {output_dir}")
        return output_dir

    @property
    def runtime_env_path(self) -> Path:
        return ArtifactPaths.runtime_env_path(self.output_dir)

    @property
    def entity_ids_path(self) -> Path:
        return ArtifactPaths.entity_ids_path(self.output_dir)

    @property
    def entities_dir(self) -> Path:
        return ArtifactPaths.entities_dir(self.output_dir)

    def read_runtime_env(self) -> Dict[str, Any]:
        """读 ``0_runtime_env.json`` 为原始 dict（兼容无 0_ 前缀旧名）。"""
        path = self._resolve_existing(self.runtime_env_path, legacy="runtime_env.json")
        if not path.is_file():
            raise FileNotFoundError(f"缺少 {RUNTIME_ENV_FILE}: {self.output_dir}")
        return ArtifactIO.read_json(path)

    def read_entity_ids(self) -> List[str]:
        path = self._resolve_existing(self.entity_ids_path, legacy="entity_ids.txt")
        return ArtifactIO.read_text_lines(path)

    def stock_investments_path(self, entity_id: str) -> Path:
        return ArtifactPaths.stock_investments_path(self.output_dir, entity_id)

    def goal_achievements_path(self, entity_id: str) -> Path:
        return ArtifactPaths.goal_achievements_path(self.output_dir, entity_id)

    def collect_stock_investment_entity_ids(self) -> List[str]:
        return ArtifactPaths.collect_entity_ids_from_stock_investments(self.output_dir)

    @staticmethod
    def _resolve_existing(path: Path, *, legacy: str) -> Path:
        if path.is_file():
            return path
        legacy_path = path.parent / legacy
        if legacy_path.is_file():
            return legacy_path
        return path


__all__ = ["EnumOutput"]
