#!/usr/bin/env python3
"""
Common enums exposed for strategies and simulator.
"""
from enum import Enum


class InvestmentResult(Enum):
    WIN = 'win'
    LOSS = 'loss'
    OPEN = 'open'
