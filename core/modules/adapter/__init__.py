"""Adapter 模块（``modules.adapter``）。

公开门面::

    from core.modules.adapter import Adapter

基类与 HistoryLoader::

    from core.modules.adapter.contracts import BaseOpportunityAdapter, HistoryLoader
"""

from .adapter import Adapter

__all__ = ["Adapter"]
