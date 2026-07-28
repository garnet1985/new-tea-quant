"""Tag 计算进度水位（incremental：上次算到的业务日，非 max(as_of)）。

SOT：``sys_tag_calc_progress.last_calculated_end``，经 ``TagDataService``：

- ``get_entity_calc_progress(scenario_name)`` → entity_id → YYYYMMDD
- ``mark_entity_calc_progress(scenario_name, entity_ends)`` → 成功后推进（取 max）
- ``clear_calc_progress_by_scenario(scenario_id)`` → refresh / recompute

``sys_tag_value.calculated_at`` / ``sys_tag_scenario.updated_at`` / max(as_of)
均不得当作业务水位。
"""

from __future__ import annotations

__all__ = []
