"""Timeline模式配置读取（框架逻辑）。"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from core.infra.project_context import ProjectContext

logger = logging.getLogger(__name__)


class TimelineConfig:
    """Timeline模式配置解析（面向对象方式）。"""

    @staticmethod
    def resolve_settings(
        *,
        module_name: str,
        performance_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        解析timeline模式配置（框架逻辑）。

        从worker.json读取module配置，合并performance_override。

        Args:
            module_name: 模块名（如"tag"、"strategy.enum"、"strategy.price"）
            performance_override: 用户自定义配置（可选）

        Returns:
            timeline配置字典（包含max_workers、entities_per_job等）

        Raises:
            ValueError: 缺少必需配置字段
        """
        # 从worker.json读取module配置（框架逻辑）
        module_config = ProjectContext.config.get_module_config(module_name)
        if module_config is None:
            raise ValueError(
                f"模块配置未找到: {module_name}，请在worker.json中配置module_task_config.{module_name}"
            )

        # 合并performance_override（框架逻辑）
        settings = module_config.copy()
        if performance_override:
            settings.update(performance_override)

        # 严格验证必需字段（框架逻辑）
        required_fields = ["max_workers"]
        missing_fields = [field for field in required_fields if field not in settings]
        if missing_fields:
            raise ValueError(
                f"timeline配置缺少必需字段: {missing_fields}，"
                f"请在worker.json或performance_override中提供这些字段"
            )

        logger.info(
            "timeline配置解析完成: module=%s, max_workers=%s",
            module_name,
            settings["max_workers"],
        )

        return settings

    @staticmethod
    def parse_performance(
        performance: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        解析performance字典（框架逻辑）。

        提取关键字段：max_workers、entities_per_job、dispatch_probe等。

        Args:
            performance: 原始performance字典

        Returns:
            解析后的performance字典
        """
        parsed = {}

        # 解析max_workers（框架逻辑）
        max_workers = performance.get("max_workers", "auto")
        if isinstance(max_workers, str) and max_workers.lower() == "auto":
            parsed["max_workers"] = "auto"
        else:
            parsed["max_workers"] = int(max_workers)

        # 解析entities_per_job（框架逻辑）
        entities_per_job = performance.get("entities_per_job", "auto")
        if isinstance(entities_per_job, str) and entities_per_job.lower() == "auto":
            parsed["entities_per_job"] = "auto"
        else:
            parsed["entities_per_job"] = int(entities_per_job)

        # 解析其他字段（框架逻辑）
        parsed["dispatch_probe"] = performance.get("dispatch_probe", True)
        parsed["force_main_process"] = performance.get("force_main_process", False)
        parsed["mb_per_entity_staged"] = performance.get("mb_per_entity_staged", None)

        return parsed