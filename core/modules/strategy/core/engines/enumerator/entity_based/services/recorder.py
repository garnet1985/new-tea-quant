"""entity_based 枚举产物 Recorder（暂为 entity_based 私有实现）。"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.helpers.opportunity_csv import OpportunityCsvHelper
from core.modules.strategy.core.services.data.simulation_output_recorder import (
    SimulationOutputRecorder,
)

logger = logging.getLogger(__name__)

SCOPE_STOCK_IDS_FILENAME = "0_scope_stock_ids.txt"
RUN_PRECONDITION_FILENAME = "0_run_precondition.json"

# opportunities CSV 不写 nested / 内部字段；targets 从 completed_targets 拆行
_OPPORTUNITY_CSV_EXCLUDED: Set[str] = {
    "completed_targets",
    "config_hash",
    "created_at",
    "updated_at",
    "record_of_today",
    "dynamic_loss_active",
    "dynamic_loss_highest",
    "expired_reason",
    "expired_date",
    "exit_reason",
    "protect_loss_active",
    "scan_date",
    "stock",
    "stock_id",
    "stock_name",
    "strategy_name",
    "strategy_version",
    "holding_days",
    "max_drawdown",
    "metadata",
    "price_return",
    "tracking",
    "triggered_stop_loss_idx",
    "extra_fields",
}
_TARGET_CSV_COLUMNS = (
    "opportunity_id",
    "date",
    "sell_price",
    "sell_ratio",
    "profit",
    "weighted_profit",
    "reason",
    "roi",
    "sell_prev_close",
    "sell_at_limit_down",
    "sell_bar_volume",
)


@dataclass
class EntityBasedEnumeratorRecorder(SimulationOutputRecorder):
    """entity_based 枚举输出：preprocess / 子进程 CSV / 后续 postprocess。"""

    settings_fp: str = ""
    env_fp: str = ""
    _job_buffer: List[Dict[str, Any]] = field(default_factory=list, repr=False)

    # ── 主进程：run 初始化 ──

    @classmethod
    def init(
        cls,
        strategy_id: str,
        *,
        stock_ids: List[str],
        settings_fp: str,
        env_fp: str,
        settings_diff: Dict[str, Any],
        extra: Optional[Dict[str, Any]] = None,
    ) -> EntityBasedEnumeratorRecorder:
        """回测前准备：分配 version 目录、写入 preprocess，返回 full context recorder。"""
        output_dir, version_id = cls._allocate_enum_version_dir(strategy_id)
        recorder = cls(
            output_dir=output_dir,
            strategy_id=strategy_id,
            version_id=version_id,
            version_dir_name=str(version_id),
            settings_fp=settings_fp,
            env_fp=env_fp,
        )
        recorder.save_preprocess(
            stock_ids=stock_ids,
            settings_diff=settings_diff,
            extra=extra,
        )
        return recorder

    @classmethod
    def _allocate_enum_version_dir(cls, strategy_id: str) -> Tuple[Path, int]:
        root = ProjectContext.path.get_strategy_directory_simulation_enum(strategy_id)
        return cls.allocate_version_dir(strategy_id, root)

    def save_preprocess(
        self,
        *,
        stock_ids: List[str],
        settings_diff: Dict[str, Any],
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """回测开始前：in-scope universe + 运行前置信息（单次写入）。"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._write_scope_stock_ids(stock_ids)
        payload: Dict[str, Any] = {
            "status": "running",
            "strategy_id": self.strategy_id,
            "version_id": self.version_id,
            "version_dir_name": self.version_dir_name,
            "settings_fingerprint": self.settings_fp,
            "env_fingerprint": self.env_fp,
            "entity_count": len(stock_ids),
            "settings_diff": dict(settings_diff or {}),
        }
        if extra:
            payload.update(extra)
        path = self.output_dir / RUN_PRECONDITION_FILENAME
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Saved run precondition: %s", path)

    # ── 跨进程：扩展 snapshot ──

    def to_snapshot(self) -> Dict[str, Any]:
        snapshot = super().to_snapshot()
        snapshot["settings_fp"] = self.settings_fp
        snapshot["env_fp"] = self.env_fp
        return snapshot

    @classmethod
    def from_snapshot(cls, snapshot: Dict[str, Any]) -> EntityBasedEnumeratorRecorder:
        base = super().from_snapshot(snapshot)
        return cls(
            output_dir=base.output_dir,
            strategy_id=base.strategy_id,
            version_id=base.version_id,
            version_dir_name=base.version_dir_name,
            settings_fp=str(snapshot.get("settings_fp") or ""),
            env_fp=str(snapshot.get("env_fp") or ""),
        )

    # ── 子进程：job 级 opportunities 写入 ──

    def buffer_opportunities(self, opportunities: List[Dict[str, Any]]) -> None:
        self._job_buffer.extend(list(opportunities or []))

    def flush_job_opportunities(self) -> Dict[str, int]:
        """将本 job 缓冲的 opportunities 按 entity 写入 CSV 并清空 buffer。"""
        if not self._job_buffer:
            return {"written_files": 0, "opportunities_count": 0, "target_files": 0}

        grouped = self._group_opportunities_by_entity(self._job_buffer)
        opportunity_files = 0
        target_files = 0
        opportunity_rows_count = 0

        for entity_id, opportunities in grouped.items():
            opp_rows, target_rows = self._build_csv_rows(opportunities)
            if opp_rows:
                OpportunityCsvHelper.write(self.output_dir, entity_id, opp_rows)
                opportunity_files += 1
                opportunity_rows_count += len(opp_rows)
            if target_rows:
                self._write_targets_csv(entity_id, target_rows)
                target_files += 1

        buffer_count = len(self._job_buffer)
        self._job_buffer.clear()
        logger.info(
            "Wrote job CSV: dir=%s, opp_files=%d, target_files=%d, opp_rows=%d",
            self.output_dir,
            opportunity_files,
            target_files,
            opportunity_rows_count,
        )
        return {
            "written_files": opportunity_files,
            "opportunities_count": opportunity_rows_count,
            "target_files": target_files,
        }

    # ── helpers ──

    def _write_scope_stock_ids(self, stock_ids: List[str]) -> None:
        normalized = sorted({str(item).strip() for item in stock_ids if str(item).strip()})
        path = self.output_dir / SCOPE_STOCK_IDS_FILENAME
        path.write_text("\n".join(normalized) + ("\n" if normalized else ""), encoding="utf-8")
        logger.info("Saved scope stock ids: %s (%d)", path, len(normalized))

    @staticmethod
    def _group_opportunities_by_entity(
        buffer: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for entry in buffer:
            entity_id = str(entry.get("entity_id") or "").strip()
            if not entity_id:
                continue
            opportunity = entry.get("opportunity")
            if not isinstance(opportunity, dict):
                continue
            grouped.setdefault(entity_id, []).append(dict(opportunity))
        return grouped

    def _write_targets_csv(self, entity_id: str, target_rows: List[Dict[str, Any]]) -> None:
        from core.utils.io.csv_io import write_dicts_to_csv

        self.output_dir.mkdir(parents=True, exist_ok=True)
        write_dicts_to_csv(
            self.output_dir / f"{entity_id}_targets.csv",
            target_rows,
            preferred_order=list(_TARGET_CSV_COLUMNS),
        )

    @staticmethod
    def _build_csv_rows(
        opportunities: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """内存 opportunity → 两张 CSV 的行数据。

        - opportunities 行：每笔机会一行（去掉 completed_targets 等内部字段）
        - targets 行：每笔机会的每次平仓/止盈一条（来自 completed_targets）
        """
        opportunity_rows: List[Dict[str, Any]] = []
        target_rows: List[Dict[str, Any]] = []

        for opportunity in opportunities:
            for target in opportunity.get("completed_targets") or []:
                if isinstance(target, dict):
                    target_rows.append(EntityBasedEnumeratorRecorder._csv_row(dict(target)))

            row = {
                k: v
                for k, v in opportunity.items()
                if k not in _OPPORTUNITY_CSV_EXCLUDED
            }
            opportunity_rows.append(EntityBasedEnumeratorRecorder._csv_row(row))

        return opportunity_rows, target_rows

    @staticmethod
    def _csv_row(row: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(row)
        for key, value in out.items():
            if isinstance(value, (dict, list)):
                out[key] = json.dumps(value, ensure_ascii=False)
            elif value is None:
                out[key] = ""
        return out


__all__ = [
    "EntityBasedEnumeratorRecorder",
    "SCOPE_STOCK_IDS_FILENAME",
    "RUN_PRECONDITION_FILENAME",
]
