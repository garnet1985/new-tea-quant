"""模拟身份指纹：收集 input → settings_fp / env_fp / disk_settings_hash。

边界:
- 负责: 有效 settings 合并、三类指纹、FingerprintResult
- 不负责: GlobalEntityCache seed、磁盘 cache 读写、Pipeline 执行
  entity_ids 由主线（entity_loader）先 resolve 再传入
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

    settings_fp: str
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
        """收集 settings / 策略代码 / 环境 input，产出三类指纹。"""
        if strategy_info is None:
            raise ValueError("strategy_info 不能为空")

        disk_settings = dict(strategy_info.settings or {})
        effective_settings, settings_diff = FingerprintCalculator.merge_settings(
            strategy_info,
            runtime_settings,
        )
        ids = [str(x).strip() for x in (entity_ids or []) if str(x).strip()]
        coerced_diff = FingerprintCalculator.coerce_numeric_tree(settings_diff)
        settings_fp = FingerprintCalculator.to_effective_settings_fingerprint(
            effective_settings,
            ids,
        )
        disk_settings_hash = FingerprintCalculator.to_disk_settings_hash(disk_settings)
        env_fp = FingerprintCalculator.to_env_fingerprint(
            strategy_info,
            effective_settings,
            entity_ids=ids,
        )
        return FingerprintResult(
            settings_fp=settings_fp,
            env_fp=env_fp,
            disk_settings_hash=disk_settings_hash,
            settings_diff=coerced_diff,
            effective_settings=effective_settings,
            entity_ids=ids,
        )

    @staticmethod
    def to_effective_settings_fingerprint(
        effective_settings: StrategySettings,
        entity_ids: List[str],
    ) -> str:
        """settings 指纹：effective settings 指纹子集 + entity_ids。"""
        subset = StrategySettings.extract_effective_settings(effective_settings)
        signature = {
            "effective_settings": FingerprintCalculator.coerce_numeric_tree(subset),
            "entity_ids": sorted(entity_ids),
        }
        return FingerprintCalculator._to_fingerprint_hash(signature)

    @staticmethod
    def to_settings_semantic_fingerprint(
        effective_settings: StrategySettings,
        entity_ids: List[str],
    ) -> str:
        """兼容别名；请用 ``to_effective_settings_fingerprint``。"""
        return FingerprintCalculator.to_effective_settings_fingerprint(
            effective_settings, entity_ids
        )

    @staticmethod
    def to_settings_diff_fingerprint(
        settings_diff: Dict[str, Any],
        entity_ids: List[str],
    ) -> str:
        """settings 指纹：已 coerce 的 settings_diff + entity_ids。

        对 diff 做指纹与对「effective 的语义核」等价，前提是 effective = disk ⊕ diff，
        且 disk 另有 ``disk_settings_hash`` 防物理文件漂移。
        """
        signature = {
            "settings_diff": FingerprintCalculator.coerce_numeric_tree(settings_diff),
            "entity_ids": sorted(entity_ids),
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
        effective_settings: Union[StrategySettings, Dict[str, Any]],
        *,
        entity_ids: List[str],
        hooks_file_path: str = "",
    ) -> str:
        """env 指纹：策略代码 / 与 JobBuilder 一致的区间 / execution_mode / 引擎与 DB。"""
        if isinstance(effective_settings, StrategySettings):
            settings_obj = effective_settings
        else:
            settings_obj = StrategySettings.from_dict(dict(effective_settings or {}))

        period = settings_obj.resolve_period()
        start_date = period.start_date
        end_date = period.end_date

        hooks_class = getattr(strategy_info, "hooks_class", None)
        hooks_class_name = hooks_class.__name__ if hooks_class is not None else ""
        hooks_code_hash = FingerprintCalculator._hooks_code_hash(
            hooks_class, hooks_file_path, strategy_info
        )

        try:
            execution_mode = settings_obj.execution_mode
        except Exception:
            simulation = settings_obj.raw_settings.get("simulation") or {}
            execution = (
                simulation.get("execution")
                if isinstance(simulation, dict)
                else {}
            )
            execution_mode = str(
                (execution.get("mode") if isinstance(execution, dict) else "")
                or ""
            )

        signature = {
            "strategy_id": getattr(strategy_info, "unique_relative_path", "") or "",
            "entity_ids": sorted(entity_ids or []),
            "start_date": start_date,
            "end_date": end_date,
            "execution_mode": execution_mode,
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
