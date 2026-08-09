"""跨模块契约：adapter 基类与历史加载器。"""

from __future__ import annotations

from core.modules.adapter.core.base_adapter import BaseOpportunityAdapter
from core.modules.adapter.core.history_loader import HistoryLoader

__all__ = ["BaseOpportunityAdapter", "HistoryLoader"]
