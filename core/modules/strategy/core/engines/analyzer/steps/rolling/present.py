"""滚动验证的终端展示：窗口表，不是旋钮战役。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, TextIO, Union

from core.infra.cmd_layout import CmdLayout

from ..campaign.labels import CampaignLabels

_SECTION_WIDTH = 64


class RollingPresenter:
    """滚动窗口对照。"""

    def __init__(self, report: Mapping[str, Any]) -> None:
        self._report = dict(report)

    @classmethod
    def load(cls, report: Union[Mapping[str, Any], str, Path]) -> "RollingPresenter":
        if isinstance(report, Mapping):
            return cls(report)
        path = Path(report)
        if path.is_dir():
            path = path / "report.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"滚动报告格式无效: {path}")
        return cls(payload)

    def present(self, stream: Optional[TextIO] = None) -> None:
        out = stream or sys.stdout
        icon = CmdLayout.icon.get
        report = self._report
        summarized = report.get("report") if isinstance(report.get("report"), dict) else report

        CmdLayout.title.print_banner(f"{icon('chart')} 滚动窗口怎么读", stream=out)
        print(
            f"{icon('gear')} 策略 {report.get('folder') or '-'}  ·  "
            f"{int(summarized.get('n') or report.get('cell_count') or 0)} 段窗口",
            file=out,
            flush=True,
        )
        headline = str(summarized.get("headline") or report.get("headline") or "").strip()
        if headline:
            print(f"   {headline}", file=out, flush=True)
        self._print_table(summarized, out)
        persist = report.get("persist") if isinstance(report.get("persist"), dict) else {}
        path = persist.get("report_path") or report.get("report_path")
        if path:
            print(f"   报告: {path}", file=out, flush=True)

    def _print_table(self, summarized: Mapping[str, Any], out: TextIO) -> None:
        windows = [
            item
            for item in summarized.get("windows") or []
            if isinstance(item, dict)
        ]
        if not windows:
            print("   没有可展示的窗口。", file=out, flush=True)
            return
        headers = ["窗口", "回测", "账户收益", "相对首段", "机会数"]
        rows: List[List[str]] = []
        for item in windows:
            outcomes = item.get("outcomes") if isinstance(item.get("outcomes"), dict) else {}
            vs_first = item.get("vs_first") if isinstance(item.get("vs_first"), dict) else {}
            vid = item.get("version_id")
            rows.append(
                [
                    str(item.get("label") or "-"),
                    f"v{vid}" if vid else "-",
                    CampaignLabels.format_number(
                        "total_return", outcomes.get("portfolio.total_return")
                    ),
                    CampaignLabels.format_delta(
                        "total_return", vs_first.get("portfolio.total_return")
                    )
                    if vs_first
                    else "-",
                    CampaignLabels.format_number(
                        "total_opportunities",
                        outcomes.get("enumerate.total_opportunities"),
                    ),
                ]
            )
        widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(cell))
        line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
        print(f"   {line}", file=out, flush=True)
        print(f"   {'─' * min(_SECTION_WIDTH, sum(widths) + 8)}", file=out, flush=True)
        for row in rows:
            line = "  ".join(row[i].ljust(widths[i]) for i in range(len(headers)))
            print(f"   {line}", file=out, flush=True)
