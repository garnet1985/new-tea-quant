#!/usr/bin/env python3
"""指纹生成服务（统一管理 settings 和 env 指纹）。"""

from __future__ import annotations

import hashlib
import inspect
import importlib
import json
from pathlib import Path
from typing import Any, Dict, List, Union

from core.infra.project_context import ProjectContext
from core.system import get_version

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import StrategySettings


class Fingerprint:
    """指纹生成服务（统一管理 settings 和 env 指纹）。"""

    @staticmethod
    def to_settings_diff_fingerprint(settings_diff: Dict[str, Any]) -> str:
        """生成 settings 指纹（基于 settings_diff）。
        
        Args:
            settings_diff: Settings 差异字段（用户修改的 settings）
        
        Returns:
            SHA256 指签（32 字符）
        
        设计：
        - 只包含 settings_diff（用户修改的部分）
        - 不包含环境信息（entity_ids、start_date 等）
        """
        signature = {"settings_diff": settings_diff}
        return Fingerprint._to_fingerprint_hash(signature)

    @staticmethod
    def to_env_fingerprint(
        strategy_info: Any,  # EnabledStrategyInfo
        effective_settings: Union[StrategySettings, Dict[str, Any]],
        hooks_file_path: str = "",
    ) -> str:
        """生成 env 指纹（基于环境信息）。
        
        Args:
            strategy_info: EnabledStrategyInfo 对象（包含 strategy_file、hooks_class 等信息）
            effective_settings: StrategySettings 对象或 dict（包含完整 settings）
            hooks_file_path: Hooks 文件路径（可选，默认从 strategy_info 获取）
        
        Returns:
            SHA256 指签（32 字符）
        
        设计：
        - 内聚所有参数获取逻辑（不再分散在 pipeline）
        - 自动从 settings 获取 start_date、end_date、entity_ids
        - 自动从 strategy_info 获取 hooks 信息
        - 统一在一个方法里组装 signature
        
        流程：
        1. 从 settings 获取 simulation.start_date/end_date
        2. 从 settings 获取 sampling.use_sampling 和 entity_ids
        3. 从 strategy_info 获取 hooks 信息
        4. 计算 hooks_code_hash 和 data_contract_mapping_hash
        5. 组装 signature 并生成指纹
        """
        # 1. 从 settings 获取 simulation 参数
        if isinstance(effective_settings, StrategySettings):
            raw_settings = effective_settings.raw_settings
        else:
            raw_settings = dict(effective_settings or {})
        
        simulation = raw_settings.get("simulation", {})
        start_date = simulation.get("start_date", "")
        end_date = simulation.get("end_date", "")

        # 2. 从 settings 获取 entity_ids（区分采样开启/关闭）
        sampling = raw_settings.get("sampling", {})
        use_sampling = sampling.get("use_sampling", False)

        if use_sampling:
            # 采样开启：需要解析 sampling 配置（TODO: 实现完整逻辑）
            entity_ids = Fingerprint._resolve_entity_ids_with_sampling(sampling, strategy_info)
        else:
            # 采样关闭：从 metadata 获取全量 entity_ids
            entity_ids = Fingerprint._resolve_full_entity_ids(strategy_info)

        # 3. 从 strategy_info 获取 hooks 信息
        strategy_id = strategy_info.unique_relative_path
        hooks_module_path = strategy_info.hooks_module_path
        hooks_class_name = strategy_info.hooks_class.__name__
        
        # Hooks 文件路径（优先使用传入参数）
        if not hooks_file_path:
            hooks_file_path = str(strategy_info.strategy_file)
        
        # 4. 计算 hooks_code_hash
        hooks_code_hash = Fingerprint._hash_file(Path(hooks_file_path))

        # 5. 计算 data_contract_mapping_hash
        data_contract_mapping_hash = Fingerprint._get_data_contract_mapping_hash()

        # 6. 组装 signature
        signature = {
            "strategy_id": strategy_id,
            "entity_ids": sorted(entity_ids),
            "start_date": start_date,
            "end_date": end_date,
            "execution_mode": raw_settings.get("execution_mode", "entity_timeline"),
            "engine_version": get_version(),
            "database_type": Fingerprint._get_database_type(),
            "hooks_module_path": hooks_module_path,
            "hooks_class_name": hooks_class_name,
            "hooks_code_hash": hooks_code_hash,
            "data_contract_mapping_hash": data_contract_mapping_hash,
        }

        return Fingerprint._to_fingerprint_hash(signature)

    @staticmethod
    def _to_fingerprint_hash(signature: Dict[str, Any]) -> str:
        """统一的指纹哈希计算（底层方法）。
        
        Args:
            signature: 签名字典（包含所有需要哈希的字段）
        
        Returns:
            SHA256 指签（32 字符）
        
        设计：
        - 统一的哈希计算逻辑（避免重复代码）
        - 稳定的排序和序列化（确保相同输入产生相同输出）
        """
        canonical = json.dumps(
            signature,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _resolve_entity_ids_with_sampling(sampling: Dict[str, Any], strategy_info: Any) -> List[str]:
        """解析采样开启时的 entity_ids（TODO: 实现完整逻辑）。
        
        Args:
            sampling: Sampling 配置字典
            strategy_info: EnabledStrategyInfo 对象
        
        Returns:
            entity_ids 列表
        
        设计：
        - 根据 sampling.strategy 解析 entity_ids
        - 可能从文件读取（sampling.pool.file）
        - 可能从配置获取（sampling.pool.stock_ids）
        """
        # TODO: 实现完整的采样逻辑
        # 暂时返回空列表（需要从 sampling 配置解析）
        return []

    @staticmethod
    def _resolve_full_entity_ids(strategy_info: Any) -> List[str]:
        """解析采样关闭时的全量 entity_ids。
        
        Args:
            strategy_info: EnabledStrategyInfo 对象
        
        Returns:
            entity_ids 列表
        
        设计：
        - 从 0_metadata.json 获取（优先）
        - 从 0_scope_stock_ids.txt 获取（次选）
        - 从 0_stock_ref.json 获取（兜底）
        """
        # TODO: 实现完整的全量 entity_ids 解析逻辑
        # 暂时返回空列表（需要从 metadata 文件读取）
        return []

    @staticmethod
    def _hash_file(path: Path) -> str:
        """计算文件 SHA256 哈希。
        
        Args:
            path: 文件路径
        
        Returns:
            SHA256 哈希（32 字符），文件不存在时返回空字符串
        """
        if not path.exists() or not path.is_file():
            return ""
        hasher = hashlib.sha256()
        with path.open("rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def _get_database_type() -> str:
        """获取数据库类型（从 ProjectContext 获取）。"""
        try:
            cfg = ProjectContext.config.load_database_config()
            return str(cfg.get("database_type") or "").strip().lower()
        except Exception:
            return "unknown"

    @staticmethod
    def _get_data_contract_mapping_hash() -> str:
        """计算 data_contract mapping 哈希。
        
        Returns:
            SHA256 哈希（32 字符）
        
        设计：
        - 计算 core mapping 文件的哈希
        - 计算 userspace mapping 文件的哈希（如果存在）
        - 合并两个哈希值
        """
        core_mapping_hash = ""
        try:
            dc_mapping_module = importlib.import_module("core.modules.data_contract.core.registry.mapping")
            dc_mapping_file = inspect.getsourcefile(dc_mapping_module)
            if dc_mapping_file:
                core_mapping_hash = Fingerprint._hash_file(Path(dc_mapping_file))
        except Exception:
            core_mapping_hash = ""

        userspace_mapping_hash = ""
        try:
            userspace_mapping_file = ProjectContext.path.get_data_contract_mapping_path()
            if userspace_mapping_file.exists():
                userspace_mapping_hash = Fingerprint._hash_file(Path(userspace_mapping_file))
        except Exception:
            userspace_mapping_hash = ""

        # 合并两个哈希（如果都存在）
        payload = {
            "core_mapping_hash": core_mapping_hash,
            "userspace_mapping_hash": userspace_mapping_hash,
        }
        return Fingerprint._to_fingerprint_hash(payload)


__all__ = ["Fingerprint"]