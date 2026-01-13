#!/usr/bin/env python3
"""
Goal 配置验证器

职责：
- 验证 goal 配置的完整性和正确性
- 支持 customized 标记跳过验证
- 验证 ratio 总和不超过 100%（没有 expiration 的情况下）
"""

from typing import Dict, Any, List
from .setting_errors import SettingError, SettingErrorLevel, SettingValidationResult


class GoalValidator:
    """Goal 配置验证器"""
    
    @staticmethod
    def validate_goal_config(
        goal_config: Dict[str, Any],
        strategy_name: str,
        field_path: str = "goal"
    ) -> SettingValidationResult:
        """
        验证 goal 配置
        
        Args:
            goal_config: goal 配置字典
            strategy_name: 策略名称（用于错误信息）
            field_path: 字段路径（用于错误信息）
        
        Returns:
            SettingValidationResult: 验证结果
        """
        result = SettingValidationResult(is_valid=True)
        
        # 检查是否标记为 customized（顶层）
        if goal_config.get("is_customized", False):
            # 跳过所有验证
            return result
        
        # 检查 goal 是否为空
        if not goal_config:
            result.errors.append(SettingError(
                level=SettingErrorLevel.CRITICAL,
                field_path=field_path,
                message="goal 配置不能为空（枚举器需要 goal 配置来定义止盈止损规则）",
                suggested_fix=(
                    '在 settings.py 中添加 goal 配置，例如：\n'
                    '  "goal": {\n'
                    '    "expiration": {"fixed_window_in_days": 30, "is_trading_days": True},\n'
                    '    "stop_loss": {"stages": [{"name": "loss10%", "ratio": -0.1, "close_invest": True}]},\n'
                    '    "take_profit": {"stages": [{"name": "win10%", "ratio": 0.1, "sell_ratio": 0.5}]}\n'
                    '  }'
                )
            ))
            result.is_valid = False
            return result
        
        # 验证 take_profit
        take_profit_result = GoalValidator._validate_take_profit(
            goal_config, strategy_name, f"{field_path}.take_profit"
        )
        result.errors.extend(take_profit_result.errors)
        result.warnings.extend(take_profit_result.warnings)
        if not take_profit_result.is_valid:
            result.is_valid = False
        
        # 验证 stop_loss
        stop_loss_result = GoalValidator._validate_stop_loss(
            goal_config, strategy_name, f"{field_path}.stop_loss"
        )
        result.errors.extend(stop_loss_result.errors)
        result.warnings.extend(stop_loss_result.warnings)
        if not stop_loss_result.is_valid:
            result.is_valid = False
        
        # 验证 expiration（可选）
        expiration_result = GoalValidator._validate_expiration(
            goal_config, strategy_name, f"{field_path}.expiration"
        )
        result.warnings.extend(expiration_result.warnings)
        
        # 验证 ratio 总和（如果没有 expiration）
        if not goal_config.get("expiration"):
            ratio_result = GoalValidator._validate_ratio_sum(
                goal_config, strategy_name, field_path
            )
            result.errors.extend(ratio_result.errors)
            result.warnings.extend(ratio_result.warnings)
            if not ratio_result.is_valid:
                result.is_valid = False
        
        # 检查配置完整性（Warning）
        if not goal_config.get("take_profit") and not goal_config.get("stop_loss"):
            result.warnings.append(SettingError(
                level=SettingErrorLevel.WARNING,
                field_path=field_path,
                message="goal 配置不完整：既没有 take_profit 也没有 stop_loss",
                suggested_fix="建议至少配置 take_profit 或 stop_loss 之一"
            ))
        elif not goal_config.get("take_profit"):
            result.warnings.append(SettingError(
                level=SettingErrorLevel.WARNING,
                field_path=field_path,
                message="goal 配置不完整：缺少 take_profit 配置",
                suggested_fix="建议配置 take_profit 以实现止盈"
            ))
        elif not goal_config.get("stop_loss"):
            result.warnings.append(SettingError(
                level=SettingErrorLevel.WARNING,
                field_path=field_path,
                message="goal 配置不完整：缺少 stop_loss 配置",
                suggested_fix="建议配置 stop_loss 以实现止损"
            ))
        
        return result
    
    @staticmethod
    def _validate_take_profit(
        goal_config: Dict[str, Any],
        strategy_name: str,
        field_path: str
    ) -> SettingValidationResult:
        """验证 take_profit 配置"""
        result = SettingValidationResult(is_valid=True)
        
        take_profit = goal_config.get("take_profit")
        if not take_profit:
            return result  # take_profit 是可选的
        
        # 检查是否标记为 customized
        if take_profit.get("is_customized", False):
            return result  # 跳过验证
        
        # 验证 stages
        stages = take_profit.get("stages", [])
        if not isinstance(stages, list) or len(stages) == 0:
            result.errors.append(SettingError(
                level=SettingErrorLevel.CRITICAL,
                field_path=field_path,
                message="take_profit.stages 必须是非空列表",
                suggested_fix=(
                    '在 settings.py 的 goal.take_profit 中添加 stages，例如：\n'
                    '  "take_profit": {\n'
                    '    "stages": [\n'
                    '      {"name": "win10%", "ratio": 0.1, "sell_ratio": 0.5}\n'
                    '    ]\n'
                    '  }'
                )
            ))
            result.is_valid = False
            return result
        
        # 验证每个 stage
        total_sell_ratio = 0.0
        for idx, stage in enumerate(stages):
            stage_path = f"{field_path}.stages[{idx}]"
            
            # 验证 ratio
            ratio = stage.get("ratio")
            if ratio is None:
                result.errors.append(SettingError(
                    level=SettingErrorLevel.CRITICAL,
                    field_path=stage_path,
                    message="take_profit stage 必须包含 ratio 字段",
                    suggested_fix=f'在 {stage_path} 中添加 "ratio": 0.1（例如）'
                ))
                result.is_valid = False
            elif not isinstance(ratio, (int, float)) or ratio <= 0:
                result.errors.append(SettingError(
                    level=SettingErrorLevel.CRITICAL,
                    field_path=stage_path,
                    message="take_profit stage 的 ratio 必须是正数",
                    suggested_fix=f'将 {stage_path}.ratio 设置为正数（例如 0.1 表示 10%）'
                ))
                result.is_valid = False
            
            # 验证 sell_ratio 或 close_invest
            sell_ratio = stage.get("sell_ratio", 0.0)
            close_invest = stage.get("close_invest", False)
            
            if not close_invest:
                if sell_ratio is None or sell_ratio <= 0:
                    result.errors.append(SettingError(
                        level=SettingErrorLevel.CRITICAL,
                        field_path=stage_path,
                        message="take_profit stage 必须包含 sell_ratio（当 close_invest=False 时）",
                        suggested_fix=f'在 {stage_path} 中添加 "sell_ratio": 0.5（例如）'
                    ))
                    result.is_valid = False
                else:
                    total_sell_ratio += sell_ratio
        
        # 验证 sell_ratio 总和不超过 1.0
        if total_sell_ratio > 1.0:
            result.errors.append(SettingError(
                level=SettingErrorLevel.CRITICAL,
                field_path=field_path,
                message=f"take_profit 的 sell_ratio 总和 ({total_sell_ratio}) 超过 100%",
                suggested_fix="调整 take_profit stages 的 sell_ratio，确保总和不超过 1.0"
            ))
            result.is_valid = False
        
        return result
    
    @staticmethod
    def _validate_stop_loss(
        goal_config: Dict[str, Any],
        strategy_name: str,
        field_path: str
    ) -> SettingValidationResult:
        """验证 stop_loss 配置"""
        result = SettingValidationResult(is_valid=True)
        
        stop_loss = goal_config.get("stop_loss")
        if not stop_loss:
            return result  # stop_loss 是可选的
        
        # 检查是否标记为 customized
        if stop_loss.get("is_customized", False):
            return result  # 跳过验证
        
        # 验证 stages
        stages = stop_loss.get("stages", [])
        if not isinstance(stages, list) or len(stages) == 0:
            result.errors.append(SettingError(
                level=SettingErrorLevel.CRITICAL,
                field_path=field_path,
                message="stop_loss.stages 必须是非空列表",
                suggested_fix=(
                    '在 settings.py 的 goal.stop_loss 中添加 stages，例如：\n'
                    '  "stop_loss": {\n'
                    '    "stages": [\n'
                    '      {"name": "loss10%", "ratio": -0.1, "close_invest": True}\n'
                    '    ]\n'
                    '  }'
                )
            ))
            result.is_valid = False
            return result
        
        # 验证每个 stage
        for idx, stage in enumerate(stages):
            stage_path = f"{field_path}.stages[{idx}]"
            
            # 验证 ratio
            ratio = stage.get("ratio")
            if ratio is None:
                result.errors.append(SettingError(
                    level=SettingErrorLevel.CRITICAL,
                    field_path=stage_path,
                    message="stop_loss stage 必须包含 ratio 字段",
                    suggested_fix=f'在 {stage_path} 中添加 "ratio": -0.1（例如）'
                ))
                result.is_valid = False
            elif not isinstance(ratio, (int, float)) or ratio >= 0:
                result.errors.append(SettingError(
                    level=SettingErrorLevel.CRITICAL,
                    field_path=stage_path,
                    message="stop_loss stage 的 ratio 必须是负数",
                    suggested_fix=f'将 {stage_path}.ratio 设置为负数（例如 -0.1 表示 -10%）'
                ))
                result.is_valid = False
        
        return result
    
    @staticmethod
    def _validate_expiration(
        goal_config: Dict[str, Any],
        strategy_name: str,
        field_path: str
    ) -> SettingValidationResult:
        """验证 expiration 配置（可选）"""
        result = SettingValidationResult(is_valid=True)
        
        expiration = goal_config.get("expiration")
        if not expiration:
            # expiration 是可选的，但建议配置
            result.warnings.append(SettingError(
                level=SettingErrorLevel.WARNING,
                field_path=field_path,
                message="goal 配置缺少 expiration（到期平仓），建议配置以避免无限持有",
                suggested_fix=(
                    '在 settings.py 的 goal 中添加 expiration，例如：\n'
                    '  "expiration": {"fixed_window_in_days": 30, "is_trading_days": True}'
                )
            ))
            return result
        
        # 验证 fixed_window_in_days 或 fixed_period
        if "fixed_window_in_days" not in expiration and "fixed_period" not in expiration:
            result.warnings.append(SettingError(
                level=SettingErrorLevel.WARNING,
                field_path=field_path,
                message="expiration 配置缺少 fixed_window_in_days 或 fixed_period",
                suggested_fix='在 expiration 中添加 "fixed_window_in_days": 30（例如）'
            ))
        
        return result
    
    @staticmethod
    def _validate_ratio_sum(
        goal_config: Dict[str, Any],
        strategy_name: str,
        field_path: str
    ) -> SettingValidationResult:
        """
        验证 ratio 总和不超过 100%（没有 expiration 的情况下）
        
        如果没有 expiration，所有 take_profit 的 sell_ratio 总和必须 <= 1.0
        """
        result = SettingValidationResult(is_valid=True)
        
        take_profit = goal_config.get("take_profit", {})
        if not take_profit or take_profit.get("is_customized", False):
            return result  # 如果 customized，跳过验证
        
        stages = take_profit.get("stages", [])
        if not stages:
            return result
        
        total_sell_ratio = 0.0
        has_close_invest = False
        
        for stage in stages:
            # 如果这个 stage 有 close_invest，标记并停止累加
            if stage.get("close_invest", False):
                has_close_invest = True
                # 注意：即使有 close_invest，也要检查之前的 sell_ratio 总和
                # 如果之前的 sell_ratio 总和已经超过 1.0，仍然报错
                break
            
            # 累加 sell_ratio（在遇到 close_invest 之前）
            sell_ratio = stage.get("sell_ratio", 0.0)
            if sell_ratio:
                total_sell_ratio += sell_ratio
        
        # 如果没有 close_invest 且总和超过 1.0，报错
        if not has_close_invest and total_sell_ratio > 1.0:
            result.errors.append(SettingError(
                level=SettingErrorLevel.CRITICAL,
                field_path=field_path,
                message=(
                    f"在没有 expiration 的情况下，take_profit 的 sell_ratio 总和 ({total_sell_ratio}) "
                    f"超过 100%，交易将永远无法关闭"
                ),
                suggested_fix=(
                    "解决方案：\n"
                    "1. 添加 expiration 配置（推荐）\n"
                    "2. 调整 take_profit stages 的 sell_ratio，确保总和 <= 1.0\n"
                    "3. 在最后一个 stage 设置 close_invest: True"
                )
            ))
            result.is_valid = False
        
        return result
