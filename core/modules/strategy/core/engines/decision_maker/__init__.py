"""决策者模式 — 资金回测回放（人替换选谁 / 买多少）。

本包:
- DecisionEngine: 会话状态机（pick / done / reset / next / finalize）
- DecisionStore: ``simulations/{vid}/decision/{dm_id}/``
- DecisionRepl: 命令行 SQL 模式
  边界: 不另起成交规则；不写 SimulateKind；UI 不在本包
"""

from .engine import DecisionEngine
from .exceptions import AmbiguousSessionsError, DecisionError
from .store import DecisionStore

__all__ = [
    "AmbiguousSessionsError",
    "DecisionEngine",
    "DecisionError",
    "DecisionStore",
]
