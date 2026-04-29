#!/usr/bin/env python3
"""
策略 ``goal`` 配置块（对应 ``settings_example`` 第 5) 节）。

止盈 / 止损 / 到期 / 保本 / 动态止损等规则校验集中在此；
枚举器等通过 ``validate_goal_dict`` 复用同一套逻辑。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .settings_base import SettingsBase, ValidationReport


@dataclass
class StrategyGoalSettings(SettingsBase):
    """持有 ``settings["goal"]`` 的同一 dict 引用；``strategy_name`` 用于校验上下文。"""

    goal: Dict[str, Any]
    strategy_name: str = "unknown"

    @classmethod
    def from_strategy_root(cls, root: Dict[str, Any]) -> StrategyGoalSettings:
        """从完整策略 ``settings`` 挂载 ``goal``；缺省或非 dict 时写入 ``{}``。"""
        if not isinstance(root, dict):
            root = {}
        block = root.get("goal")
        if not isinstance(block, dict):
            block = {}
            root["goal"] = block
        name = str(root.get("name", "unknown") or "unknown")
        return cls(goal=block, strategy_name=name)

    def apply_defaults(self) -> None:
        """与 ``settings_example`` 中常见默认对齐（仅补缺失键，不覆盖已有值）。"""
        exp = self.goal.get("expiration")
        if isinstance(exp, dict):
            if "fixed_window_in_days" not in exp:
                exp["fixed_window_in_days"] = 30
            if "is_trading_days" not in exp:
                exp["is_trading_days"] = True

    def validate(self) -> ValidationReport:
        """校验 goal；先 ``apply_defaults``，再跑完整规则。"""
        self.apply_defaults()
        return StrategyGoalSettings.validate_goal_dict(
            self.goal, self.strategy_name, "goal"
        )

    def to_dict(self) -> Dict[str, Any]:
        """权威 ``goal`` 块（深拷贝）。"""
        return self.deep_copy_dict(self.goal)

    # ------------------------------------------------------------------
    # 静态入口：供枚举器等在未包装为 dataclass 时直接校验 ``goal`` dict
    # ------------------------------------------------------------------

    @staticmethod
    def validate_goal_dict(
        goal_config: Dict[str, Any],
        strategy_name: str,
        field_path: str = "goal",
    ) -> ValidationReport:
        """
        验证 goal 配置（与枚举器等调用方使用的规则一致）。

        Args:
            goal_config: ``settings["goal"]`` 字典
            strategy_name: 策略名（用于日志/错误上下文）
            field_path: 错误路径前缀
        """
        _ = strategy_name
        result = SettingsBase.new_validation()

        if goal_config.get("is_customized", False):
            return result

        if not goal_config:
            SettingsBase.add_critical(
                result,
                field_path,
                "goal 配置不能为空（枚举器需要 goal 配置来定义止盈止损规则）",
                suggested_fix=(
                    '在 settings.py 中添加 goal 配置，例如：\n'
                    '  "goal": {\n'
                    '    "expiration": {"fixed_window_in_days": 30, "is_trading_days": True},\n'
                    '    "stop_loss": {"stages": [{"name": "loss10%", "ratio": -0.1, "close_invest": True}]},\n'
                    '    "take_profit": {"stages": [{"name": "win10%", "ratio": 0.1, "sell_ratio": 0.5}]}\n'
                    "  }"
                ),
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
                suggested_fix="建议至少配置 take_profit 或 stop_loss 之一",
            )
        elif not goal_config.get("take_profit"):
            SettingsBase.add_warning(
                result,
                field_path,
                "goal 配置不完整：缺少 take_profit 配置",
                suggested_fix="建议配置 take_profit 以实现止盈",
            )
        elif not goal_config.get("stop_loss"):
            SettingsBase.add_warning(
                result,
                field_path,
                "goal 配置不完整：缺少 stop_loss 配置",
                suggested_fix="建议配置 stop_loss 以实现止损",
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
            SettingsBase.add_critical(
                result,
                field_path,
                "take_profit.stages 必须是非空列表",
                suggested_fix=(
                    '在 settings.py 的 goal.take_profit 中添加 stages，例如：\n'
                    '  "take_profit": {\n'
                    '    "stages": [\n'
                    '      {"name": "win10%", "ratio": 0.1, "sell_ratio": 0.5}\n'
                    "    ]\n"
                    "  }"
                ),
            )
            return result

        total_sell_ratio = 0.0
        for idx, stage in enumerate(stages):
            stage_path = f"{field_path}.stages[{idx}]"

            ratio = stage.get("ratio")
            if ratio is None:
                SettingsBase.add_critical(
                    result,
                    stage_path,
                    "take_profit stage 必须包含 ratio 字段",
                    suggested_fix=f'在 {stage_path} 中添加 "ratio": 0.1（例如）',
                )
            elif not isinstance(ratio, (int, float)) or ratio <= 0:
                SettingsBase.add_critical(
                    result,
                    stage_path,
                    "take_profit stage 的 ratio 必须是正数",
                    suggested_fix=f'将 {stage_path}.ratio 设置为正数（例如 0.1 表示 10%）',
                )

            sell_ratio = stage.get("sell_ratio", 0.0)
            close_invest = stage.get("close_invest", False)

            if not close_invest:
                if sell_ratio is None or sell_ratio <= 0:
                    SettingsBase.add_critical(
                        result,
                        stage_path,
                        "take_profit stage 必须包含 sell_ratio（当 close_invest=False 时）",
                        suggested_fix=f'在 {stage_path} 中添加 "sell_ratio": 0.5（例如）',
                    )
                else:
                    total_sell_ratio += float(sell_ratio)

        if total_sell_ratio > 1.0:
            SettingsBase.add_critical(
                result,
                field_path,
                f"take_profit 的 sell_ratio 总和 ({total_sell_ratio}) 超过 100%",
                suggested_fix="调整 take_profit stages 的 sell_ratio，确保总和不超过 1.0",
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
            SettingsBase.add_critical(
                result,
                field_path,
                "stop_loss.stages 必须是非空列表",
                suggested_fix=(
                    '在 settings.py 的 goal.stop_loss 中添加 stages，例如：\n'
                    '  "stop_loss": {\n'
                    '    "stages": [\n'
                    '      {"name": "loss10%", "ratio": -0.1, "close_invest": True}\n'
                    "    ]\n"
                    "  }"
                ),
            )
            return result

        for idx, stage in enumerate(stages):
            stage_path = f"{field_path}.stages[{idx}]"

            ratio = stage.get("ratio")
            if ratio is None:
                SettingsBase.add_critical(
                    result,
                    stage_path,
                    "stop_loss stage 必须包含 ratio 字段",
                    suggested_fix=f'在 {stage_path} 中添加 "ratio": -0.1（例如）',
                )
            elif not isinstance(ratio, (int, float)) or ratio >= 0:
                SettingsBase.add_critical(
                    result,
                    stage_path,
                    "stop_loss stage 的 ratio 必须是负数",
                    suggested_fix=f'将 {stage_path}.ratio 设置为负数（例如 -0.1 表示 -10%）',
                )

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
            SettingsBase.add_warning(
                result,
                field_path,
                "goal 配置缺少 expiration（到期平仓），建议配置以避免无限持有",
                suggested_fix=(
                    '在 settings.py 的 goal 中添加 expiration，例如：\n'
                    '  "expiration": {"fixed_window_in_days": 30, "is_trading_days": True}'
                ),
            )
            return result

        if "fixed_window_in_days" not in expiration:
            SettingsBase.add_warning(
                result,
                field_path,
                "expiration 配置缺少 fixed_window_in_days",
                suggested_fix='在 expiration 中添加 "fixed_window_in_days": 30（例如）',
            )

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
                (
                    f"在没有 expiration 的情况下，take_profit 的 sell_ratio 总和 ({total_sell_ratio}) "
                    "超过 100%，交易将永远无法关闭"
                ),
                suggested_fix=(
                    "解决方案：\n"
                    "1. 添加 expiration 配置（推荐）\n"
                    "2. 调整 take_profit stages 的 sell_ratio，确保总和 <= 1.0\n"
                    "3. 在最后一个 stage 设置 close_invest: True"
                ),
            )

        return result
