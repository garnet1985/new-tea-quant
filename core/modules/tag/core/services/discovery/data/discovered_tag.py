"""Tag 发现三层 data class（draft → info → enabled）。

消费者: DiscoveryService

本文件:
- TagDraft: 磁盘发现 + settings/hooks 轻量校验（未通过则丢弃）
- TagInfo: 验证通过、可 UI 展示（含 settings dict、hooks_class）
- EnabledTagInfo: is_enabled=True，供后续 calculation 消费
  边界: 负责发现阶段元数据与校验；不负责 TagSettings 全量校验或引擎编排
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from core.infra.discovery import Discovery
from core.modules.tag.core.services.discovery.hooks_loader import TagHooksLoader

if TYPE_CHECKING:
    from core.modules.tag.core.engines.per_entity.shared.hooks.tag_hooks import TagHooks

logger = logging.getLogger(__name__)


@dataclass
class TagDraft:
    """发现的 tag draft（未验证，内部使用）。

    约定：文件夹下同时存在 ``tag.py`` 和 ``settings.py``。
    """

    unique_relative_path: str
    tag_file: Path
    settings_file: Path
    _validation_errors: List[str] = field(default_factory=list, init=False)

    def id(self) -> str:
        return self.unique_relative_path

    def is_valid(self) -> bool:
        self._validation_errors = []
        self._validate_settings()
        self._validate_hooks()
        return len(self._validation_errors) == 0

    def validation_errors(self) -> List[str]:
        return self._validation_errors

    def _validate_settings(self) -> None:
        try:
            settings_dict = Discovery.file.load_python_config(
                self.settings_file, var_name="settings"
            )
            if not isinstance(settings_dict, dict):
                self._validation_errors.append("settings.py必须返回dict")
                return

            meta = settings_dict.get("meta")
            if not isinstance(meta, dict):
                self._validation_errors.append("settings.py缺少meta字段或meta不是dict")
                return

            key = str(meta.get("key") or "").strip()
            if not key:
                self._validation_errors.append("settings.py缺少meta.key字段")

            if "is_enabled" not in settings_dict:
                self._validation_errors.append("settings.py缺少is_enabled字段")

            calculation = settings_dict.get("calculation")
            if not isinstance(calculation, dict):
                self._validation_errors.append(
                    "settings.py缺少calculation或calculation不是dict"
                )
            else:
                execution = calculation.get("execution")
                if not isinstance(execution, dict):
                    self._validation_errors.append(
                        "settings.py中calculation.execution必须是dict"
                    )
                else:
                    execution_mode = execution.get("mode")
                    if execution_mode not in ["entity_based", "slice_based"]:
                        self._validation_errors.append(
                            "settings.py中calculation.execution.mode必须是"
                            "entity_based或slice_based"
                        )

        except Exception as exc:
            self._validation_errors.append(f"无法加载settings.py: {exc}")

    def _validate_hooks(self) -> None:
        hooks_result = TagHooksLoader.load_hooks_class(
            self.tag_file.parent, self.unique_relative_path
        )
        if hooks_result is None:
            self._validation_errors.append("tag.py缺少公开 hooks 类")


@dataclass
class TagInfo(TagDraft):
    """验证合格的 tag 信息（UI 显示）。

    符合以下条件：
    1. tag.py 和 settings.py 存在
    2. settings.py 包含 meta.key（全局唯一）
    3. settings.py 包含 is_enabled
    4. calculation.execution.mode ∈ {entity_based, slice_based}
    5. tag.py 包含公开 hooks 类
    """

    key: str = ""
    display_name: str = ""
    is_enabled: bool = False
    settings: Dict[str, Any] = field(default_factory=dict)
    hooks_class: Optional[Type["TagHooks"]] = None
    hooks_module_path: str = ""
    hooks_class_name: str = ""
    hooks_file_path: Path = field(default_factory=lambda: Path("."))
    folder: Path = field(default_factory=lambda: Path("."))

    @classmethod
    def from_draft(cls, draft: TagDraft) -> Optional["TagInfo"]:
        if not draft.is_valid():
            logger.warning(
                "Tag validation failed: %s, errors: %s",
                draft.unique_relative_path,
                draft.validation_errors(),
            )
            return None

        settings_dict = Discovery.file.load_python_config(
            draft.settings_file, var_name="settings"
        )

        hooks_result = TagHooksLoader.load_hooks_class(
            draft.tag_file.parent, draft.unique_relative_path
        )
        if hooks_result is None:
            return None

        hooks_module_path, hooks_class_name, hooks_file_path, hooks_class = hooks_result

        return cls(
            unique_relative_path=draft.unique_relative_path,
            tag_file=draft.tag_file,
            settings_file=draft.settings_file,
            folder=draft.tag_file.parent,
            key=str(settings_dict.get("meta", {}).get("key", "")).strip(),
            display_name=str(
                settings_dict.get("meta", {}).get("display_name", "")
            ).strip(),
            is_enabled=bool(settings_dict.get("is_enabled", False)),
            settings=settings_dict,
            hooks_class=hooks_class,
            hooks_module_path=hooks_module_path,
            hooks_class_name=hooks_class_name,
            hooks_file_path=hooks_file_path,
        )


@dataclass
class EnabledTagInfo(TagInfo):
    """启用的 tag 信息（calculation 消费）。``is_enabled=True`` 约束。"""

    def get_execution_mode(self) -> str:
        """``calculation.execution.mode``（发现阶段已校验）。"""
        calculation = self.settings.get("calculation")
        if not isinstance(calculation, dict):
            raise ValueError("settings.calculation 须为 dict")
        execution = calculation.get("execution")
        if not isinstance(execution, dict):
            raise ValueError("settings.calculation.execution 须为 dict")
        mode = str(execution.get("mode") or "").strip()
        if mode not in ("entity_based", "slice_based"):
            raise ValueError(
                f"settings.calculation.execution.mode 非法: {mode!r}"
            )
        return mode


__all__ = ["TagDraft", "TagInfo", "EnabledTagInfo"]
