#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app.analyzer.strategy.historicLow.strategy_settings import strategy_settings

def test_strategy_settings():
    """测试策略设置读取"""
    print("测试策略设置读取:")
    print("=" * 50)
    
    goal_cfg = strategy_settings.get('goal', {})
    take_profit_stages = (goal_cfg.get('take_profit') or {}).get('stages') or []
    stop_loss_stages = (goal_cfg.get('stop_loss') or {}).get('stages') or []
    
    print(f"take_profit_stages: {take_profit_stages}")
    print(f"stop_loss_stages: {stop_loss_stages}")
    
    print("\n构建stages:")
    stages = []
    
    # 1) 移动止损至不亏不赚
    for s in stop_loss_stages:
        wr = float(s.get('win_ratio') or 0.0)
        is_dyn = bool(s.get('is_dynamic_loss', False))
        loss_ratio = float(s.get('loss_ratio') or 0.0)
        if not is_dyn and loss_ratio == 0 and wr > 0:
            has_take_profit_at_same_level = any(
                float(tp.get('win_ratio') or 0.0) == wr 
                for tp in take_profit_stages
            )
            if not has_take_profit_at_same_level:
                stages.append({ 'profit_rate': wr, 'action': 'move_stop_loss_to_breakeven' })
            break
    
    # 2) 分段止盈
    for s in take_profit_stages:
        wr = float(s.get('win_ratio') or 0.0)
        sr = float(s.get('sell_ratio') or 0.0)
        stages.append({ 'profit_rate': wr, 'action': 'partial_exit', 'exit_ratio': sr })
    
    # 3) 动态止损触发
    dyn = next((s for s in stop_loss_stages if s.get('is_dynamic_loss')), None)
    if dyn is not None:
        stages.append({
            'profit_rate': float(dyn.get('win_ratio') or 0.0),
            'action': 'dynamic_trailing_stop',
            'trail_ratio': float(dyn.get('loss_ratio') or 0.1)
        })
    
    print(f"构建的stages: {stages}")
    
    # 测试execute_stage_action中的逻辑
    print("\n测试execute_stage_action逻辑:")
    for stage in stages:
        action = stage.get('action', '')
        profit_rate = stage.get('profit_rate', 0)
        
        if action == 'partial_exit':
            exit_ratio = stage.get('exit_ratio', 0.2)
            print(f"  止盈阶段: {profit_rate*100:.0f}% -> {exit_ratio*100:.0f}%")
            print(f"  会调用: StrategyEntity.to_target(win_ratio={profit_rate}, ...)")

if __name__ == "__main__":
    test_strategy_settings()
