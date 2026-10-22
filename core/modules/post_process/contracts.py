"""跨模块契约：协议类型与 BaseAdapter。"""

from __future__ import annotations

from core.modules.post_process.core.base_adapter import BaseAdapter
from core.modules.post_process.core.protocol import (
    Opportunity,
    ScanSessionReport,
    StrategyScanReport,
)
from core.modules.post_process.core.post_processor_types import (
    AdapterBinding,
    PostProcessorDefinition,
)

__all__ = [
    "BaseAdapter",
    "AdapterBinding",
    "Opportunity",
    "PostProcessorDefinition",
    "ScanSessionReport",
    "StrategyScanReport",
]
