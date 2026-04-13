from __future__ import annotations

from typing import Any, Dict, Optional

from core.modules.tag.core.base_tag_worker import BaseTagWorker


class MacroRegimeTagWorker(BaseTagWorker):
    """general 模式示例 worker。"""

    def calculate_tag(
        self,
        as_of_date: str,
        historical_data: Dict[str, Any],
        tag_definition: Any,
    ) -> Optional[Dict[str, Any]]:
        gdp_rows = historical_data.get("macro.gdp", []) or []
        if not gdp_rows:
            return None

        latest = gdp_rows[-1]
        return {
            "value": {
                "as_of_date": as_of_date,
                "quarter": latest.get("quarter"),
                "gdp_yoy": latest.get("gdp_yoy"),
            }
        }
