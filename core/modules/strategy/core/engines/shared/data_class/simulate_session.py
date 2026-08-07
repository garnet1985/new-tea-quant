"""一次 simulate 编排会话（Facade → Pipeline）。

消费者: enumerator, price_factor, portfolio
其它: Facade

本文件:
- SimulateSession: discovery 之后、Pipeline 之前组装的会话袋
  边界: 负责携带 EnabledStrategyInfo + FingerprintResult + kind/steps/enum_version；
        不负责算指纹、读写 DB 缓存、或引擎内 tick 业务
  命名: 不用 RuntimeContext（易与 BE job / HookRuntime 混淆）；这是一次 simulate 调用的 session
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
)
from core.modules.strategy.core.services.simulation_cache.fingerprints import (
    FingerprintResult,
)


@dataclass
class SimulateSession:
    """一次 simulate 的编排会话（不含 CacheManager）。

    每次 ``Strategy.simulate`` 新建；不在内存里跨请求复用（settings / env 可能变）。
    """

    strategy_info: EnabledStrategyInfo
    fp_res: FingerprintResult
    kind: SimulateKind
    enum_version: Optional[str] = None
    steps: List[SimulateKind] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        strategy_info: EnabledStrategyInfo,
        fp_res: FingerprintResult,
        kind: SimulateKind,
    ) -> "SimulateSession":
        """由已发现策略 + 指纹结果打开会话（steps / enum_version 稍后由 Facade 填）。"""
        return cls(strategy_info=strategy_info, fp_res=fp_res, kind=kind)

    @property
    def settings_fp(self) -> str:
        return self.fp_res.settings_fp

    @property
    def env_fp(self) -> str:
        return self.fp_res.env_fp

    @property
    def effective_settings(self):
        return self.fp_res.effective_settings

    @property
    def settings_diff(self):
        return self.fp_res.settings_diff

    @property
    def global_entity_cache(self):
        return self.fp_res.global_entity_cache

    @property
    def entity_ids(self) -> List[str]:
        return self.fp_res.entity_ids

    @property
    def strategy_key(self) -> str:
        return str(
            self.strategy_info.unique_relative_path or self.strategy_info.key or ""
        )

    @property
    def strategy_folder(self) -> Path:
        """Discovered strategy root; all on-disk strategy paths hang off this."""
        info = self.strategy_info
        if info is not None and getattr(info, "folder", None) is not None:
            try:
                return info.resolved_folder()
            except Exception:
                folder = Path(info.folder)
                if folder.is_absolute():
                    return folder
        from core.infra.project_context import ProjectContext

        return ProjectContext.path.coerce_strategy_folder(self.strategy_key)

    def validate_for_run(self) -> None:
        """跑 Pipeline 前自检。"""
        if self.strategy_info is None:
            raise ValueError("SimulateSession.strategy_info 不能为空")
        if self.fp_res is None:
            raise ValueError("SimulateSession.fp_res 不能为空")
        if not self.settings_fp or not self.env_fp:
            raise ValueError("settings_fp / env_fp 不能为空")
        if self.fp_res.global_entity_cache is None:
            raise ValueError("global_entity_cache 不能为空")
        if self.kind == SimulateKind.FULL:
            raise ValueError("simulate(kind=full) 暂不支持")
        if not self.steps:
            raise ValueError("steps 为空：请先 resolve steps")
        if (
            self.kind != SimulateKind.ENUMERATE
            and self.enum_version is None
            and SimulateKind.ENUMERATE not in self.steps
        ):
            raise ValueError(
                f"{self.kind.value} 需要 enum_version 或 steps 中包含 enumerate"
            )


__all__ = ["SimulateSession"]
