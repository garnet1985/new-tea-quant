"""指纹生成器。"""
from __future__ import annotations

import hashlib
import importlib
import inspect
import json
from pathlib import Path
from typing import Any, Dict, List

from core.infra.project_context import ProjectContext
from core.system import get_version


class Fingerprint:
    """指纹生成器。"""

    @staticmethod
    def to_settings_fingerprint(settings_diff: Dict[str, Any]) -> str:
        """生成settings指纹（基于settings_diff）。

        Args:
            settings_diff: 设置差异（影响回测结果）

        Returns:
            settings_fp（SHA256 hash）
        """
        signature = {
            "settings_diff": settings_diff,
        }
        return Fingerprint._to_fingerprint_hash(signature)

    @staticmethod
    def to_env_fingerprint(
        strategy_id: str,
        entity_ids: List[str],
        start_date: str,
        end_date: str,
        execution_mode: str,
        hooks_module_path: str,
        hooks_class_name: str,
        hooks_file_path: str = "",
        **kwargs: Any,
    ) -> str:
        """生成env指纹（基于环境信息）。

        Args:
            strategy_id: 策略ID（相对路径）
            entity_ids: entity列表
            start_date: 开始日期
            end_date: 结束日期
            execution_mode: 执行模式
            hooks_module_path: hooks模块路径
            hooks_class_name: hooks类名
            hooks_file_path: hooks源文件路径（用于计算code_hash）
            **kwargs: 其他环境因子

        Returns:
            env_fp（SHA256 hash）
        """
        signature = {
            "strategy_id": strategy_id,
            "entity_ids": sorted(entity_ids),
            "start_date": start_date,
            "end_date": end_date,
            "execution_mode": execution_mode,
            "hooks_module_path": hooks_module_path,
            "hooks_class_name": hooks_class_name,
        }

        # 添加系统版本
        signature["engine_version"] = get_version()

        # 添加数据库类型
        signature["database_type"] = Fingerprint._get_database_type()

        # 添加hooks代码hash
        if hooks_file_path:
            signature["hooks_code_hash"] = Fingerprint._hash_file(Path(hooks_file_path))
        else:
            signature["hooks_code_hash"] = ""

        # 添加data_contract mapping hash
        signature["data_contract_mapping_hash"] = Fingerprint._get_data_contract_mapping_hash()

        # 添加其他环境因子
        for key, value in kwargs.items():
            if value is not None:
                signature[key] = value

        return Fingerprint._to_fingerprint_hash(signature)

    @staticmethod
    def _to_fingerprint_hash(payload: Dict[str, Any]) -> str:
        """生成指纹hash（SHA256）。

        Args:
            payload: 指纹签名数据

        Returns:
            SHA256 hash字符串
        """
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_file(path: Path) -> str:
        """计算文件的SHA256 hash。

        Args:
            path: 文件路径

        Returns:
            SHA256 hash字符串
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
        """获取数据库类型（mysql / duckdb等）。"""
        cfg = ProjectContext.config.load_database_config()
        return str(cfg.get("database_type") or "").strip().lower()

    @staticmethod
    def _get_data_contract_mapping_hash() -> str:
        """获取data_contract mapping的hash。

        包含core和userspace的mapping源文件hash。
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
        userspace_mapping_file = ProjectContext.path.get_data_contract_mapping_path()
        if userspace_mapping_file.exists():
            userspace_mapping_hash = Fingerprint._hash_file(Path(userspace_mapping_file))

        payload = {
            "core_mapping_hash": core_mapping_hash,
            "userspace_mapping_hash": userspace_mapping_hash,
        }
        return Fingerprint._to_fingerprint_hash(payload)


__all__ = ["Fingerprint"]