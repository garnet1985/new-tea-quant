#!/usr/bin/env python3
"""
对比黑名单更新前后的结果
"""

import json
import os
import statistics

def load_session_summary(version_dir):
    """加载指定版本的session summary"""
    session_file = f"app/analyzer/strategy/historicLow/tmp/{version_dir}/session_summary.json"
    
    if not os.path.exists(session_file):
        print(f"❌ 文件不存在: {session_file}")
        return None
    
    with open(session_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def compare_results():
    print("=" * 80)
    print("📊 黑名单更新前后结果对比分析")
    print("=" * 80)
    print()
    
    # 加载524版本结果（更新前）
    v524_data = load_session_summary("2025_09_11-524-backup")
    
    if not v524_data:
        print("❌ 无法加载524版本数据")
        return
    
    print("📈 524版本结果 (更新前):")
    print("-" * 60)
    print(f"  总投资次数: {v524_data['total_investments']:,}")
    print(f"  胜率: {v524_data['win_rate']:.1f}%")
    print(f"  平均ROI: {v524_data['avg_roi']:.1f}%")
    print(f"  年化收益率: {v524_data['annual_return']:.1f}%")
    print(f"  平均投资时长: {v524_data['avg_duration_days']:.1f}天")
    print(f"  总收益: {v524_data['total_profit']:.1f}")
    print(f"  平均每笔收益: {v524_data['avg_profit_per_investment']:.2f}")
    print()
    
    # 显示结果分布
    print("🎯 结果分布:")
    print(f"  🟢 盈利 (≥20%): {v524_data['green_dot_count']:,} ({v524_data['green_dot_rate']:.1f}%)")
    print(f"  🟡 微盈 (<20%): {v524_data['yellow_dot_count']:,} ({v524_data['yellow_dot_rate']:.1f}%)")
    print(f"  🔴 亏损: {v524_data['red_dot_count']:,} ({v524_data['red_dot_rate']:.1f}%)")
    print()
    
    # 分析黑名单更新影响
    print("📊 黑名单更新影响分析:")
    print("-" * 60)
    
    # 从之前的分析我们知道：
    # 原黑名单: 51只股票，396次投资，平均胜率69.5%，平均ROI7.6%
    # 新黑名单: 1只股票，4次投资，平均胜率25.0%，平均ROI-1.8%
    
    print("黑名单更新详情:")
    print(f"  原黑名单: 51只股票，396次投资")
    print(f"  新黑名单: 1只股票，4次投资")
    print(f"  移除股票: 50只股票，392次投资")
    print()
    
    # 计算理论上的改善
    print("理论改善计算:")
    
    # 原黑名单股票的表现
    old_blacklist_investments = 396
    old_blacklist_win_rate = 69.5
    old_blacklist_avg_roi = 7.6
    old_blacklist_total_profit = 111.95
    
    # 新黑名单股票的表现
    new_blacklist_investments = 4
    new_blacklist_win_rate = 25.0
    new_blacklist_avg_roi = -1.8
    new_blacklist_total_profit = -24.45
    
    # 移除的股票表现
    removed_investments = old_blacklist_investments - new_blacklist_investments
    removed_total_profit = old_blacklist_total_profit - new_blacklist_total_profit
    
    print(f"  移除的股票:")
    print(f"    投资次数: {removed_investments}")
    print(f"    总收益: {removed_total_profit:.2f}")
    print(f"    平均每笔收益: {removed_total_profit/removed_investments:.2f}")
    print()
    
    # 计算如果这些股票不在黑名单中的潜在收益
    # 假设非黑名单股票的平均表现
    non_blacklist_avg_roi = 9.9  # 从之前的分析得出
    non_blacklist_win_rate = 71.2  # 从之前的分析得出
    
    # 估算移除股票的潜在收益（如果按非黑名单股票表现）
    estimated_profit_per_investment = non_blacklist_avg_roi / 100  # 转换为小数
    estimated_total_profit = removed_investments * estimated_profit_per_investment
    
    print(f"  潜在改善:")
    print(f"    如果移除股票按非黑名单表现:")
    print(f"    估算总收益: {estimated_total_profit:.2f}")
    print(f"    实际总收益: {removed_total_profit:.2f}")
    print(f"    收益差异: {estimated_total_profit - removed_total_profit:.2f}")
    print()
    
    # 计算整体改善
    total_improvement = estimated_total_profit - removed_total_profit
    improvement_percentage = (total_improvement / v524_data['total_profit']) * 100
    
    print(f"📈 整体改善估算:")
    print(f"  总收益改善: {total_improvement:.2f}")
    print(f"  改善百分比: {improvement_percentage:.1f}%")
    print()
    
    # 分析黑名单标准
    print("🎯 黑名单标准分析:")
    print("-" * 60)
    print("当前黑名单标准:")
    print("  - 最少投资次数: 3次")
    print("  - 最大胜率: 30%")
    print("  - 最大平均收益: -5.0")
    print()
    
    print("标准合理性分析:")
    print("  ✅ 投资次数标准合理: 确保有足够样本")
    print("  ✅ 胜率标准严格: 30%以下确实表现很差")
    print("  ✅ 收益标准合理: -5%以下确实亏损严重")
    print()
    
    # 建议
    print("💡 建议:")
    print("-" * 60)
    print("1. 黑名单更新效果:")
    print("   - 大幅减少了黑名单股票数量 (51→1)")
    print("   - 移除了表现相对较好的股票")
    print("   - 保留了真正的问题股票")
    print()
    
    print("2. 策略优化建议:")
    print("   - 可以考虑更严格的黑名单标准")
    print("   - 建议增加最大投资次数限制")
    print("   - 可以考虑增加最大亏损幅度限制")
    print()
    
    print("3. 监控建议:")
    print("   - 定期更新黑名单 (建议每季度)")
    print("   - 监控新黑名单股票的表现")
    print("   - 跟踪整体策略表现变化")
    print()
    
    print("=" * 80)
    print("✅ 黑名单更新影响分析完成")
    print("=" * 80)

if __name__ == "__main__":
    compare_results()
