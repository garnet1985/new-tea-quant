"""枚举 version 目录定位与原始 IO（无业务投影）。

消费者: EnumSource；enumerator（写路径经 ArtifactPaths）
边界: 目录位置、json/dict、entity_ids 文本行
不负责: runtime/period 字段投影（见 enum_source.EnumSource）
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
        """读 ``runtime_env.json``。"""
        path = self.runtime_env_path
        if not path.is_file():
            raise FileNotFoundError(f"缺少 {RUNTIME_ENV_FILE}: {self.output_dir}")
        return ArtifactIO.read_json(path)

    def read_entity_ids(self) -> List[str]:
        return ArtifactIO.read_text_lines(self.entity_ids_path)

    def stock_investments_path(self, entity_id: str) -> Path:
        return ArtifactPaths.stock_investments_path(self.output_dir, entity_id)

    def goal_achievements_path(self, entity_id: str) -> Path:
        return ArtifactPaths.goal_achievements_path(self.output_dir, entity_id)

    def collect_stock_investment_entity_ids(self) -> List[str]:
        return ArtifactPaths.collect_entity_ids_from_stock_investments(self.output_dir)


__all__ = ["EnumOutput"]
