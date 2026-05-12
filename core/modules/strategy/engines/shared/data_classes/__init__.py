#!/usr/bin/env python3
"""Shared data classes across engines."""

from .investment_base import BaseInvestment
from .opportunity import Opportunity

__all__ = ["BaseInvestment", "Opportunity"]
