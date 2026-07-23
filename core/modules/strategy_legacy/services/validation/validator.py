#!/usr/bin/env python3
"""Validation service entrypoints."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from .settings import StrategySettings, ValidationReport


def build_settings(raw_settings: Dict[str, Any]) -> StrategySettings:
    """Build normalized settings object from raw dict."""
    if not isinstance(raw_settings, dict):
        raise ValueError("raw_settings must be a dict")
    return StrategySettings(raw_settings=dict(raw_settings))


def validate_settings(raw_settings: Dict[str, Any]) -> ValidationReport:
    """Validate settings and return structured report."""
    settings = build_settings(raw_settings)
    return settings.validate()


def normalize_and_validate(raw_settings: Dict[str, Any]) -> Tuple[Dict[str, Any], ValidationReport]:
    """Return normalized settings dict together with validation report."""
    settings = build_settings(raw_settings)
    report = settings.validate()
    return settings.to_dict(), report

