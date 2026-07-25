"""ReportManager 生命周期基类（四引擎共用语义，产物形状私有）。

契约: begin(子类工厂) → collect* → finalize(= summarize + save) → present*
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, TextIO


@dataclass
class BaseReportManager(ABC):
    """薄编排基类：统一生命周期，不统一 overall / profiler 字段。

    边界:
    - 负责: collect / summarize / save / present / finalize 语义
    - 不负责: version 分配细节、worker binding、引擎私有产物 schema
    - 调用方: 各引擎 ReportManager 子类
    """

    output_dir: Path

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)

    def collect(self, item: Any) -> None:
        """增量收集（默认 no-op；enum/scanner 等按需覆盖）。"""
        _ = item

    @abstractmethod
    def summarize(self) -> Any:
        """聚合全局结果（引擎私有 summary / dataclass）。"""

    @abstractmethod
    def save(self) -> Any:
        """落盘；返回路径句柄或引擎约定值。"""

    def present(self, stream: Optional[TextIO] = None) -> None:
        """CLI / adapter 展示（默认 no-op）。"""
        _ = stream

    def finalize(self, **kwargs: Any) -> Any:
        """模板方法：summarize → save。子类可 override 以接收 run_result / sim 等。"""
        _ = kwargs
        summary = self.summarize()
        saved = self.save()
        return saved if saved is not None else summary


__all__ = ["BaseReportManager"]
