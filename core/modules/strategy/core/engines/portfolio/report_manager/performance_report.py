"""Portfolio performance.json（轻量）。"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, TextIO, TYPE_CHECKING

from core.infra.cmd_layout import CmdLayout
from core.modules.strategy.core.services.artifacts import (
    PERFORMANCE_FILE,
)


@dataclass
class PerformanceReport:
    PERFORMANCE_FILE = PERFORMANCE_FILE

    strategy_key: str = ""
    version_id: int = 0
    elapsed_seconds: float = 0.0
    created_at: str = ""

    @classmethod
    def build(
        cls,
        *,
        strategy_key: str = "",
        version_id: int = 0,
        elapsed_seconds: float = 0.0,
    ) -> "PerformanceReport":
        return cls(
            strategy_key=strategy_key,
            version_id=version_id,
            elapsed_seconds=float(elapsed_seconds or 0.0),
            created_at=datetime.now().isoformat(),
        )

    @classmethod
    def load(cls, output_dir: Path) -> "PerformanceReport":
        path = Path(output_dir) / cls.PERFORMANCE_FILE
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save(self, output_dir: Path) -> Path:
        path = Path(output_dir) / self.PERFORMANCE_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def present(self, stream: Optional[TextIO] = None) -> None:
        out = stream or sys.stdout
        icon = CmdLayout.icon.get
        CmdLayout.title.print_section(f"{icon('clock')} 性能", stream=out)
        print(
            f"{icon('rocket')} {self.elapsed_seconds:.2f}s",
            file=out,
            flush=True,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_key": self.strategy_key,
            "version_id": self.version_id,
            "elapsed_seconds": self.elapsed_seconds,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "PerformanceReport":
        data = raw or {}
        return cls(
            strategy_key=str(data.get("strategy_key") or ""),
            version_id=int(data.get("version_id") or 0),
            elapsed_seconds=float(data.get("elapsed_seconds") or 0.0),
            created_at=str(data.get("created_at") or ""),
        )


class PerformanceReportHandle:
    def __init__(self, manager: "ReportManager") -> None:
        self._manager = manager
        self._report: Optional[PerformanceReport] = None

    def build(self, *, elapsed_seconds: float = 0.0) -> "PerformanceReportHandle":
        self._report = PerformanceReport.build(
            strategy_key=self._manager.strategy_key,
            version_id=self._manager.version_id,
            elapsed_seconds=elapsed_seconds,
        )
        return self

    def save(self) -> Path:
        if self._report is None:
            self.build()
        assert self._report is not None
        return self._report.save(self._manager.output_dir)

    def present(self, stream: Optional[TextIO] = None) -> None:
        PerformanceReport.load(self._manager.output_dir).present(stream=stream)


if TYPE_CHECKING:
    from core.modules.strategy.core.engines.portfolio.report_manager.report_manager import (
        ReportManager,
    )


__all__ = ["PerformanceReport", "PerformanceReportHandle"]
