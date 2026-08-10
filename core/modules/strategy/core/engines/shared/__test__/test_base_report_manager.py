"""BaseReportManager：finalize 顺序 summarize → save。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List

import pytest

from core.modules.strategy.core.engines.shared.services.report_manager import (
    BaseReportManager,
)

pytestmark = pytest.mark.force_run


@dataclass
class _StubReportManager(BaseReportManager):
    calls: List[str] = field(default_factory=list)
    summary_value: Any = "summary"
    save_value: Any = "saved"

    def summarize(self) -> Any:
        self.calls.append("summarize")
        return self.summary_value

    def save(self) -> Any:
        self.calls.append("save")
        return self.save_value


def test_finalize_calls_summarize_then_save(tmp_path: Path) -> None:
    mgr = _StubReportManager(output_dir=tmp_path)
    result = mgr.finalize()
    assert mgr.calls == ["summarize", "save"]
    assert result == "saved"


def test_collect_and_present_default_noop(tmp_path: Path) -> None:
    mgr = _StubReportManager(output_dir=tmp_path)
    mgr.collect({"x": 1})
    mgr.present()
    assert mgr.calls == []
