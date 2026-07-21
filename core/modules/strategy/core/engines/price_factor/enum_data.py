"""枚举 version 轻量加载（价格回测主进程输入；不读 entities CSV）。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.enumerator.shared.report_manager.runtime_snapshot import (
    RuntimeSnapshot,
)


@dataclass(frozen=True)
class EnumVersionData:
    """枚举 version 的主进程侧句柄。

    只含目录、version、runtime（period / entity_ids / market_profile）。
    ``entities/`` 下 CSV 由 worker 按 batch 再读。
    """

    output_dir: Path
    version_id: str
    runtime: RuntimeSnapshot

    @property
    def entity_ids(self) -> List[str]:
        return list(self.runtime.entity_ids)

    @property
    def start_date(self) -> str:
        return str(self.runtime.period.start_date or "").strip()

    @property
    def end_date(self) -> str:
        return str(self.runtime.period.end_date or "").strip()


def resolve_enum_version_dir(strategy_path: str, version_id: str) -> Path:
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


def load_enum_version(output_dir: Path, version_id: str) -> EnumVersionData:
    """读 ``0_runtime_env.json`` + ``0_entity_ids.txt``；不读 entities CSV。"""
    directory = Path(output_dir)
    runtime = RuntimeSnapshot.load(directory)
    return EnumVersionData(
        output_dir=directory,
        version_id=str(version_id),
        runtime=runtime,
    )


__all__ = [
    "EnumVersionData",
    "load_enum_version",
    "resolve_enum_version_dir",
]
