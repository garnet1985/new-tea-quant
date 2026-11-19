"""PostProcess 门面 — 协议规范化、Adapter / PostProcessor 发现与执行。"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Type

from core.modules.post_process.core.adapter_loader import AdapterLoader
from core.modules.post_process.core.adapter_readiness import (
    check_adapter_readiness as readiness_check,
)
from core.modules.post_process.core.adapter_validator import AdapterValidator
from core.modules.post_process.core.catalog_summary import (
    list_adapter_summaries,
    list_post_processor_summaries,
    summarize_adapter,
    summarize_post_processor,
)
from core.modules.post_process.core.post_processor_executor import PostProcessorExecutor
from core.modules.post_process.core.post_processor_loader import PostProcessorLoader
from core.modules.post_process.core.post_processor_types import PostProcessorDefinition
from core.modules.post_process.core.post_processor_validator import PostProcessorValidator
from core.modules.post_process.core.post_processor_writer import (
    set_enabled as write_set_enabled,
    update_adapters as write_update_adapters,
)
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

    @staticmethod
    def summarize_adapter(name: str) -> Optional[Dict[str, Any]]:
        """Adapter 目录摘要（校验、readiness、status）；不含 secrets。"""
        return summarize_adapter(name)

    @staticmethod
    def list_adapter_summaries() -> List[Dict[str, Any]]:
        """全部 Adapter 目录摘要。"""
        return list_adapter_summaries()

    @staticmethod
    def check_adapter_readiness(
        name: str,
        *,
        config: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """合并 settings 后做静态就绪检查，并给出 status（live/dry_run/unavailable）。"""
        return readiness_check(name, config_override=config)

    # ----- post_processor -----

    @staticmethod
    def list_post_processors() -> List[str]:
        return PostProcessorLoader.list_keys()

    @staticmethod
    def list_enabled_post_processors() -> List[str]:
        """全局启用的 PostProcessor key（``is_enabled: true``）。"""
        return PostProcessorLoader.list_enabled_keys()

    @staticmethod
    def validate_post_processor(key: str) -> Tuple[bool, str]:
        return PostProcessorValidator.validate(key)

    @staticmethod
    def load_post_processor(key: str) -> Optional[PostProcessorDefinition]:
        return PostProcessorLoader.load(key)

    @staticmethod
    def summarize_post_processor(key: str) -> Optional[Dict[str, Any]]:
        """PostProcessor 摘要（adapters、拓扑序、校验、dry_run 汇总）。"""
        return summarize_post_processor(key)

    @staticmethod
    def list_post_processor_summaries() -> List[Dict[str, Any]]:
        """全部 PostProcessor 摘要。"""
        return list_post_processor_summaries()

    @staticmethod
    def set_enabled(key: str, enabled: bool) -> PostProcessorDefinition:
        """写入 YAML ``is_enabled``。"""
        return write_set_enabled(key, enabled)

    @staticmethod
    def update_post_processor_adapters(
        key: str,
        adapters: Mapping[str, Any],
    ) -> Tuple[PostProcessorDefinition, List[str]]:
        """写回方案内 adapters 与 depends_on；返回定义与拓扑序。"""
        return write_update_adapters(key, adapters)

    @staticmethod
    def run_post_processor(key: str, session: ScanSessionReport) -> Dict[str, Any]:
        """校验会话后执行指定 PostProcessor（忽略 is_enabled，供显式调用）。

        返回该方案内各 adapter 的 ``run`` 输出（name → return）。
        """
        ok, err = PostProcess.validate_session(session)
        if not ok:
            raise ValueError(f"ScanSessionReport 无效: {err}")
        return PostProcessorExecutor.run(key, session)

    @staticmethod
    def is_run_enabled() -> bool:
        """工作区是否允许跑扫描后处理（默认 True；关闭需 prefs 声明）。"""
        from core.modules.post_process.core.run_prefs import RunPrefs

        return RunPrefs.is_enabled()

    @staticmethod
    def set_run_enabled(enabled: bool) -> bool:
        """持久化工作区「是否跑扫描后处理」；开启=去掉声明。"""
        from core.modules.post_process.core.run_prefs import RunPrefs

        return RunPrefs.set_enabled(bool(enabled))

    @staticmethod
    def run_enabled_post_processors(session: ScanSessionReport) -> Dict[str, Any]:
        """扫描结束后对所有 ``is_enabled`` 的 PostProcessor 各跑一遍。

        若工作区 prefs 关闭后处理，直接跳过（CLI / UI / Pipeline 共用）。

        返回::

            {
              "ran": [<post_processor key>, ...],
              "ui": { ... },
              "skipped": bool,
            }
        """
        from core.modules.post_process.core.post_processor_executor import (
            ui_contributions_from_outputs,
        )

        ok, err = PostProcess.validate_session(session)
        if not ok:
            raise ValueError(f"ScanSessionReport 无效: {err}")
        if not PostProcess.is_run_enabled():
            return {"ran": [], "ui": {}, "skipped": True}
        keys = PostProcess.list_enabled_post_processors()
        ui: Dict[str, Any] = {}
        for key in keys:
            outputs = PostProcessorExecutor.run(key, session) or {}
            # 后写覆盖：多方案都含 presenter 时保留最后一次
            ui.update(ui_contributions_from_outputs(outputs))
        return {"ran": list(keys), "ui": ui, "skipped": False}

    # ------------------------------------------------------------------
    # Userspace 用例（脚手架 / 写文件 / 校验；发现即注册）
    # ------------------------------------------------------------------

    @staticmethod
    def scaffold_user_adapter(
        *,
        name: str,
        display_name: str = "",
    ) -> Dict[str, Any]:
        """在 ``userspace/.../adapters`` 从模板新建 Adapter 骨架。"""
        from core.modules.post_process.core.user_post_process import UserPostProcessOps

        return UserPostProcessOps.scaffold_adapter(
            name=name, display_name=display_name
        )

    @staticmethod
    def write_user_adapter_files(
        *,
        name: str,
        adapter_py: str = "",
        settings_py: str = "",
    ) -> Dict[str, Any]:
        """覆盖已有 Adapter 的 adapter.py / settings.py。"""
        from core.modules.post_process.core.user_post_process import UserPostProcessOps

        return UserPostProcessOps.write_adapter_files(
            name=name, adapter_py=adapter_py, settings_py=settings_py
        )

    @staticmethod
    def validate_user_adapter(*, name: str) -> Dict[str, Any]:
        """校验 userspace Adapter（结构 + 可加载）。"""
        from core.modules.post_process.core.user_post_process import UserPostProcessOps

        return UserPostProcessOps.validate_adapter(name=name)

    @staticmethod
    def scaffold_user_post_processor(
        *,
        key: str,
        name: str = "",
        adapter_name: str = "",
        is_enabled: bool = False,
    ) -> Dict[str, Any]:
        """在 ``userspace/.../post_processors`` 新建 YAML 骨架。"""
        from core.modules.post_process.core.user_post_process import UserPostProcessOps

        return UserPostProcessOps.scaffold_post_processor(
            key=key,
            name=name,
            adapter_name=adapter_name,
            is_enabled=is_enabled,
        )

    @staticmethod
    def write_user_post_processor_yaml(
        *,
        key: str,
        yaml_body: str = "",
    ) -> Dict[str, Any]:
        """覆盖 PostProcessor YAML（key 强制对齐目录）。"""
        from core.modules.post_process.core.user_post_process import UserPostProcessOps

        return UserPostProcessOps.write_post_processor_yaml(
            key=key, yaml_body=yaml_body
        )

    @staticmethod
    def validate_user_post_processor(*, key: str) -> Dict[str, Any]:
        """校验 PostProcessor 声明与所引用 Adapter。"""
        from core.modules.post_process.core.user_post_process import UserPostProcessOps

        return UserPostProcessOps.validate_post_processor(key=key)

    @staticmethod
    def describe_user_adapter(*, name: str) -> Dict[str, Any]:
        from core.modules.post_process.core.user_post_process import UserPostProcessOps

        return UserPostProcessOps.describe_adapter(name=name)

    @staticmethod
    def describe_user_post_processor(*, key: str) -> Dict[str, Any]:
        from core.modules.post_process.core.user_post_process import UserPostProcessOps

        return UserPostProcessOps.describe_post_processor(key=key)

    @staticmethod
    def list_user_adapter_summaries() -> Dict[str, Any]:
        from core.modules.post_process.core.user_post_process import UserPostProcessOps

        return UserPostProcessOps.list_adapter_summaries()

    @staticmethod
    def list_user_post_processor_summaries() -> Dict[str, Any]:
        from core.modules.post_process.core.user_post_process import UserPostProcessOps

        return UserPostProcessOps.list_post_processor_summaries()


__all__ = ["PostProcess"]
