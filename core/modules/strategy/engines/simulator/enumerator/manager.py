#!/usr/bin/env python3
"""Enumerator engine manager bridge."""

from .opportunity_enumerator import OpportunityEnumerator


class EnumeratorManager(OpportunityEnumerator):
    """Bridge manager backed by legacy enumerator implementation."""

