#!/usr/bin/env python3
"""
策略 ``goal`` 配置块（对应 ``settings_example`` 第 5) 节）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .settings_base import SettingsBase, ValidationReport


@dataclass
class StrategyGoalSettings(SettingsBase):
    goal: Dict[str, Any]
    strategy_name: str = "unknown"

    @classmethod
    def from_strategy_root(cls, root: Dict[str, Any]) -> "StrategyGoalSettings":
        if not isinstance(root, dict):
            root = {}
        block = root.get("goal")
        if not isinstance(block, dict):
            block = {}
            root["goal"] = block
        name = str(root.get("name", "unknown") or "unknown")
        return cls(goal=block, strategy_name=name)

    def apply_defaults(self) -> None:
        exp = self.goal.get("expiration")
        if isinstance(exp, dict):
            if "fixed_window_in_days" not in exp:
                exp["fixed_window_in_days"] = 30
            if "is_trading_days" not in exp:
                exp["is_trading_days"] = True

    def validate(self) -> ValidationReport:
        self.apply_defaults()
        return StrategyGoalSettings.validate_goal_dict(
            self.goal, self.strategy_name, "goal"
        )

    def to_dict(self) -> Dict[str, Any]:
        return self.deep_copy_dict(self.goal)

    @staticmethod
    def validate_goal_dict(
        goal_config: Dict[str, Any],
        strategy_name: str,
        field_path: str = "goal",
    ) -> ValidationReport:
        _ = strategy_name
        result = SettingsBase.new_validation()

        if goal_config.get("is_customized", False):
            return result

        if not goal_config:
            SettingsBase.add_critical(
                result,
                field_path,
                "goal 配置不能为空（枚举器需要 goal 配置来定义止盈止损规则）",
            )
            return result

        take_profit_result = StrategyGoalSettings._validate_take_profit(
            goal_config, strategy_name, f"{field_path}.take_profit"
        )
        result.errors.extend(take_profit_result.errors)
        result.warnings.extend(take_profit_result.warnings)
        if not take_profit_result.is_valid:
            result.is_valid = False

        stop_loss_result = StrategyGoalSettings._validate_stop_loss(
            goal_config, strategy_name, f"{field_path}.stop_loss"
        )
        result.errors.extend(stop_loss_result.errors)
        result.warnings.extend(stop_loss_result.warnings)
        if not stop_loss_result.is_valid:
            result.is_valid = False

        expiration_result = StrategyGoalSettings._validate_expiration(
            goal_config, strategy_name, f"{field_path}.expiration"
        )
        result.warnings.extend(expiration_result.warnings)

        if not goal_config.get("expiration"):
            ratio_result = StrategyGoalSettings._validate_ratio_sum(
                goal_config, strategy_name, field_path
            )
            result.errors.extend(ratio_result.errors)
            result.warnings.extend(ratio_result.warnings)
            if not ratio_result.is_valid:
                result.is_valid = False

        if not goal_config.get("take_profit") and not goal_config.get("stop_loss"):
            SettingsBase.add_warning(
                result,
                field_path,
                "goal 配置不完整：既没有 take_profit 也没有 stop_loss",
            )
        elif not goal_config.get("take_profit"):
            SettingsBase.add_warning(
                result,
                field_path,
                "goal 配置不完整：缺少 take_profit 配置",
            )
        elif not goal_config.get("stop_loss"):
            SettingsBase.add_warning(
                result,
                field_path,
                "goal 配置不完整：缺少 stop_loss 配置",
            )

        return result

    @staticmethod
    def _validate_take_profit(
        goal_config: Dict[str, Any],
        strategy_name: str,
        field_path: str,
    ) -> ValidationReport:
        _ = strategy_name
        result = SettingsBase.new_validation()
        take_profit = goal_config.get("take_profit")
        if not take_profit:
            return result
        if take_profit.get("is_customized", False):
            return result

        stages = take_profit.get("stages", [])
        if not isinstance(stages, list) or len(stages) == 0:
            SettingsBase.add_critical(result, field_path, "take_profit.stages 必须是非空列表")
            return result

        total_sell_ratio = 0.0
        for idx, stage in enumerate(stages):
            stage_path = f"{field_path}.stages[{idx}]"
            ratio = stage.get("ratio")
            if ratio is None:
                SettingsBase.add_critical(result, stage_path, "take_profit stage 必须包含 ratio 字段")
            elif not isinstance(ratio, (int, float)) or ratio <= 0:
                SettingsBase.add_critical(result, stage_path, "take_profit stage 的 ratio 必须是正数")

            sell_ratio = stage.get("sell_ratio", 0.0)
            close_invest = stage.get("close_invest", False)
            if not close_invest:
                if sell_ratio is None or sell_ratio <= 0:
                    SettingsBase.add_critical(result, stage_path, "take_profit stage 缺少 sell_ratio")
                else:
                    total_sell_ratio += float(sell_ratio)

        if total_sell_ratio > 1.0:
            SettingsBase.add_critical(
                result,
                field_path,
                f"take_profit 的 sell_ratio 总和 ({total_sell_ratio}) 超过 100%",
            )
        return result

    @staticmethod
    def _validate_stop_loss(
        goal_config: Dict[str, Any],
        strategy_name: str,
        field_path: str,
    ) -> ValidationReport:
        _ = strategy_name
        result = SettingsBase.new_validation()
        stop_loss = goal_config.get("stop_loss")
        if not stop_loss:
            return result
        if stop_loss.get("is_customized", False):
            return result

        stages = stop_loss.get("stages", [])
        if not isinstance(stages, list) or len(stages) == 0:
            SettingsBase.add_critical(result, field_path, "stop_loss.stages 必须是非空列表")
            return result

        for idx, stage in enumerate(stages):
            stage_path = f"{field_path}.stages[{idx}]"
            ratio = stage.get("ratio")
            if ratio is None:
                SettingsBase.add_critical(result, stage_path, "stop_loss stage 必须包含 ratio 字段")
            elif not isinstance(ratio, (int, float)) or ratio >= 0:
                SettingsBase.add_critical(result, stage_path, "stop_loss stage 的 ratio 必须是负数")
        return result

    @staticmethod
    def _validate_expiration(
        goal_config: Dict[str, Any],
        strategy_name: str,
        field_path: str,
    ) -> ValidationReport:
        _ = strategy_name
        result = SettingsBase.new_validation()
        expiration = goal_config.get("expiration")
        if not expiration:
            SettingsBase.add_warning(result, field_path, "goal 缺少 expiration")
            return result
        if "fixed_window_in_days" not in expiration:
            SettingsBase.add_warning(result, field_path, "expiration 缺少 fixed_window_in_days")
        return result

    @staticmethod
    def _validate_ratio_sum(
        goal_config: Dict[str, Any],
        strategy_name: str,
        field_path: str,
    ) -> ValidationReport:
        _ = strategy_name
        result = SettingsBase.new_validation()
        take_profit = goal_config.get("take_profit", {})
        if not take_profit or take_profit.get("is_customized", False):
            return result
        stages = take_profit.get("stages", [])
        if not stages:
            return result

        total_sell_ratio = 0.0
        has_close_invest = False
        for stage in stages:
            if stage.get("close_invest", False):
                has_close_invest = True
                break
            sell_ratio = stage.get("sell_ratio", 0.0)
            if sell_ratio:
                total_sell_ratio += float(sell_ratio)

        if not has_close_invest and total_sell_ratio > 1.0:
            SettingsBase.add_critical(
                result,
                field_path,
                f"无 expiration 且 sell_ratio 总和 ({total_sell_ratio}) > 1.0",
            )
        return result


__all__ = ["StrategyGoalSettings"]
