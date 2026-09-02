"""模拟身份指纹：收集 input → execute_fp / env_fp / disk_settings_hash。

不负责 GlobalEntityCache seed、磁盘 cache、Pipeline。
entity_ids 由调用方（entity_loader）先 resolve 再传入。
"""
from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
)
from core.system import get_version


@dataclass(frozen=True)
class FingerprintResult:
    """一次模拟请求的身份指纹与有效 settings。

    不含运行时 cache：主线用 ``effective_settings`` 再 seed GlobalEntityCache。
    """

    execute_fp: str
    env_fp: str
    disk_settings_hash: str
    settings_diff: Dict[str, Any]
    effective_settings: StrategySettings
    entity_ids: List[str]


class FingerprintCalculator:
    """收集 identity 输入并产出指纹。"""

    @staticmethod
    def merge_settings(
        strategy_info: EnabledStrategyInfo,
        runtime_settings: Optional[Dict[str, Any]] = None,
    ) -> Tuple[StrategySettings, Dict[str, Any]]:
        """disk settings ⊕ runtime → effective settings + diff。"""
        if strategy_info is None:
            raise ValueError("strategy_info 不能为空")
        disk_settings = dict(strategy_info.settings or {})
        return StrategySettings.calculate_effective_settings(
            disk_settings=disk_settings,
            user_settings=runtime_settings or {},
        )

    @staticmethod
    def calculate_fingerprints(
        strategy_info: EnabledStrategyInfo,
        runtime_settings: Optional[Dict[str, Any]] = None,
        *,
        entity_ids: Optional[Sequence[str]] = None,
    ) -> FingerprintResult:
        """收集 settings / hooks / 环境，产出 execute_fp 与 env_fp。"""
        if strategy_info is None:
            raise ValueError("strategy_info 不能为空")

        disk_settings = dict(strategy_info.settings or {})
        effective_settings, settings_diff = FingerprintCalculator.merge_settings(
            strategy_info,
            runtime_settings,
        )
        ids = [str(x).strip() for x in (entity_ids or []) if str(x).strip()]
        coerced_diff = FingerprintCalculator.coerce_numeric_tree(settings_diff)
        execute_fp = FingerprintCalculator.to_execute_fingerprint(
            effective_settings,
            ids,
        )
        disk_settings_hash = FingerprintCalculator.to_disk_settings_hash(disk_settings)
        env_fp = FingerprintCalculator.to_env_fingerprint(strategy_info)
        return FingerprintResult(
            execute_fp=execute_fp,
            env_fp=env_fp,
            disk_settings_hash=disk_settings_hash,
            settings_diff=coerced_diff,
            effective_settings=effective_settings,
            entity_ids=ids,
        )

    @staticmethod
    def extract_execute_scope(
        *,
        entity_ids: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """``execute_fp.scope``：只放标的快照（区间已在 simulation 里）。"""
        ids = [str(x).strip() for x in (entity_ids or []) if str(x).strip()]
        return {"entity_ids": sorted(ids)}

    @staticmethod
    def extract_execute_payload(
        settings: Union[StrategySettings, Dict[str, Any], None],
        *,
        entity_ids: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """``execute_fp`` 哈希前的稳定载荷。"""
        return {
            "settings": StrategySettings.extract_execute_settings(settings),
            "scope": FingerprintCalculator.extract_execute_scope(entity_ids=entity_ids),
        }

    @staticmethod
    def to_execute_fingerprint(
        effective_settings: Union[StrategySettings, Dict[str, Any], None],
        entity_ids: Optional[Sequence[str]] = None,
    ) -> str:
        """对 extract_execute_payload 做哈希（settings 投影 ⊕ scope）。"""
        payload = FingerprintCalculator.extract_execute_payload(
            effective_settings,
            entity_ids=entity_ids,
        )
        signature = {
            "settings": FingerprintCalculator.coerce_numeric_tree(payload["settings"]),
            "scope": payload["scope"],
        }
        return FingerprintCalculator._to_fingerprint_hash(signature)

    @staticmethod
    def to_disk_settings_hash(disk_settings: Dict[str, Any]) -> str:
        """磁盘 settings 中影响结果的字段哈希（物理文件被改则缓存失效）。"""
        filtered = StrategySettings._filter_fingerprint_fields(
            dict(disk_settings or {})
        )
        return FingerprintCalculator._to_fingerprint_hash(
            FingerprintCalculator.coerce_numeric_tree(filtered)
        )

    @staticmethod
    def to_env_fingerprint(
        strategy_info: EnabledStrategyInfo,
        *,
        hooks_file_path: str = "",
    ) -> str:
        """不可逆环境：NTQ 版本、hooks 源码、DB / 合约映射。"""
        hooks_class = getattr(strategy_info, "hooks_class", None)
        hooks_class_name = hooks_class.__name__ if hooks_class is not None else ""
        hooks_code_hash = FingerprintCalculator._hooks_code_hash(
            hooks_class, hooks_file_path, strategy_info
        )

        signature = {
            "strategy_id": getattr(strategy_info, "unique_relative_path", "") or "",
            "engine_version": get_version(),
            "database_type": FingerprintCalculator._get_database_type(),
            "hooks_module_path": getattr(strategy_info, "hooks_module_path", "") or "",
            "hooks_class_name": hooks_class_name,
            "hooks_code_hash": hooks_code_hash,
            "data_contract_mapping_hash": (
                FingerprintCalculator._get_data_contract_mapping_hash()
            ),
        }
        return FingerprintCalculator._to_fingerprint_hash(signature)

    @staticmethod
    def coerce_numeric_tree(value: Any) -> Any:
        """指纹用：int/float 数值相等时统一为 float，避免 UI JSON 与 settings.py 漂移。"""
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return float(value)
        if isinstance(value, float):
            return float(value)
        if isinstance(value, dict):
            return {
                k: FingerprintCalculator.coerce_numeric_tree(v) for k, v in value.items()
            }
        if isinstance(value, list):
            return [FingerprintCalculator.coerce_numeric_tree(v) for v in value]
        return value

    @staticmethod
    def _hooks_code_hash(
        hooks_class: Any,
        hooks_file_path: str,
        strategy_info: EnabledStrategyInfo,
    ) -> str:
        if hooks_class is not None:
            try:
                src = inspect.getsourcefile(hooks_class)
                if src:
                    return FingerprintCalculator._hash_file(Path(src))
            except Exception:
                pass
        path = hooks_file_path or str(getattr(strategy_info, "strategy_file", "") or "")
        return FingerprintCalculator._hash_file(Path(path)) if path else ""

    @staticmethod
    def _to_fingerprint_hash(signature: Dict[str, Any]) -> str:
        canonical = json.dumps(
            signature,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_file(path: Path) -> str:
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
        try:
            cfg = ProjectContext.config.load_database_config()
            return str(cfg.get("database_type") or "").strip().lower()
        except Exception:
            return "unknown"

    @staticmethod
    def _get_data_contract_mapping_hash() -> str:
        core_mapping_hash = ""
        try:
            from core.modules.data_contract import ContractIssuer

            src = ContractIssuer.system_registry_source_path()
            if src is not None:
                core_mapping_hash = FingerprintCalculator._hash_file(Path(src))
        except Exception:
            core_mapping_hash = ""

        userspace_mapping_hash = ""
        try:
            userspace_mapping_file = ProjectContext.path.get_data_contract_mapping_path()
            if userspace_mapping_file.exists():
                userspace_mapping_hash = FingerprintCalculator._hash_file(
                    Path(userspace_mapping_file)
                )
        except Exception:
            userspace_mapping_hash = ""

        return FingerprintCalculator._to_fingerprint_hash(
            {
                "core_mapping_hash": core_mapping_hash,
                "userspace_mapping_hash": userspace_mapping_hash,
            }
        )


__all__ = ["FingerprintCalculator", "FingerprintResult"]
