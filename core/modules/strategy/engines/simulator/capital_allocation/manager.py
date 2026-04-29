#!/usr/bin/env python3
"""Capital allocation engine manager bridge."""

from .simulator import CapitalAllocationSimulator


class CapitalAllocationManager(CapitalAllocationSimulator):
    """Bridge manager backed by legacy capital allocation implementation."""

