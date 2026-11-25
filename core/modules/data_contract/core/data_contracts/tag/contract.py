"""Tag Contract - 继承时序基类，覆盖方法以支持 scenario。"""
from __future__ import annotations

from typing import Any, Dict, Optional

from core.modules.data_contract.core.base.base_time_series_contract import (
    BaseTimeSeriesContract,
)


class TagContract(BaseTimeSeriesContract):
    """Tag Contract - 支持动态 type/scope 和 scenario 参数。

    特殊性：
    1. type/scope 是动态的（取决于 scenario）
    2. fill_in_data 需要 scenario 参数
    3. loader 需要 scenario 才能加载
    4. 时间轴为 as_of_date，须走时序 until 才能被策略切片
    """

    def fill_in_data(
        self,
        runtime: Optional[Dict[str, Any]] = None,
        force_reload: bool = False,
    ) -> "TagContract":
        """加载 Tag 数据（需要 scenario 参数）。"""
        if runtime is None:
            runtime = {}

        scenario_name = runtime.get("scenario_name") or runtime.get("tag_scenario")
        scenario_id = runtime.get("scenario_id")

        if not scenario_name and not scenario_id:
            raise ValueError(
                "加载 Tag 失败：缺少 scenario 标识\n"
                "请在 runtime 中提供：\n"
                "  - scenario_name（推荐）或 tag_scenario\n"
                "  - 或 scenario_id"
            )

        if "type" in runtime or "scope" in runtime:
            raise ValueError(
                "Tag 的 type/scope 由 scenario 配置决定，不能在 runtime 中手动指定\n"
                "请在 runtime 中只提供 scenario_name/scenario_id"
            )

        scenario_info = self.get_scenario_info(scenario_name) if scenario_name else None
        # type/scope 写进 meta 侧语义，不塞进 runtime（避免再次触发上面的校验）
        if scenario_info:
            self.meta.type = scenario_info.get("type", "time_series")
            self.meta.scope = scenario_info.get("scope", "per_entity")
        else:
            self.meta.type = "time_series"
            self.meta.scope = "per_entity"

        super().fill_in_data(runtime=runtime, force_reload=force_reload)
        return self

    def validate_runtime(self, runtime: Dict[str, Any]) -> None:
        """验证 runtime 参数（Tag 需要额外的 scenario 参数）。"""
        super().validate_runtime(runtime)

        scenario_name = runtime.get("scenario_name") or runtime.get("tag_scenario")
        scenario_id = runtime.get("scenario_id")

        if not scenario_name and not scenario_id:
            raise ValueError("Tag runtime 缺少 scenario 标识（scenario_name/scenario_id）")

    def get_scenario_info(self, scenario_name: str) -> Optional[Dict[str, Any]]:
        """获取 scenario 配置信息（用于动态确定 type/scope）。"""
        _ = scenario_name
        return None


__all__ = ["TagContract"]
