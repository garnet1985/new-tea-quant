"""Tag Contract - 继承 BaseDataKey，覆盖方法以支持 scenario。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.modules.data_contract.core.data_class.base_contract import BaseDataKey, ContractRuntime


class TagContract(BaseDataKey):
    """Tag Contract - 支持动态 type/scope 和 scenario 参数。

    特殊性：
    1. type/scope 是动态的（取决于 scenario）
    2. fill_in_data 需要 scenario 参数
    3. loader 需要 scenario 才能加载
    """

    def fill_in_data(self, runtime: Optional[Dict[str, Any]] = None) -> 'TagContract':
        """加载 Tag 数据（需要 scenario 参数）。

        Args:
            runtime: 运行时参数，必须包含：
                - entity_ids（实体列表）
                - scenario_name 或 scenario_id（scenario 标识）
                - start_time, end_time（可选）

        Returns:
            TagContract: self（支持链式调用）

        Raises:
            ValueError: 如果缺少 scenario 参数
        """
        # 验证 scenario 参数
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

        # 动态确定 type/scope（从 scenario 配置中读取）
        # 不能随便给默认值，必须从 scenario 中获取
        scenario_name = runtime.get("scenario_name") or runtime.get("tag_scenario")
        scenario_id = runtime.get("scenario_id")

        # TODO: 从数据库或配置文件中读取 scenario 配置
        # 这里暂时报错，提示用户 type/scope 由 scenario 决定
        if "type" in runtime or "scope" in runtime:
            raise ValueError(
                "Tag 的 type/scope 由 scenario 配置决定，不能在 runtime 中手动指定\n"
                "请在 runtime 中只提供 scenario_name/scenario_id"
            )

        # 从 scenario 配置中获取 type/scope（待实现）
        scenario_info = self.get_scenario_info(scenario_name) if scenario_name else None
        if scenario_info:
            runtime["type"] = scenario_info.get("type", "time_series")
            runtime["scope"] = scenario_info.get("scope", "per_entity")
        else:
            # 如果没有 scenario_info，暂时使用默认值（待完善）
            runtime["type"] = "time_series"
            runtime["scope"] = "per_entity"
        return super().fill_in_data(runtime=runtime)

    def validate_runtime(self, runtime: Dict[str, Any]) -> None:
        """验证 runtime 参数（Tag 需要额外的 scenario 参数）。

        Args:
            runtime: 运行时参数

        Raises:
            ValueError: 如果缺少必要参数
        """
        # 先调用基类验证
        super().validate_runtime(runtime)

        # 验证 scenario 参数
        scenario_name = runtime.get("scenario_name") or runtime.get("tag_scenario")
        scenario_id = runtime.get("scenario_id")

        if not scenario_name and not scenario_id:
            raise ValueError("Tag runtime 缺少 scenario 标识（scenario_name/scenario_id）")

    def get_scenario_info(self, scenario_name: str) -> Optional[Dict[str, Any]]:
        """获取 scenario 配置信息（用于动态确定 type/scope）。

        Args:
            scenario_name: scenario 名称

        Returns:
            Optional[Dict[str, Any]]: scenario 配置（包含 type, scope 等），如果不存在返回 None
        """
        # TODO: 从数据库或配置文件中读取 scenario 信息
        # 这里暂时返回 None（需要实现）
        # 示例返回值：
        # {
        #     "name": "技术指标",
        #     "type": "time_series",  # 或 "non_time_series"
        #     "scope": "per_entity",  # 或 "global"
        # }
        return None


__all__ = ['TagContract']