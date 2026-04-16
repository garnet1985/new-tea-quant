from __future__ import annotations

from typing import Any, Dict, Optional, List, Tuple
import json
import logging

from core.modules.tag.base_tag_worker import BaseTagWorker

logger = logging.getLogger(__name__)


class ActivityRatio20TagWorker(BaseTagWorker):
    """
    活跃度标签（ratio20）：

    - ratio20 = amount_t / mean(amount_{t-19..t})
    - 产生 2 个布尔标签：activity_high / activity_low
    - 每天计算一次，但仅当状态发生变化时才落库（减少存储、避免 tag 多了变乱）
    """

    def on_before_execute_tagging(self):
        # 初始化每个 tag_definition 的上次状态：优先从 DB 读取最新事件，否则默认 False
        entity_id = self.entity["id"]
        for tag_definition in self.tag_definitions:
            key = self._tracker_state_key(entity_id, tag_definition.id)
            self.tracker[key] = self._load_latest_bool_value_from_db(
                entity_id=entity_id,
                tag_definition_id=tag_definition.id,
            )

    def calculate_tag(
        self,
        as_of_date: str,
        historical_data: Dict[str, Any],
        tag_definition: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        主流程（只记录变化）：

        1) 获取计算必要信息（core 参数）
        2) 计算当前 tag 的布尔值
        3) 与上一次状态对比；若变化则返回写入 payload，否则返回 None
        """
        # 1) core 参数
        core = self._read_core_params()

        # 2) 当前布尔值
        new_value = self._compute_current_tag_value(
            as_of_date=as_of_date,
            historical_data=historical_data,
            tag_definition=tag_definition,
            core=core,
        )
        if new_value is None:
            return None

        # 3) 仅在变化时写入（delta）
        entity_id = self.entity["id"]
        tag_definition_id = int(tag_definition.id)
        if not self._is_value_changed(
            entity_id=entity_id,
            tag_definition_id=tag_definition_id,
            new_value=new_value,
        ):
            return None

        self._remember_latest_value(
            entity_id=entity_id,
            tag_definition_id=tag_definition_id,
            new_value=new_value,
        )
        return {"value": {"value": new_value}}

    # ---------------------------------------------------------------------
    # helpers
    # ---------------------------------------------------------------------

    def _read_core_params(self) -> Dict[str, Any]:
        """
        读取 settings.core，并做最小类型归一化。
        """
        core = self.config.get("core", {}) or {}
        return {
            "window": int(core.get("window", 20) or 20),
            "high_threshold": float(core.get("high_threshold", 1.5) or 1.5),
            "low_threshold": float(core.get("low_threshold", 0.7) or 0.7),
        }

    def _compute_current_tag_value(
        self,
        *,
        as_of_date: str,
        historical_data: Dict[str, Any],
        tag_definition: Any,
        core: Dict[str, Any],
    ) -> Optional[bool]:
        """
        计算当前 tag_definition 对应的布尔值。

        - activity_high: ratio20 >= high_threshold
        - activity_low : ratio20 <= low_threshold
        """
        daily_klines = historical_data.get("stock.kline", []) or []
        if not daily_klines:
            return None

        ratio20 = self._compute_activity_ratio(
            daily_klines,
            as_of_date,
            window=int(core["window"]),
        )
        if ratio20 is None:
            return None

        tag_name = getattr(tag_definition, "tag_name", None) or getattr(tag_definition, "name", "")
        if tag_name == "activity_high":
            return ratio20 >= float(core["high_threshold"])
        if tag_name == "activity_low":
            return ratio20 <= float(core["low_threshold"])
        return None

    def _is_value_changed(self, *, entity_id: str, tag_definition_id: int, new_value: bool) -> bool:
        """
        判断与 tracker 中的上一次状态是否不同。
        """
        key = self._tracker_state_key(entity_id, tag_definition_id)
        prev = bool(self.tracker.get(key, False))
        return new_value != prev

    def _remember_latest_value(self, *, entity_id: str, tag_definition_id: int, new_value: bool) -> None:
        """
        将最新状态写回 tracker，供后续日期对比。
        """
        key = self._tracker_state_key(entity_id, tag_definition_id)
        self.tracker[key] = bool(new_value)

    @staticmethod
    def _tracker_state_key(entity_id: str, tag_definition_id: int) -> str:
        """
        tracker 内部使用的“状态键”。

        这是实现细节；外部只需理解我们会记住“上一次布尔状态”以支持只记录变化。
        """
        return f"last_bool_{entity_id}_{tag_definition_id}"

    @staticmethod
    def _compute_activity_ratio(
        daily_klines: List[Dict[str, Any]],
        as_of_date: str,
        *,
        window: int,
    ) -> Optional[float]:
        usable = [k for k in daily_klines if k.get("date") and k.get("date") <= as_of_date]
        if len(usable) < window:
            return None

        last = usable[-window:]
        amounts: List[float] = []
        for k in last:
            v = k.get("amount")
            if v is None or v == "":
                return None
            try:
                amounts.append(float(v))
            except (TypeError, ValueError):
                return None

        avg = sum(amounts) / float(len(amounts)) if amounts else 0.0
        if avg <= 0:
            return 0.0
        return float(amounts[-1]) / avg

    def _load_latest_bool_value_from_db(self, *, entity_id: str, tag_definition_id: int) -> bool:
        """
        读取该 entity + tag_definition 的最新一条 tag_value 事件，返回其 bool 状态。
        若不存在或解析失败，返回 False（默认状态）。
        """
        try:
            rows = self.tag_data_service.db.execute_sync_query(
                """
                SELECT json_value
                FROM sys_tag_value
                WHERE entity_id = %s AND tag_definition_id = %s
                ORDER BY as_of_date DESC
                LIMIT 1
                """,
                (entity_id, tag_definition_id),
            )
            if not rows:
                return False
            raw = rows[0].get("json_value")
            if raw is None or raw == "":
                return False
            if isinstance(raw, dict):
                payload = raw
            else:
                payload = json.loads(raw) if isinstance(raw, str) else {}
            v = payload.get("value")
            if isinstance(v, bool):
                return v
            if isinstance(v, (int, float)):
                return bool(v)
            return False
        except Exception as e:
            logger.warning(
                "读取最新 tag_value 失败，使用默认 False: entity=%s tag_definition_id=%s err=%s",
                entity_id,
                tag_definition_id,
                e,
            )
            return False

