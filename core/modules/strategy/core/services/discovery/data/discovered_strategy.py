"""策略发现三层 data class（draft → info → enabled）。

本文件:
- StrategyDraft: 磁盘发现 + settings/hooks 校验（未通过则丢弃）
- StrategyInfo: 验证通过、可 UI 展示（含 settings dict、hooks_class）
- EnabledStrategyInfo: is_enabled=True，供 scan / simulate 消费
  边界: 负责发现阶段元数据与校验；不负责指纹、缓存或引擎编排
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from core.infra.discovery import Discovery
from core.modules.strategy.core.services.discovery.worker_loader import StrategyWorkerLoader

if TYPE_CHECKING:
    from core.modules.strategy.core.hooks.base import StrategyHooks

logger = logging.getLogger(__name__)


@dataclass
class StrategyDraft:
    """发现的策略draft（未验证，内部使用）。

    约定：文件夹下同时存在 strategy.py 和 settings.py。
    """

    unique_relative_path: str
    strategy_file: Path
    settings_file: Path
    _validation_errors: List[str] = field(default_factory=list, init=False)

    def id(self) -> str:
        return self.unique_relative_path

    def is_valid(self) -> bool:
        """验证策略是否合格，返回True/False。"""
        self._validation_errors = []
        self._validate_settings()
        self._validate_hooks()
        return len(self._validation_errors) == 0

    def validation_errors(self) -> List[str]:
        """返回验证错误列表（供用户参考）。"""
        return self._validation_errors

    def _validate_settings(self) -> None:
        """验证settings.py字段。"""
        try:
            settings_dict = Discovery.file.load_python_config(
                self.settings_file, var_name="settings"
            )
            if not isinstance(settings_dict, dict):
                self._validation_errors.append("settings.py必须返回dict")
                return

            # 验证meta.key
            meta = settings_dict.get("meta")
            if not isinstance(meta, dict):
                self._validation_errors.append("settings.py缺少meta字段或meta不是dict")
                return

            key = str(meta.get("key") or "").strip()
            if not key:
                self._validation_errors.append("settings.py缺少meta.key字段")

            # 验证is_enabled
            if "is_enabled" not in settings_dict:
                self._validation_errors.append("settings.py缺少is_enabled字段")

            # 验证 simulation.execution.mode
            simulation = settings_dict.get("simulation")
            if not isinstance(simulation, dict):
                self._validation_errors.append("settings.py缺少simulation或simulation不是dict")
            else:
                execution = simulation.get("execution")
                if not isinstance(execution, dict):
                    self._validation_errors.append(
                        "settings.py中simulation.execution必须是dict"
                    )
                else:
                    execution_mode = execution.get("mode")
                    if execution_mode not in ["entity_based", "slice_based"]:
                        self._validation_errors.append(
                            "settings.py中simulation.execution.mode必须是"
                            "entity_based或slice_based"
                        )

        except Exception as exc:
            self._validation_errors.append(f"无法加载settings.py: {exc}")

    def _validate_hooks(self) -> None:
        """验证strategy.py中的hooks类。"""
        hooks_result = StrategyWorkerLoader.load_hooks_class(
            self.strategy_file.parent, self.unique_relative_path
        )
        if hooks_result is None:
            self._validation_errors.append(
                "strategy.py缺少继承StrategyHooks的公开类"
            )

@dataclass
class StrategyInfo(StrategyDraft):
    """验证合格的策略信息（UI显示）。

    符合以下条件：
    1. strategy.py 和 settings.py 存在
    2. settings.py 包含 meta.key（全局唯一）
    3. settings.py 包含 is_enabled
    4. strategy.py 包含公开类，继承 StrategyHooks
    5. 路径符合机器可读命名规则
    """

    key: str = ""
    display_name: str = ""
    is_enabled: bool = False
    settings: Dict[str, Any] = field(default_factory=dict)
    hooks_class: Optional[Type["StrategyHooks"]] = None
    hooks_module_path: str = ""

    # 添加folder字段（从draft继承时会自动填充）
    folder: Path = field(default_factory=lambda: Path("."))

    @classmethod
    def from_draft(cls, draft: StrategyDraft) -> Optional[StrategyInfo]:
        """从draft构建StrategyInfo（如果验证通过）。"""
        if not draft.is_valid():
            logger.warning(
                "Strategy validation failed: %s, errors: %s",
                draft.unique_relative_path,
                draft.validation_errors(),
            )
            return None

        # 加载settings
        settings_dict = Discovery.file.load_python_config(
            draft.settings_file, var_name="settings"
        )

        # 加载hooks
        hooks_result = StrategyWorkerLoader.load_hooks_class(
            draft.strategy_file.parent, draft.unique_relative_path
        )
        if hooks_result is None:
            return None

        hooks_module_path, hooks_class_name, _hooks_file_path, hooks_class = hooks_result

        # 构建StrategyInfo
        return cls(
            unique_relative_path=draft.unique_relative_path,
            strategy_file=draft.strategy_file,
            settings_file=draft.settings_file,
            folder=draft.strategy_file.parent,  # 添加folder字段
            key=str(settings_dict.get("meta", {}).get("key", "")).strip(),
            display_name=str(
                settings_dict.get("meta", {}).get("display_name", "")
            ).strip(),
            is_enabled=bool(settings_dict.get("is_enabled", False)),
            settings=settings_dict,
            hooks_class=hooks_class,
            hooks_module_path=hooks_module_path,
        )

@dataclass
class EnabledStrategyInfo(StrategyInfo):
    """启用的策略信息（回测/扫描）。
    is_enabled=True约束。
    """

    def get_execution_mode(self) -> str:
        """``simulation.execution.mode``（发现阶段已校验）。"""
        simulation = self.settings.get("simulation")
        if not isinstance(simulation, dict):
            raise ValueError("settings.simulation 须为 dict")
        execution = simulation.get("execution")
        if not isinstance(execution, dict):
            raise ValueError("settings.simulation.execution 须为 dict")
        mode = str(execution.get("mode") or "").strip()
        if mode not in ("entity_based", "slice_based"):
            raise ValueError(
                f"settings.simulation.execution.mode 非法: {mode!r}"
            )
        return mode


__all__ = ["StrategyDraft", "StrategyInfo", "EnabledStrategyInfo"]