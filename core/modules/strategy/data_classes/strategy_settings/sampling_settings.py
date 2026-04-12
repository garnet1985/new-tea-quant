#!/usr/bin/env python3
"""
策略 ``sampling`` 配置块（对应 ``settings_example`` 第 4) 节）。

与 ``StockSamplingHelper.get_stock_list`` 使用的结构一致：
strategy / sampling_amount / 各策略子块（continuous、pool、blacklist 等）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet

from .settings_base import SettingsBase, ValidationReport

# 与 ``StockSamplingHelper.get_stock_list`` 分支一致
KNOWN_STRATEGIES: FrozenSet[str] = frozenset(
    {"uniform", "stratified", "random", "continuous", "pool", "blacklist"}
)

_STRATEGY_SUBKEYS = frozenset(
    {"uniform", "stratified", "random", "continuous", "pool", "blacklist"}
)


@dataclass
class StrategySamplingSettings(SettingsBase):
    """持有 ``settings["sampling"]`` 的同一 dict 引用。"""

    sampling: Dict[str, Any]

    @classmethod
    def from_strategy_root(cls, root: Dict[str, Any]) -> StrategySamplingSettings:
        """从完整策略 ``settings`` 挂载 ``sampling``；缺省或非 dict 时写入 ``{}``。"""
        if not isinstance(root, dict):
            root = {}
        block = root.get("sampling")
        if not isinstance(block, dict):
            block = {}
            root["sampling"] = block
        return cls(sampling=block)

    def apply_defaults(self) -> None:
        """与 ``settings_example`` 及整包默认逻辑中的 sampling 部分对齐。"""
        s = self.sampling
        if "strategy" not in s:
            s["strategy"] = "continuous"
        if "sampling_amount" not in s:
            s["sampling_amount"] = 10

    def validate(self) -> ValidationReport:
        """
        校验 sampling 结构与策略名；必要时给出 pool/blacklist 数据源提示。

        先 ``apply_defaults``，再检查 strategy、sampling_amount、子块类型。
        """
        result = SettingsBase.new_validation()
        self.apply_defaults()

        raw_strategy = self.sampling.get("strategy", "continuous")
        if isinstance(raw_strategy, str):
            strategy = raw_strategy.strip() or "continuous"
        else:
            strategy = ""
        if not strategy:
            SettingsBase.add_critical(
                result,
                "sampling.strategy",
                "sampling.strategy 必须为非空字符串",
                suggested_fix='设置 "strategy": "continuous" 等（见 settings_example）',
            )
        elif strategy not in KNOWN_STRATEGIES:
            SettingsBase.add_critical(
                result,
                "sampling.strategy",
                f"未知采样策略: {raw_strategy!r}",
                suggested_fix=f"使用其一: {', '.join(sorted(KNOWN_STRATEGIES))}",
            )
        else:
            self.sampling["strategy"] = strategy

        amount = self.sampling.get("sampling_amount", 10)
        try:
            n = int(amount)
            if n < 1:
                raise ValueError
        except (TypeError, ValueError):
            SettingsBase.add_critical(
                result,
                "sampling.sampling_amount",
                "sampling_amount 必须为正整数",
                suggested_fix='设置 "sampling_amount": 50 等正整数',
            )

        for key in _STRATEGY_SUBKEYS:
            sub = self.sampling.get(key)
            if sub is None:
                continue
            if not isinstance(sub, dict):
                SettingsBase.add_critical(
                    result,
                    f"sampling.{key}",
                    f"sampling.{key} 必须为对象（dict）",
                    suggested_fix="子配置请使用对象，例如 continuous: { start_idx: 0 }",
                )

        if result.is_valid and strategy in KNOWN_STRATEGIES:
            self._validate_strategy_specific(strategy, result)

        self._warn_extra_strategy_blocks(strategy, result)
        return result

    def _validate_strategy_specific(self, strategy: str, result: ValidationReport) -> None:
        if strategy == "pool":
            cfg = self.sampling.get("pool") or {}
            if not isinstance(cfg, dict):
                return
            ids = cfg.get("stock_ids") or []
            file_path = cfg.get("file")
            has_ids = isinstance(ids, list) and len(ids) > 0
            has_file = isinstance(file_path, str) and bool(file_path.strip())
            if not has_ids and not has_file:
                SettingsBase.add_critical(
                    result,
                    "sampling.pool",
                    "pool 采样需配置 stock_ids（非空列表）或 file（相对策略目录）",
                    suggested_fix='例如 "pool": {"stock_ids": ["000001.SZ"]} 或 "file": "stock_lists/pool.txt"',
                )

        if strategy == "blacklist":
            cfg = self.sampling.get("blacklist") or {}
            if not isinstance(cfg, dict):
                return
            ids = cfg.get("stock_ids") or []
            file_path = cfg.get("file")
            has_ids = isinstance(ids, list) and len(ids) > 0
            has_file = isinstance(file_path, str) and bool(file_path.strip())
            if not has_ids and not has_file:
                SettingsBase.add_critical(
                    result,
                    "sampling.blacklist",
                    "blacklist 采样需配置 stock_ids（非空列表）或 file（相对策略目录）",
                    suggested_fix='例如 "blacklist": {"stock_ids": ["000001.SZ"]} 或 "file": "stock_lists/bl.txt"',
                )

    def _warn_extra_strategy_blocks(self, active: str, result: ValidationReport) -> None:
        """若填了多种策略子块，与「只保留一种取样方式」的说明对齐，给出 Warning。"""
        if not active or active not in KNOWN_STRATEGIES:
            return
        filled = [
            k
            for k in _STRATEGY_SUBKEYS
            if k != active and isinstance(self.sampling.get(k), dict) and self.sampling.get(k)
        ]
        for k in filled:
            SettingsBase.add_warning(
                result,
                f"sampling.{k}",
                f"当前 strategy 为 {active!r}，但存在非空的 sampling.{k}；示例约定只保留一种取样子配置",
                suggested_fix=f"删除与 {active!r} 无关的子块，或改用对应的 strategy",
            )

    def to_dict(self) -> Dict[str, Any]:
        return self.deep_copy_dict(dict(self.sampling))

    def get_strategy(self) -> str:
        return str(self.sampling.get("strategy", "continuous") or "continuous")

    def get_sampling_amount(self) -> int:
        try:
            return max(int(self.sampling.get("sampling_amount", 10) or 10), 1)
        except (TypeError, ValueError):
            return 10

    def get_sub_config(self, key: str) -> Dict[str, Any]:
        sub = self.sampling.get(key)
        return sub if isinstance(sub, dict) else {}
