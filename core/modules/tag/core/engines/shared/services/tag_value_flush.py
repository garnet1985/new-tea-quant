"""Tag value 落库（buffer → ``sys_tag_value``）。

消费者: TagSlicePipeline, TagEntityPipeline

本文件:
- TagValueFlushService: 将 executor buffer 行转为 DB 行并攒批 save_batch
  边界: 负责编码与写入；不负责 hooks / BE 调度
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.modules.tag.engines.shared.report_save_buffer import TagReportSaveBuffer

if TYPE_CHECKING:
    from core.modules.data_manager.data_services.stock.sub_services.tag_service import (
        TagDataService,
    )

logger = logging.getLogger(__name__)


class TagValueFlushService:
    """主进程攒批写入 tag values。"""

    def __init__(
        self,
        tag_data_service: Optional["TagDataService"],
        *,
        dry_run: bool = False,
        batch_size: int = 5000,
        entity_type: str = "stock",
    ) -> None:
        self._tags = tag_data_service
        self._dry_run = bool(dry_run)
        self._entity_type = str(entity_type or "stock").strip() or "stock"
        self._buffer = TagReportSaveBuffer(
            save_fn=self._save_db_rows,
            batch_size=batch_size,
        )

    @classmethod
    def encode_json_value(cls, tag_result: Any) -> str:
        """编码为 ``sys_tag_value.json_value``。"""
        if isinstance(tag_result, dict):
            payload = {k: v for k, v in tag_result.items() if k != "tag_name"}
            if not payload:
                payload = dict(tag_result)
        else:
            payload = {"value": tag_result}
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def to_db_row(
        cls,
        buffered: Dict[str, Any],
        *,
        entity_type: str = "stock",
    ) -> Dict[str, Any]:
        """executor buffer 行 → TagDataService.save_batch 行。"""
        if not isinstance(buffered, dict):
            raise TypeError("buffered tag value must be dict")
        entity_id = str(buffered.get("entity_id") or "").strip()
        tag_definition_id = buffered.get("tag_definition_id")
        as_of_date = str(buffered.get("as_of_date") or "").strip()
        if not entity_id:
            raise ValueError("tag value missing entity_id")
        if tag_definition_id is None or tag_definition_id == "":
            raise ValueError("tag value missing tag_definition_id")
        if not as_of_date:
            raise ValueError("tag value missing as_of_date")

        if "json_value" in buffered and buffered.get("json_value") is not None:
            json_value = str(buffered.get("json_value"))
        else:
            # buffer 形态：value + 可选 start/end；编码时去掉非结果字段
            encode_src = {
                k: v
                for k, v in buffered.items()
                if k
                not in {
                    "entity_id",
                    "entity_type",
                    "tag_definition_id",
                    "tag_name",
                    "as_of_date",
                    "json_value",
                }
            }
            if "value" not in encode_src and "value" in buffered:
                encode_src["value"] = buffered.get("value")
            json_value = cls.encode_json_value(encode_src)

        row: Dict[str, Any] = {
            "entity_id": entity_id,
            "entity_type": str(
                buffered.get("entity_type") or entity_type or "stock"
            ).strip()
            or "stock",
            "tag_definition_id": int(tag_definition_id),
            "as_of_date": as_of_date,
            "json_value": json_value,
        }
        if buffered.get("start_date") is not None:
            row["start_date"] = buffered.get("start_date")
        if buffered.get("end_date") is not None:
            row["end_date"] = buffered.get("end_date")
        return row

    def extend(self, buffered_rows: List[Dict[str, Any]]) -> int:
        """追加 buffer 行；达到 batch_size 时写入。返回追加行数。"""
        if not buffered_rows:
            return 0
        self._buffer.extend_in_chunks(list(buffered_rows))
        return len(buffered_rows)

    def flush(self) -> int:
        """刷出剩余缓冲。返回累计已写入行数。"""
        self._buffer.flush()
        return int(self._buffer.saved_row_count)

    @property
    def saved_row_count(self) -> int:
        return int(self._buffer.saved_row_count)

    def _save_db_rows(self, rows: List[Dict[str, Any]]) -> int:
        db_rows = [
            self.to_db_row(r, entity_type=self._entity_type) for r in rows
        ]
        if self._dry_run:
            logger.info("[DRY RUN] skip save_batch rows=%d", len(db_rows))
            return len(db_rows)
        if self._tags is None:
            raise ValueError("tag_data_service is required unless dry_run=True")
        return int(self._tags.save_batch(db_rows) or len(db_rows))


__all__ = ["TagValueFlushService"]
