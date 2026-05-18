#!/usr/bin/env python3
"""lot_size Compiled / Resolved dataclasses。"""

from __future__ import annotations

from ..shared.base import CompiledRuleBase


class LotSizeCompiled(CompiledRuleBase):
    def resolve(self, stock_id: str):
        pass


__all__ = ["LotSizeCompiled"]
