"""枚举 version 产物读取句柄（下游主进程侧）。

消费者: price_factor, portfolio（enumerator 写路径用 EnumOutput / investment_csv）
边界: 基于 EnumOutput 定位；投影 runtime / period / entity_ids；委托加载 investments/goals CSV
不负责: 写 P/O 自有产物；CSV 行 schema 定义见 investment_csv
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

from core.modules.strategy.core.engines.shared.services.simulation_output.enumerator_output import (
    EnumOutput,
)

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.shared.services.simulation_output.investment_csv import (
        EntityInvestmentCsv,
        GoalAchievementCsv,
    )


@dataclass(frozen=True)
class _SettingsSnapshotView:
    effective_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EnumRuntimeMeta:
    """下游需要的 runtime 字段投影（非 enumerator.RuntimeEnv）。"""

    strategy_key: str
    strategy_path: str
    market_profile: str
    settings_snapshot: _SettingsSnapshotView


@dataclass(frozen=True)
class EnumSource:
    """一次枚举 version 的只读句柄（定位 + 常用字段投影）。"""

    output_dir: Path
    version_id: str
    layout: EnumOutput
    runtime: EnumRuntimeMeta
    entity_ids: List[str]
    start_date: str
    end_date: str

    @classmethod
    def resolve_dir(cls, strategy_path: str, version_id: str) -> Path:
        return EnumOutput.resolve_dir(strategy_path, version_id)

    @classmethod
    def load(cls, output_dir: Path, version_id: str) -> "EnumSource":
        layout = EnumOutput.open(Path(output_dir), str(version_id))
        raw = layout.read_runtime_env()
        entity_ids = layout.read_entity_ids()
        period = raw.get("period") if isinstance(raw.get("period"), dict) else {}
        settings_raw = raw.get("settings") if isinstance(raw.get("settings"), dict) else {}
        if "effective_settings" not in settings_raw and isinstance(raw.get("settings_snapshot"), dict):
            settings_raw = raw.get("settings_snapshot") or {}
        strategy_key = str(raw.get("strategy_key") or "").strip()
        strategy_path = str(raw.get("strategy_path") or strategy_key).strip()
        runtime = EnumRuntimeMeta(
            strategy_key=strategy_key,
            strategy_path=strategy_path,
            market_profile=str(raw.get("market_profile") or "").strip(),
            settings_snapshot=_SettingsSnapshotView(
                effective_settings=dict(settings_raw.get("effective_settings") or {}),
            ),
        )
        return cls(
            output_dir=layout.output_dir,
            version_id=str(version_id),
            layout=layout,
            runtime=runtime,
            entity_ids=list(entity_ids),
            start_date=str(period.get("start_date") or "").strip(),
            end_date=str(period.get("end_date") or "").strip(),
        )

    @classmethod
    def stub(
        cls,
        output_dir: Path,
        version_id: str = "1",
        *,
        entity_ids: List[str] | None = None,
        start_date: str = "20240101",
        end_date: str = "20240131",
        market_profile: str = "",
        strategy_key: str = "demo",
    ) -> "EnumSource":
        """测试用句柄（不读盘）。"""
        layout = EnumOutput.open(Path(output_dir), str(version_id))
        key = str(strategy_key or "").strip()
        return cls(
            output_dir=layout.output_dir,
            version_id=str(version_id),
            layout=layout,
            runtime=EnumRuntimeMeta(
                strategy_key=key,
                strategy_path=key,
                market_profile=str(market_profile or "").strip(),
                settings_snapshot=_SettingsSnapshotView(),
            ),
            entity_ids=list(entity_ids or []),
            start_date=str(start_date or "").strip(),
            end_date=str(end_date or "").strip(),
        )

    def load_investments(self, entity_id: str) -> "EntityInvestmentCsv":
        """读 ``{entity_id}_stock_investments.csv``。"""
        from core.modules.strategy.core.engines.shared.services.simulation_output.investment_csv import (
            EntityInvestmentCsv,
        )

        return EntityInvestmentCsv.load(self.output_dir, entity_id)

    def load_goals(self, entity_id: str) -> "GoalAchievementCsv":
        """读 ``{entity_id}_goal_achievements.csv``。"""
        from core.modules.strategy.core.engines.shared.services.simulation_output.investment_csv import (
            GoalAchievementCsv,
        )

        return GoalAchievementCsv.load(self.output_dir, entity_id)

    def investment_entity_ids(self) -> List[str]:
        """按 investments CSV 文件名收集 entity_id（runtime 列表为空时兜底）。"""
        from core.modules.strategy.core.engines.shared.services.simulation_output.investment_csv import (
            EntityInvestmentCsv,
        )

        return EntityInvestmentCsv.collect_entity_ids(self.output_dir)


__all__ = [
    "EnumRuntimeMeta",
    "EnumSource",
]
