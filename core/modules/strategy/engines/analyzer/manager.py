#!/usr/bin/env python3
"""Analyzer engine manager bridge."""

from .analyzer import Analyzer


class AnalyzerManager(Analyzer):
    """Bridge manager backed by legacy analyzer implementation."""

