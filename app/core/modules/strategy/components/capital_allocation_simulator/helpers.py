#!/usr/bin/env python3
"""
辅助函数模块

包含 JSON 编码器等工具函数
"""

import json
from datetime import datetime


class DateTimeEncoder(json.JSONEncoder):
    """自定义 JSON 编码器，处理 datetime 对象和其他不可序列化的类型"""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, (int, float)):
            return float(obj) if isinstance(obj, float) else int(obj)
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        return super().default(obj)
