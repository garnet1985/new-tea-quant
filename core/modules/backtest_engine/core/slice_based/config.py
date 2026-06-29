"""
Backtest Engine - Slice-based Config

切片模式的配置解析。

职责：
- 解析slice配置（reader_workers、queue_capacity、slice_open_days等）
- 严格验证必需字段（缺少字段报错）
- 面向对象设计（SliceConfig类 + 静态方法）

特点：
- 读算分离配置（reader_workers + compute_processes）
- 管道队列控制配置（queue_capacity + preload_depth）
- 更严格的验证（slice更容易OOM）
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SliceConfig:
    """切片模式配置解析（面向对象方式）。
    
    职责：
    - 解析slice配置
    - 严格验证必需字段
    - 提供默认值（合理范围）
    """
    
    @staticmethod
    def resolve_settings(
        *,
        module_name: str,
        performance_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """解析slice配置。
        
        Args:
            module_name: 模块名称（用于读取worker.json）
            performance_override: 配置覆盖（可选）
            
        Returns:
            Dict[str, Any]: 配置字典
            
        Raises:
            ValueError: 缺少必需字段或字段值无效
        """
        # 读取模块配置（从worker.json）
        from core.infra.project_context import ProjectContext
        
        module_config = ProjectContext.config.get_module_config(module_name)
        if module_config is None:
            raise ValueError(
                f"模块配置未找到: {module_name}，请在worker.json中配置"
            )
        
        # 合并配置（模块配置 + 性能覆盖）
        settings = dict(module_config)
        if performance_override:
            settings.update(performance_override)
        
        # 严格验证必需字段
        SliceConfig._validate_required_fields(settings)
        
        # 解析slice配置
        SliceConfig._resolve_slice_settings(settings)
        
        logger.info(
            "Slice配置解析: reader_workers=%s, queue=%s, preload=%s, slice_days=%s",
            settings.get("reader_workers"),
            settings.get("queue_capacity"),
            settings.get("preload_depth"),
            settings.get("slice_open_days"),
        )
        
        return settings
    
    @staticmethod
    def _validate_required_fields(settings: Dict[str, Any]) -> None:
        """严格验证必需字段。
        
        Args:
            settings: 配置字典
            
        Raises:
            ValueError: 缺少必需字段或字段值无效
        """
        # 必需字段（slice特有）
        required_fields = [
            "slice_open_days",  # 切片天数
        ]
        
        missing_fields = [
            field for field in required_fields
            if field not in settings or settings[field] in (None, "")
        ]
        
        if missing_fields:
            raise ValueError(
                f"Slice配置缺少必需字段: {missing_fields}，"
                f"请在worker.json中配置"
            )
        
        # 验证字段值范围
        slice_open_days = int(settings.get("slice_open_days", 0))
        if slice_open_days <= 0:
            raise ValueError(
                f"slice_open_days必须大于0: {slice_open_days}"
            )
    
    @staticmethod
    def _resolve_slice_settings(settings: Dict[str, Any]) -> None:
        """解析slice特有配置。
        
        Args:
            settings: 配置字典（会被修改）
        """
        # Reader workers（默认2）
        if settings.get("reader_workers") in (None, "", "auto"):
            settings["reader_workers"] = 2
        
        # Compute processes（默认1，单进程）
        if settings.get("compute_processes") in (None, "", "auto"):
            settings["compute_processes"] = 1
        
        # Queue capacity（默认10）
        if settings.get("queue_capacity") in (None, "", "auto"):
            settings["queue_capacity"] = 10
        
        # Preload depth（默认2）
        if settings.get("preload_depth") in (None, "", "auto"):
            settings["preload_depth"] = 2
        
        # 验证字段值范围
        reader_workers = int(settings["reader_workers"])
        if reader_workers <= 0:
            raise ValueError(f"reader_workers必须大于0: {reader_workers}")
        
        compute_processes = int(settings["compute_processes"])
        if compute_processes <= 0:
            raise ValueError(f"compute_processes必须大于0: {compute_processes}")
        
        queue_capacity = int(settings["queue_capacity"])
        if queue_capacity <= 0:
            raise ValueError(f"queue_capacity必须大于0: {queue_capacity}")
        
        preload_depth = int(settings["preload_depth"])
        if preload_depth <= 0:
            raise ValueError(f"preload_depth必须大于0: {preload_depth}")


__all__ = ["SliceConfig"]