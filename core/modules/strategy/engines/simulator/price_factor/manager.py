#!/usr/bin/env python3
"""Price factor engine manager bridge."""

from .simulator import PriceFactorSimulator


class PriceFactorManager(PriceFactorSimulator):
    """Bridge manager backed by legacy price factor implementation."""

