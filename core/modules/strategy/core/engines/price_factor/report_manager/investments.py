"""价格回测每股 ``entities/{id}_price_investments.csv``。

本文件:
- PriceInvestmentRow / EntityInvestments: 行模型与 CSV 读写
  边界: 负责 entity 级 price CSV；不负责 enum 源 CSV 或 overall 汇总
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Sequence

from core.modules.strategy.core.engines.price_factor.report_manager.report_consts import (
    ReportPaths,
)
from core.utils.io.csv_io import read_csv_to_dicts, write_dicts_to_csv


@dataclass
class PriceInvestmentRow:
    """价格层单笔投资记录（成交回放后）。"""

    opportunity_id: str = ""
    enter_date: str = ""
    enter_price: float = 0.0
    exit_date: str = ""
    exit_price: float = 0.0
    roi: float = 0.0
    holding_days: int = 0
    holding_trading_days: int = 0
    exit_reason: str = ""
    skip_reason: str = ""
    lifecycle: str = ""
    result: str = ""

    COLUMN_ORDER: ClassVar[Sequence[str]] = (
        "opportunity_id",
        "enter_date",
        "enter_price",
        "exit_date",
        "exit_price",
        "roi",
        "holding_days",
        "holding_trading_days",
        "exit_reason",
        "skip_reason",
        "lifecycle",
        "result",
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "PriceInvestmentRow":
        data = raw or {}
        return cls(
            opportunity_id=str(data.get("opportunity_id") or "").strip(),
            enter_date=str(data.get("enter_date") or "").strip(),
            enter_price=_as_float(data.get("enter_price")),
            exit_date=str(data.get("exit_date") or "").strip(),
            exit_price=_as_float(data.get("exit_price")),
            roi=_as_float(data.get("roi")),
            holding_days=_as_int(data.get("holding_days")),
            holding_trading_days=_as_int(data.get("holding_trading_days")),
            exit_reason=str(data.get("exit_reason") or "").strip(),
            skip_reason=str(data.get("skip_reason") or "").strip(),
            lifecycle=str(data.get("lifecycle") or "").strip(),
            result=str(data.get("result") or "").strip(),
        )


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


class EntityInvestments:
    """``entities/{id}_investments.csv`` 读写。"""

    @classmethod
    def path(cls, output_dir: Path, entity_id: str) -> Path:
        return ReportPaths.investments_csv(output_dir, entity_id)

    @classmethod
    def save(
        cls,
        output_dir: Path,
        entity_id: str,
        rows: Sequence[PriceInvestmentRow | Dict[str, Any]],
    ) -> Path:
        path = cls.path(output_dir, entity_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payloads: List[Dict[str, Any]] = []
        for row in rows:
            if isinstance(row, PriceInvestmentRow):
                payloads.append(row.to_dict())
            else:
                payloads.append(dict(row or {}))
        if not payloads:
            # 写表头，便于契约固定
            payloads = [{name: "" for name in PriceInvestmentRow.COLUMN_ORDER}]
        write_dicts_to_csv(path, payloads, preferred_order=PriceInvestmentRow.COLUMN_ORDER)
        return path

    @classmethod
    def load(cls, output_dir: Path, entity_id: str) -> List[PriceInvestmentRow]:
        path = cls.path(output_dir, entity_id)
        if not path.is_file():
            return []
        raw_rows = read_csv_to_dicts(path)
        out: List[PriceInvestmentRow] = []
        for raw in raw_rows:
            row = PriceInvestmentRow.from_dict(raw)
            # 跳过仅表头占位行
            if not row.opportunity_id and not row.enter_date:
                continue
            out.append(row)
        return out

    @classmethod
    def load_all(
        cls,
        output_dir: Path,
        entity_ids: Sequence[str],
    ) -> Dict[str, List[PriceInvestmentRow]]:
        return {
            str(eid): cls.load(output_dir, eid)
            for eid in entity_ids
            if str(eid or "").strip()
        }


__all__ = ["EntityInvestments", "PriceInvestmentRow"]
