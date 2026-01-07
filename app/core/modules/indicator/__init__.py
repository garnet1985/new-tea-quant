#!/usr/bin/env python3
"""
Indicator Module - 技术指标计算模块

提供技术指标计算服务，基于 pandas-ta-classic
所有模块都可以使用此服务
"""

from .indicator_service import IndicatorService

__all__ = ['IndicatorService']
