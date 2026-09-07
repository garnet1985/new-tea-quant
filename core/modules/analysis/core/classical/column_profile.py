"""Column profiling — constant / varying, numeric / text (no domain schema)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


class ColumnProfiler:
    @classmethod
    def summarize(cls, values: Sequence[Any]) -> Dict[str, Any]:
        cleaned = [value for value in values if value not in (None, "")]
        if not cleaned:
            return {"role": "empty", "count": 0}

        numeric = [cls.coerce_float(value) for value in cleaned]
        if all(item is not None for item in numeric):
            nums = [float(item) for item in numeric if item is not None]
            unique = sorted(set(nums))
            if len(unique) == 1:
                return {
                    "role": "constant",
                    "dtype": "numeric",
                    "count": len(nums),
                    "value": unique[0],
                }
            return {
                "role": "varying",
                "dtype": "numeric",
                "count": len(nums),
                "unique_count": len(unique),
                "min": unique[0],
                "max": unique[-1],
            }

        texts = [str(value) for value in cleaned]
        unique_text = sorted(set(texts))
        if len(unique_text) == 1:
            return {
                "role": "constant",
                "dtype": "text",
                "count": len(texts),
                "value": unique_text[0],
            }
        return {
            "role": "varying",
            "dtype": "text",
            "count": len(texts),
            "unique_count": len(unique_text),
        }

    @staticmethod
    def coerce_float(value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value).strip())
        except (TypeError, ValueError):
            return None


__all__ = ["ColumnProfiler"]
