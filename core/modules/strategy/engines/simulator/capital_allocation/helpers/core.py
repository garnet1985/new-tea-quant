#!/usr/bin/env python3
import json
from datetime import datetime


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, (int, float)):
            return float(obj) if isinstance(obj, float) else int(obj)
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return super().default(obj)


__all__ = ["DateTimeEncoder"]
