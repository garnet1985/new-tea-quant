#!/usr/bin/env python3
"""amplitude_limit Compiled / Resolved dataclasses。"""

from __future__ import annotations

from ..shared.base import CompiledRuleBase


class AmplitudeLimitCompiled(CompiledRuleBase):
    def resolve(self, stock_id: str):
        pass


__all__ = ["AmplitudeLimitCompiled"]
