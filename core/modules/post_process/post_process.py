"""PostProcess 门面 — 协议规范化、Adapter / PostProcessor 发现与执行。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple, Type

from core.modules.post_process.core.adapter_loader import AdapterLoader
from core.modules.post_process.core.adapter_validator import AdapterValidator
from core.modules.post_process.core.post_processor_executor import PostProcessorExecutor
from core.modules.post_process.core.post_processor_loader import PostProcessorLoader
from core.modules.post_process.core.post_processor_types import PostProcessorDefinition
from core.modules.post_process.core.post_processor_validator import PostProcessorValidator
from core.modules.post_process.core.protocol import Opportunity, ScanSessionReport
from core.modules.post_process.core.session_builder import (
    build_session_report,
    goal_summary_from_settings,
    opportunity_from_scan_item,
)


class PostProcess:
    """扫描后续处理门面（协议 + PostProcessor / Adapter）。"""

    # ----- protocol -----

    @staticmethod
    def build_session_report(
        *,
        scan_date: str,
        strategy_name: str,
        opportunities: Sequence[Any],
        goal: Optional[Dict[str, Any]] = None,
        strategy_version: str = "",
        emitted_at: str = "",
    ) -> ScanSessionReport:
        """将单策略扫描结果规范为 ``ScanSessionReport``。"""
        return build_session_report(
            scan_date=scan_date,
            strategy_name=strategy_name,
            opportunities=opportunities,
            goal=goal,
            strategy_version=strategy_version,
            emitted_at=emitted_at,
        )

    @staticmethod
    def opportunity_from_scan_item(
        item: Any,
        *,
        strategy_name: str = "",
        index: int = 0,
    ) -> Opportunity:
        return opportunity_from_scan_item(
            item, strategy_name=strategy_name, index=index
        )

    @staticmethod
    def goal_summary_from_settings(goal_block: Any) -> Dict[str, Any]:
        return goal_summary_from_settings(goal_block)

    @staticmethod
    def validate_session(session: ScanSessionReport) -> Tuple[bool, str]:
        if not isinstance(session, ScanSessionReport):
            return False, "须为 ScanSessionReport"
        return session.validate()

    # ----- adapter -----

    @staticmethod
    def list_adapters() -> List[str]:
        return AdapterLoader.list_names()

    @staticmethod
    def validate_adapter(name: str) -> Tuple[bool, str]:
        return AdapterValidator.validate(name)

    @staticmethod
    def load_adapter_class(name: str) -> Optional[Type]:
        return AdapterLoader.load_class(name)

    # ----- post_processor -----

    @staticmethod
    def list_post_processors() -> List[str]:
        return PostProcessorLoader.list_keys()

    @staticmethod
    def validate_post_processor(key: str) -> Tuple[bool, str]:
        return PostProcessorValidator.validate(key)

    @staticmethod
    def load_post_processor(key: str) -> Optional[PostProcessorDefinition]:
        return PostProcessorLoader.load(key)

    @staticmethod
    def run_post_processor(key: str, session: ScanSessionReport) -> None:
        """校验会话后执行指定 PostProcessor。"""
        ok, err = PostProcess.validate_session(session)
        if not ok:
            raise ValueError(f"ScanSessionReport 无效: {err}")
        PostProcessorExecutor.run(key, session)


__all__ = ["PostProcess"]
