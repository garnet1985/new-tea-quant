#!/usr/bin/env python3
from enum import Enum


class InvestmentResult(Enum):
    WIN = 'win'
    LOSS = 'loss'
    OPEN = 'open'


__all__ = ['InvestmentResult']


