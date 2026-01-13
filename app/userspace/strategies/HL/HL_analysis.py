#!/usr/bin/env python3
"""
HistoricLow 策略分析模块
包含各种分析方法和黑名单定义功能
"""

import json
import os
from typing import Dict, List, Any
from collections import defaultdict
from datetime import datetime, timedelta

from .settings import strategy_settings


class HistoricLowAnalysis:
    def __init__(self):
        self.tmp_dir = "app/analyzer/strategy/HL/tmp"
    
    def get_latest_session_dir(self) -> str:
        """获取最新的模拟结果目录"""
        if not os.path.exists(self.tmp_dir):
            raise FileNotFoundError("找不到tmp目录")
        
        subdirs = [d for d in os.listdir(self.tmp_dir) if os.path.isdir(os.path.join(self.tmp_dir, d))]
        if not subdirs:
            raise FileNotFoundError("找不到模拟结果目录")
        
        # 按时间排序，取最新的
        latest_dir = sorted(subdirs)[-1]
        return os.path.join(self.tmp_dir, latest_dir)
    
    def load_investment_data(self, session_dir: str) -> List[Dict[str, Any]]:
        """加载投资数据"""
        investments = []
        
        for filename in os.listdir(session_dir):
            if filename.endswith('.json') and filename != '0_session_summary.json':
                filepath = os.path.join(session_dir, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 提取投资记录
                    if 'results' in data:
                        for result in data['results']:
                            if 'slope_info' in result:
                                investments.append({
                                    'stock': filename.replace('.json', ''),
                                    'success': result.get('status') == 'win',
                                    'roi': result.get('roi', 0) * 100,  # 转换为百分比
                                    'duration': result.get('invest_duration_days', 0),
                                    'slope': result['slope_info'].get('slope_ratio', 0)
                                })
                except Exception as e:
                    print(f"⚠️ 读取文件失败 {filename}: {e}")
        
        return investments
    
    def define_blacklist(self, investments: List[Dict[str, Any]], 
                        min_investments: int = 2,
                        max_win_rate: float = 50.0,
                        max_avg_profit: float = 0.0) -> List[str]:
        """
        定义黑名单股票
        
        Args:
            investments: 投资记录列表
            min_investments: 最小投资次数（低于此次数不进入黑名单）
            max_win_rate: 最大胜率（低于此胜率进入黑名单）
            max_avg_profit: 最大平均收益（低于此收益进入黑名单）
            
        Returns:
            List[str]: 黑名单股票代码列表
        """
        # 按股票分组统计
        stock_stats = defaultdict(lambda: {
            'investments': [],
            'total_count': 0,
            'win_count': 0,
            'total_roi': 0.0
        })
        
        for inv in investments:
            stock = inv['stock']
            stock_stats[stock]['investments'].append(inv)
            stock_stats[stock]['total_count'] += 1
            stock_stats[stock]['total_roi'] += inv['roi']
            if inv['success']:
                stock_stats[stock]['win_count'] += 1
        
        # 计算每只股票的统计指标
        blacklist = []
        
        for stock, stats in stock_stats.items():
            if stats['total_count'] < min_investments:
                continue  # 投资次数太少，不进入黑名单
            
            win_rate = (stats['win_count'] / stats['total_count']) * 100
            avg_profit = stats['total_roi'] / stats['total_count']
            
            # 判断是否应该进入黑名单
            if win_rate <= max_win_rate or avg_profit <= max_avg_profit:
                blacklist.append(stock)
        
        return sorted(blacklist)
    
    def analyze_blacklist_changes(self, old_blacklist: List[str], new_blacklist: List[str]) -> Dict[str, List[str]]:
        """分析黑名单变化"""
        old_set = set(old_blacklist)
        new_set = set(new_blacklist)
        
        return {
            'removed': sorted(list(old_set - new_set)),  # 从黑名单移除的股票
            'added': sorted(list(new_set - old_set)),    # 新加入黑名单的股票
            'kept': sorted(list(old_set & new_set))      # 保持在黑名单的股票
        }
    
    def generate_blacklist_report(self, session_dir: str, 
                                 min_investments: int = 2,
                                 max_win_rate: float = 50.0,
                                 max_avg_profit: float = 0.0) -> Dict[str, Any]:
        """生成黑名单分析报告"""
        print(f"📁 分析目录: {session_dir}")
        
        # 加载投资数据
        investments = self.load_investment_data(session_dir)
        print(f"📊 总共找到 {len(investments)} 个投资记录")
        
        # 定义新的黑名单
        new_blacklist = self.define_blacklist(investments, min_investments, max_win_rate, max_avg_profit)
        
        # 获取当前黑名单
        current_blacklist = strategy_settings.get('problematic_stocks', [])
        
        # 分析变化
        changes = self.analyze_blacklist_changes(current_blacklist, new_blacklist)
        
        # 生成报告
        report = {
            'session_dir': session_dir,
            'criteria': {
                'min_investments': min_investments,
                'max_win_rate': max_win_rate,
                'max_avg_profit': max_avg_profit
            },
            'current_blacklist': current_blacklist,
            'new_blacklist': new_blacklist,
            'changes': changes,
            'summary': {
                'current_count': len(current_blacklist),
                'new_count': len(new_blacklist),
                'removed_count': len(changes['removed']),
                'added_count': len(changes['added']),
                'kept_count': len(changes['kept'])
            }
        }
        
        return report
    
    def print_blacklist_report(self, report: Dict[str, Any]):
        """打印黑名单分析报告"""
        print("\n" + "="*80)
        print("📋 黑名单分析报告")
        print("="*80)
        
        print(f"\n📊 分析标准:")
        print(f"   最小投资次数: {report['criteria']['min_investments']}")
        print(f"   最大胜率: {report['criteria']['max_win_rate']}%")
        print(f"   最大平均收益: {report['criteria']['max_avg_profit']}%")
        
        print(f"\n📈 黑名单统计:")
        print(f"   当前黑名单: {report['summary']['current_count']} 只股票")
        print(f"   新黑名单: {report['summary']['new_count']} 只股票")
        print(f"   移除: {report['summary']['removed_count']} 只股票")
        print(f"   新增: {report['summary']['added_count']} 只股票")
        print(f"   保持: {report['summary']['kept_count']} 只股票")
        
        if report['changes']['removed']:
            print(f"\n✅ 从黑名单移除的股票 ({len(report['changes']['removed'])} 只):")
            for stock in report['changes']['removed']:
                print(f"   - {stock}")
        
        if report['changes']['added']:
            print(f"\n❌ 新加入黑名单的股票 ({len(report['changes']['added'])} 只):")
            for stock in report['changes']['added']:
                print(f"   - {stock}")
        
        if report['changes']['kept']:
            print(f"\n🔄 保持在黑名单的股票 ({len(report['changes']['kept'])} 只):")
            for stock in report['changes']['kept']:
                print(f"   - {stock}")
        
        print(f"\n📝 新的黑名单:")
        for stock in report['new_blacklist']:
            print(f"   - {stock}")

    def load_all_simulation_results(self):
        """加载所有模拟结果"""
        all_investments = []
        
        if not os.path.exists(self.tmp_dir):
            print("❌ 找不到tmp目录")
            return []
        
        # 遍历所有子目录
        for subdir in os.listdir(self.tmp_dir):
            subdir_path = os.path.join(self.tmp_dir, subdir)
            if not os.path.isdir(subdir_path):
                continue
                
            print(f"📁 处理目录: {subdir}")
            
            # 处理该目录下的所有股票文件
            for filename in os.listdir(subdir_path):
                if filename.endswith('.json') and filename != '0_session_summary.json':
                    filepath = os.path.join(subdir_path, filename)
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # 提取投资记录
                        if 'results' in data:
                            for result in data['results']:
                                if 'start_date' in result:
                                    all_investments.append({
                                        'session': subdir,
                                        'stock': filename.replace('.json', ''),
                                        'invest_date': result['start_date'],
                                        'success': result.get('status') == 'win',
                                        'roi': result.get('roi', 0) * 100,
                                        'duration': result.get('invest_duration_days', 0),
                                        'slope': result.get('slope_info', {}).get('slope_ratio', 0)
                                    })
                    except Exception as e:
                        print(f"⚠️ 读取文件失败 {filename}: {e}")
        
        return all_investments
    
    def analyze_distribution_by_time(self, investments):
        """按时间分析投资分布"""
        print(f"\n📊 总共找到 {len(investments)} 个投资记录")
        
        # 按年份分组
        year_stats = defaultdict(lambda: {
            'count': 0,
            'wins': 0,
            'total_roi': 0.0,
            'stocks': set()
        })
        
        # 按月份分组（1-12月）
        month_stats = defaultdict(lambda: {
            'count': 0,
            'wins': 0,
            'total_roi': 0.0,
            'stocks': set()
        })
        
        # 按年份-月份分组
        year_month_stats = defaultdict(lambda: {
            'count': 0,
            'wins': 0,
            'total_roi': 0.0,
            'stocks': set()
        })
        
        for inv in investments:
            invest_date = inv['invest_date']
            year = invest_date[:4]
            month = invest_date[4:6]  # 修正：从第4位开始取2位作为月份
            year_month = f"{year}-{month}"
            
            # 年份统计
            year_stats[year]['count'] += 1
            year_stats[year]['total_roi'] += inv['roi']
            year_stats[year]['stocks'].add(inv['stock'])
            if inv['success']:
                year_stats[year]['wins'] += 1
            
            # 月份统计（只统计1-12月）
            if month in ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']:
                month_stats[month]['count'] += 1
                month_stats[month]['total_roi'] += inv['roi']
                month_stats[month]['stocks'].add(inv['stock'])
                if inv['success']:
                    month_stats[month]['wins'] += 1
            
            # 年月统计
            year_month_stats[year_month]['count'] += 1
            year_month_stats[year_month]['total_roi'] += inv['roi']
            year_month_stats[year_month]['stocks'].add(inv['stock'])
            if inv['success']:
                year_month_stats[year_month]['wins'] += 1
        
        return year_stats, month_stats, year_month_stats
    
    def print_month_analysis(self, month_stats):
        """打印月份分析结果"""
        print("\n" + "="*80)
        print("📅 按月份分析投资分布 (1-12月)")
        print("="*80)
        
        print(f"{'月份':<8} {'投资次数':<8} {'胜率':<8} {'平均收益':<10} {'股票数':<8} {'总收益':<10}")
        print("-" * 80)
        
        # 按1-12月顺序排序
        month_order = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
        month_names = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
        
        for i, month in enumerate(month_order):
            if month in month_stats:
                stats = month_stats[month]
                win_rate = (stats['wins'] / stats['count']) * 100 if stats['count'] > 0 else 0
                avg_roi = stats['total_roi'] / stats['count'] if stats['count'] > 0 else 0
                
                print(f"{month_names[i]:<8} {stats['count']:<8} {win_rate:<7.1f}% {avg_roi:<9.2f}% {len(stats['stocks']):<8} {stats['total_roi']:<9.2f}%")
            else:
                print(f"{month_names[i]:<8} {0:<8} {0:<7.1f}% {0:<9.2f}% {0:<8} {0:<9.2f}%")
    
    def print_year_analysis(self, year_stats):
        """打印年份分析结果"""
        print("\n" + "="*80)
        print("📅 按年份分析投资分布")
        print("="*80)
        
        print(f"{'年份':<8} {'投资次数':<8} {'胜率':<8} {'平均收益':<10} {'股票数':<8} {'总收益':<10}")
        print("-" * 80)
        
        for year in sorted(year_stats.keys()):
            stats = year_stats[year]
            win_rate = (stats['wins'] / stats['count']) * 100 if stats['count'] > 0 else 0
            avg_roi = stats['total_roi'] / stats['count'] if stats['count'] > 0 else 0
            
            print(f"{year:<8} {stats['count']:<8} {win_rate:<7.1f}% {avg_roi:<9.2f}% {len(stats['stocks']):<8} {stats['total_roi']:<9.2f}%")
    
    def find_best_worst_periods(self, year_month_stats):
        """找出最佳和最差的投资期间"""
        print("\n" + "="*80)
        print("🏆 最佳和最差投资期间分析")
        print("="*80)
        
        # 计算每个期间的胜率和平均收益
        periods = []
        for year_month, stats in year_month_stats.items():
            if stats['count'] >= 3:  # 至少3次投资才考虑
                win_rate = (stats['wins'] / stats['count']) * 100
                avg_roi = stats['total_roi'] / stats['count']
                periods.append({
                    'period': year_month,
                    'count': stats['count'],
                    'win_rate': win_rate,
                    'avg_roi': avg_roi,
                    'total_roi': stats['total_roi']
                })
        
        # 按胜率排序
        periods_by_win_rate = sorted(periods, key=lambda x: x['win_rate'], reverse=True)
        
        # 按平均收益排序
        periods_by_roi = sorted(periods, key=lambda x: x['avg_roi'], reverse=True)
        
        print("\n🥇 胜率最高的期间 (前10名):")
        print(f"{'期间':<10} {'投资次数':<8} {'胜率':<8} {'平均收益':<10} {'总收益':<10}")
        print("-" * 60)
        for period in periods_by_win_rate[:10]:
            print(f"{period['period']:<10} {period['count']:<8} {period['win_rate']:<7.1f}% {period['avg_roi']:<9.2f}% {period['total_roi']:<9.2f}%")
        
        print("\n🥉 胜率最低的期间 (后10名):")
        print(f"{'期间':<10} {'投资次数':<8} {'胜率':<8} {'平均收益':<10} {'总收益':<10}")
        print("-" * 60)
        for period in periods_by_win_rate[-10:]:
            print(f"{period['period']:<10} {period['count']:<8} {period['win_rate']:<7.1f}% {period['avg_roi']:<9.2f}% {period['total_roi']:<9.2f}%")
        
        print("\n💰 平均收益最高的期间 (前10名):")
        print(f"{'期间':<10} {'投资次数':<8} {'胜率':<8} {'平均收益':<10} {'总收益':<10}")
        print("-" * 60)
        for period in periods_by_roi[:10]:
            print(f"{period['period']:<10} {period['count']:<8} {period['win_rate']:<7.1f}% {period['avg_roi']:<9.2f}% {period['total_roi']:<9.2f}%")
        
        print("\n💸 平均收益最低的期间 (后10名):")
        print(f"{'期间':<10} {'投资次数':<8} {'胜率':<8} {'平均收益':<10} {'总收益':<10}")
        print("-" * 60)
        for period in periods_by_roi[-10:]:
            print(f"{period['period']:<10} {period['count']:<8} {period['win_rate']:<7.1f}% {period['avg_roi']:<9.2f}% {period['total_roi']:<9.2f}%")
    
    def analyze_investment_distribution(self):
        """分析投资分布"""
        print("🔍 开始分析所有模拟结果的投资分布...")
        
        # 加载所有投资数据
        investments = self.load_all_simulation_results()
        
        if not investments:
            print("❌ 没有找到投资数据")
            return None
        
        # 分析分布
        year_stats, month_stats, year_month_stats = self.analyze_distribution_by_time(investments)
        
        # 打印分析结果
        self.print_year_analysis(year_stats)
        self.print_month_analysis(month_stats)
        self.find_best_worst_periods(year_month_stats)
        
        return {
            'investments': investments,
            'year_stats': year_stats,
            'month_stats': month_stats,
            'year_month_stats': year_month_stats
        }

    def load_2024_investments(self) -> List[Dict[str, Any]]:
        """加载2024年1月到现在的投资数据，按start_date排序"""
        all_investments = []
        
        if not os.path.exists(self.tmp_dir):
            print("❌ 找不到tmp目录")
            return []
        
        # 遍历所有子目录
        for subdir in os.listdir(self.tmp_dir):
            subdir_path = os.path.join(self.tmp_dir, subdir)
            if not os.path.isdir(subdir_path):
                continue
                
            # 处理该目录下的所有股票文件
            for filename in os.listdir(subdir_path):
                if filename.endswith('.json') and filename != '0_session_summary.json':
                    filepath = os.path.join(subdir_path, filename)
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # 提取投资记录
                        if 'results' in data:
                            for result in data['results']:
                                if 'start_date' in result:
                                    start_date = result['start_date']
                                    year = start_date[:4]
                                    month = start_date[4:6]
                                    
                                    # 只处理2024年1月及以后的投资
                                    if year == '2024' and int(month) >= 1:
                                        all_investments.append({
                                            'stock': filename.replace('.json', ''),
                                            'start_date': start_date,
                                            'end_date': result.get('end_date', ''),
                                            'success': result.get('status') == 'win',
                                            'roi': result.get('roi', 0),
                                            'duration': result.get('invest_duration_days', 0),
                                            'purchase_price': result.get('purchase_price', 0),
                                            'total_profit': result.get('profit', 0)
                                        })
                                        
                    except Exception as e:
                        print(f"⚠️ 读取文件失败 {filename}: {e}")
        
        # 按start_date排序
        all_investments.sort(key=lambda x: x['start_date'])
        return all_investments
    
    def calculate_kelly_fraction(self, current_stock: str, historical_data: List[Dict[str, Any]]) -> float:
        """计算凯莉公式的投资比例 - 基于当前股票的历史胜率"""
        
        # 筛选出当前股票的历史投资记录
        stock_historical_data = [inv for inv in historical_data if inv['stock'] == current_stock]
        
        # 如果当前股票没有历史记录，使用默认胜率50%
        if len(stock_historical_data) < 3:
            # 使用默认胜率50%和平均盈亏比
            win_rate = 0.5
            avg_win = 0.15  # 默认平均盈利15%
            avg_loss = -0.08  # 默认平均亏损8%
        else:
            # 计算当前股票的历史胜率和盈亏比
            wins = sum(1 for inv in stock_historical_data if inv['success'])
            total = len(stock_historical_data)
            win_rate = wins / total if total > 0 else 0.5
            
            # 计算平均盈利和亏损
            win_returns = [inv['roi'] for inv in stock_historical_data if inv['success']]
            loss_returns = [inv['roi'] for inv in stock_historical_data if not inv['success']]
            
            avg_win = sum(win_returns) / len(win_returns) if win_returns else 0.15
            avg_loss = sum(loss_returns) / len(loss_returns) if loss_returns else -0.08
        
        # 凯莉公式
        if avg_loss == 0:
            return 0.1  # 默认投资10%
        
        b = avg_win / abs(avg_loss)
        p = win_rate
        q = 1 - win_rate
        
        if b == 0:
            return 0.1  # 默认投资10%
        
        kelly_fraction = (b * p - q) / b
        kelly_fraction = max(0.05, min(kelly_fraction, 0.3))  # 限制在5%-30%之间
        
        return kelly_fraction
    
    def simulate_daily_investment(self, investments: List[Dict[str, Any]], 
                                 initial_capital: float = 100000,
                                 base_shares: int = 500,
                                 use_kelly: bool = False,
                                 use_filter: bool = False,
                                 min_roi_threshold: float = 0.05) -> Dict[str, Any]:
        """逐日模拟投资 - 考虑时间重叠和资金占用的现实版本"""
        print(f"🔍 开始现实模拟投资...")
        print(f"   初始资金: {initial_capital:,.0f} 元")
        print(f"   基础股数: {base_shares} 股")
        print(f"   使用凯莉公式: {'是' if use_kelly else '否'}")
        
        # 按时间排序
        investments.sort(key=lambda x: x['start_date'])
        
        # 初始化状态
        cash_pool = initial_capital
        active_investments = []  # 当前投资中的股票
        total_invested = 0
        total_return = 0
        investment_count = 0
        daily_events = []
        
        print(f"   总投资机会: {len(investments)} 个")
        
        # 创建投资机会字典，按日期索引，并去重
        opportunities_by_date = defaultdict(list)
        seen_investments = set()  # 用于去重
        
        for inv in investments:
            # 创建唯一标识符
            unique_key = f"{inv['stock']}_{inv['start_date']}_{inv['purchase_price']}_{inv['roi']}"
            
            if unique_key not in seen_investments:
                seen_investments.add(unique_key)
                opportunities_by_date[inv['start_date']].append(inv)
        
        print(f"   去重后机会: {sum(len(ops) for ops in opportunities_by_date.values())} 个")
        
        # 获取时间范围 - 使用所有投资的实际时间范围
        start_dates = [inv['start_date'] for inv in investments]
        end_dates = [inv['end_date'] for inv in investments if inv['end_date']]
        
        start_date = min(start_dates)
        end_date = max(end_dates) if end_dates else max(start_dates)
        
        # 转换为datetime对象
        start_dt = datetime.strptime(start_date, '%Y%m%d')
        end_dt = datetime.strptime(end_date, '%Y%m%d')
        
        print(f"   时间范围: {start_date} 到 {end_date}")
        print(f"   总天数: {(end_dt - start_dt).days + 1} 天")
        
        # 逐日模拟
        current_dt = start_dt
        while current_dt <= end_dt:
            current_date = current_dt.strftime('%Y%m%d')
            
            # 1. 检查是否有投资需要平仓
            new_active_investments = []
            for active_inv in active_investments:
                if active_inv['end_date'] == current_date:
                    # 平仓
                    cost = active_inv['shares'] * active_inv['purchase_price']
                    if active_inv['success']:
                        profit = cost * active_inv['roi']
                        total_return += profit
                        cash_pool += cost + profit  # 本金 + 收益回到池子
                        total_invested += cost
                        
                        daily_events.append({
                            'date': current_date,
                            'action': '平仓',
                            'stock': active_inv['stock'],
                            'shares': active_inv['shares'],
                            'profit': profit,
                            'cash_pool': cash_pool,
                            'total_invested': total_invested
                        })
                    else:
                        # 亏损情况
                        loss = cost * abs(active_inv['roi'])
                        total_return -= loss
                        cash_pool += cost - loss  # 本金 - 亏损回到池子
                        total_invested += cost
                        
                        daily_events.append({
                            'date': current_date,
                            'action': '平仓',
                            'stock': active_inv['stock'],
                            'shares': active_inv['shares'],
                            'profit': -loss,
                            'cash_pool': cash_pool,
                            'total_invested': total_invested
                        })
                else:
                    # 继续持有
                    new_active_investments.append(active_inv)
            
            active_investments = new_active_investments
            
            # 2. 检查是否有新的投资机会
            if current_date in opportunities_by_date:
                for opportunity in opportunities_by_date[current_date]:
                    price = opportunity['purchase_price']
                    if price <= 0:
                        continue
                    
                    # 投资过滤：资金小于阈值时，只投资收益率大于阈值的机会
                    if use_filter and opportunity['roi'] < min_roi_threshold:
                        daily_events.append({
                            'date': current_date,
                            'action': '跳过',
                            'stock': opportunity['stock'],
                            'reason': f'收益率{opportunity["roi"]:.2%}低于阈值{min_roi_threshold:.2%}'
                        })
                        continue
                    
                    # 计算投资金额
                    if use_kelly:
                        # 使用凯莉公式 - 基于当前股票的历史胜率计算投资比例
                        historical_data = [inv for inv in investments if inv['start_date'] < current_date]
                        kelly_fraction = self.calculate_kelly_fraction(opportunity['stock'], historical_data)
                        # 计算投资金额（总资金的百分比）
                        investment_amount = cash_pool * kelly_fraction
                        # 计算股数（必须是500的倍数）
                        shares_float = investment_amount / (price * 500)  # 计算多少个500股
                        shares = round(shares_float) * 500  # 四舍五入后乘以500
                        cost = shares * price
                        
                        # 调试信息：前几个投资
                        if investment_count < 3:
                            print(f"   调试: {opportunity['stock']} 凯莉比例={kelly_fraction:.3f}, 投资金额={investment_amount:,.0f}, 股数={shares}, 成本={cost:,.0f}")
                    else:
                        # 固定股数
                        shares = base_shares
                        cost = shares * price
                    
                    # 检查资金是否足够且股数大于0
                    if cash_pool >= cost and shares > 0:
                        # 买入
                        cash_pool -= cost
                        investment_count += 1
                        
                        # 调试信息：前几个投资
                        if investment_count <= 5:
                            print(f"   执行投资 #{investment_count}: {opportunity['stock']} {shares}股，成本{cost:,.0f}元，剩余资金{cash_pool:,.0f}元")
                        elif investment_count == 10 or investment_count == 50 or investment_count == 100:
                            print(f"   执行投资 #{investment_count}: {opportunity['stock']} {shares}股，成本{cost:,.0f}元，剩余资金{cash_pool:,.0f}元")
                        
                        # 添加到投资中列表
                        active_investments.append({
                            'stock': opportunity['stock'],
                            'shares': shares,
                            'purchase_price': price,
                            'start_date': opportunity['start_date'],
                            'end_date': opportunity['end_date'],
                            'success': opportunity['success'],
                            'roi': opportunity['roi']
                        })
                        
                        daily_events.append({
                            'date': current_date,
                            'action': '买入',
                            'stock': opportunity['stock'],
                            'shares': shares,
                            'cost': cost,
                            'cash_pool': cash_pool,
                            'total_invested': total_invested
                        })
                    else:
                        # 调试信息：资金不足的情况
                        if investment_count < 5:
                            print(f"   资金不足: {opportunity['stock']} 需要{cost:,.0f}元，但只有{cash_pool:,.0f}元")
                        # 资金不足，跳过
                        daily_events.append({
                            'date': current_date,
                            'action': '跳过',
                            'stock': opportunity['stock'],
                            'shares': shares,
                            'cost': cost,
                            'cash_pool': cash_pool,
                            'total_invested': total_invested,
                            'reason': '资金不足'
                        })
            
            # 移动到下一天
            current_dt += timedelta(days=1)
        
        # 计算最终结果 - 包括现金池和投资中的资产
        invested_value = 0
        for active_inv in active_investments:
            # 计算投资中的股票当前价值（假设按买入价计算，实际应该按当前市价）
            invested_value += active_inv['shares'] * active_inv['purchase_price']
        
        final_assets = cash_pool + invested_value
        total_return_pct = (final_assets - initial_capital) / initial_capital
        
        # 计算年化收益 - 使用实际投资活跃期间
        days_diff = (end_dt - start_dt).days
        annual_return = total_return_pct * (365 / days_diff)
        
        result = {
            'initial_capital': initial_capital,
            'final_assets': final_assets,
            'total_return': total_return_pct,
            'annual_return': annual_return,
            'investment_count': investment_count,
            'total_invested': total_invested,
            'total_return_amount': total_return,
            'active_investments': len(active_investments),
            'days_diff': days_diff,
            'daily_events': daily_events
        }
        
        print(f"   最终投资次数: {investment_count}")
        print(f"   实际事件数量: {len([e for e in daily_events if e['action'] == '买入'])}")
        return result
    
    def compare_investment_methods(self, initial_capital: float = 100000, base_shares: int = 500):
        """对比固定投资和凯莉公式投资"""
        print("🔍 开始对比投资方法...")
        
        # 加载配置
        kelly_config = strategy_settings.get("core", {}).get("kelly_formula", {})
        filter_config = strategy_settings.get("core", {}).get("investment_filter", {})
        
        # 判断是否使用凯莉公式
        use_kelly = kelly_config.get("enabled", True) and initial_capital >= kelly_config.get("min_capital_threshold", 200000)
        
        # 判断是否启用投资过滤
        use_filter = filter_config.get("enabled", True) and initial_capital < filter_config.get("min_capital_threshold", 500000)
        min_roi_threshold = filter_config.get("min_roi_threshold", 0.05)
        
        print(f"💰 初始资金: {initial_capital:,.0f} 元")
        print(f"🎯 凯莉公式阈值: {kelly_config.get('min_capital_threshold', 200000):,.0f} 元")
        print(f"📊 使用凯莉公式: {'是' if use_kelly else '否'}")
        print(f"🔍 启用投资过滤: {'是' if use_filter else '否'}")
        if use_filter:
            print(f"📈 最小收益率阈值: {min_roi_threshold:.2%}")
        
        # 加载2024年投资数据
        investments = self.load_2024_investments()
        
        if not investments:
            print("❌ 没有找到2024年的投资数据")
            return None
        
        print(f"📊 找到 {len(investments)} 个2024年投资记录")
        
        if use_kelly:
            # 只运行凯莉公式投资模拟
            print("\n📈 模拟凯莉公式投资...")
            kelly_result = self.simulate_daily_investment(
                investments, initial_capital, base_shares, use_kelly=True, 
                use_filter=use_filter, min_roi_threshold=min_roi_threshold
            )
            
            # 打印凯莉公式结果
            self.print_kelly_result(kelly_result)
            
            return {
                'kelly': kelly_result,
                'method_used': 'kelly'
            }
        else:
            # 只运行固定投资模拟
            print("\n📈 模拟固定投资...")
            fixed_result = self.simulate_daily_investment(
                investments, initial_capital, base_shares, use_kelly=False,
                use_filter=use_filter, min_roi_threshold=min_roi_threshold
            )
            
            # 打印固定投资结果
            self.print_fixed_result(fixed_result)
            
            return {
                'fixed': fixed_result,
                'method_used': 'fixed'
            }
    
    def print_investment_comparison(self, fixed_result: Dict[str, Any], kelly_result: Dict[str, Any]):
        """打印投资方法对比结果"""
        print("\n" + "="*80)
        print("📊 投资方法对比报告 (2024年1月到现在)")
        print("="*80)
        
        print(f"\n💰 资金状况:")
        print(f"   初始资金: {fixed_result['initial_capital']:,.0f} 元")
        print(f"   固定投资最终资产: {fixed_result['final_assets']:,.0f} 元")
        print(f"   凯莉公式最终资产: {kelly_result['final_assets']:,.0f} 元")
        
        print(f"\n📈 收益对比:")
        print(f"   固定投资总收益: {fixed_result['total_return']*100:.2f}%")
        print(f"   凯莉公式总收益: {kelly_result['total_return']*100:.2f}%")
        print(f"   收益差异: {(kelly_result['total_return'] - fixed_result['total_return'])*100:.2f}%")
        
        print(f"\n📅 年化收益:")
        print(f"   固定投资年化收益: {fixed_result['annual_return']*100:.2f}%")
        print(f"   凯莉公式年化收益: {kelly_result['annual_return']*100:.2f}%")
        print(f"   年化收益差异: {(kelly_result['annual_return'] - fixed_result['annual_return'])*100:.2f}%")
        
        print(f"\n📊 投资统计:")
        print(f"   固定投资次数: {fixed_result['investment_count']}")
        print(f"   凯莉公式投资次数: {kelly_result['investment_count']}")
        print(f"   固定投资总投资: {fixed_result['total_invested']:,.0f} 元")
        print(f"   凯莉公式总投资: {kelly_result['total_invested']:,.0f} 元")
        print(f"   固定投资剩余持仓: 0 只")
        print(f"   凯莉公式剩余持仓: 0 只")
        
        print(f"\n📅 时间信息:")
        print(f"   投资期间: {fixed_result['days_diff']} 天")
        print(f"   年化系数: {365 / fixed_result['days_diff']:.2f}")
        
        # 显示前10个投资事件
        print(f"\n📋 固定投资前10个事件:")
        for event in fixed_result['daily_events'][:10]:
            if event['action'] == '买入':
                print(f"   {event['date']} - 买入 {event['stock']} {event['shares']}股，成本{event['cost']:,.0f}元，池子剩余{event['cash_pool']:,.0f}元")
            elif event['action'] == '平仓':
                print(f"   {event['date']} - 平仓 {event['stock']} {event['shares']}股，收益{event['profit']:,.0f}元，池子剩余{event['cash_pool']:,.0f}元")
            else:
                print(f"   {event['date']} - {event['action']} {event['stock']} {event.get('reason', '')}")
        
        print(f"\n📋 凯莉公式投资前10个事件:")
        for event in kelly_result['daily_events'][:10]:
            if event['action'] == '买入':
                print(f"   {event['date']} - 买入 {event['stock']} {event['shares']}股，成本{event['cost']:,.0f}元，池子剩余{event['cash_pool']:,.0f}元")
            elif event['action'] == '平仓':
                print(f"   {event['date']} - 平仓 {event['stock']} {event['shares']}股，收益{event['profit']:,.0f}元，池子剩余{event['cash_pool']:,.0f}元")
            else:
                print(f"   {event['date']} - {event['action']} {event['stock']} {event.get('reason', '')}")
    
    def print_kelly_result(self, kelly_result: Dict[str, Any]):
        """打印凯莉公式投资结果"""
        print("\n" + "="*80)
        print("📊 凯莉公式投资报告 (2024年1月到现在)")
        print("="*80)
        
        print(f"\n💰 资金状况:")
        print(f"   最终资产: {kelly_result['final_assets']:,.0f} 元")
        print(f"   总收益: {kelly_result['total_return']:.2f}%")
        print(f"   年化收益: {kelly_result['annual_return']:.2f}%")
        
        print(f"\n📊 投资统计:")
        print(f"   投资次数: {kelly_result['investment_count']}")
        print(f"   总投资: {kelly_result['total_invested']:,.0f} 元")
        print(f"   剩余持仓: {kelly_result['active_investments']} 只")
        
        print(f"\n📅 时间信息:")
        print(f"   投资期间: {kelly_result['days_diff']} 天")
        print(f"   年化系数: {365 / kelly_result['days_diff']:.2f}")
        
        # 显示前10个投资事件
        print(f"\n📋 前10个投资事件:")
        for event in kelly_result['daily_events'][:10]:
            if event['action'] == '买入':
                print(f"   {event['date']} - 买入 {event['stock']} {event['shares']}股，成本{event['cost']:,.0f}元，池子剩余{event['cash_pool']:,.0f}元")
            elif event['action'] == '平仓':
                print(f"   {event['date']} - 平仓 {event['stock']} {event['shares']}股，收益{event.get('profit', 0):,.0f}元，池子剩余{event['cash_pool']:,.0f}元")
            else:
                print(f"   {event['date']} - {event['action']} {event['stock']} {event.get('reason', '')}")
    
    def print_fixed_result(self, fixed_result: Dict[str, Any]):
        """打印固定投资结果"""
        print("\n" + "="*80)
        print("📊 固定投资报告 (2024年1月到现在)")
        print("="*80)
        
        print(f"\n💰 资金状况:")
        print(f"   最终资产: {fixed_result['final_assets']:,.0f} 元")
        print(f"   总收益: {fixed_result['total_return']:.2f}%")
        print(f"   年化收益: {fixed_result['annual_return']:.2f}%")
        
        print(f"\n📊 投资统计:")
        print(f"   投资次数: {fixed_result['investment_count']}")
        print(f"   总投资: {fixed_result['total_invested']:,.0f} 元")
        print(f"   剩余持仓: {fixed_result['active_investments']} 只")
        
        print(f"\n📅 时间信息:")
        print(f"   投资期间: {fixed_result['days_diff']} 天")
        print(f"   年化系数: {365 / fixed_result['days_diff']:.2f}")
        
        # 显示前10个投资事件
        print(f"\n📋 前10个投资事件:")
        for event in fixed_result['daily_events'][:10]:
            if event['action'] == '买入':
                print(f"   {event['date']} - 买入 {event['stock']} {event['shares']}股，成本{event['cost']:,.0f}元，池子剩余{event['cash_pool']:,.0f}元")
            elif event['action'] == '平仓':
                print(f"   {event['date']} - 平仓 {event['stock']} {event['shares']}股，收益{event.get('profit', 0):,.0f}元，池子剩余{event['cash_pool']:,.0f}元")
            else:
                print(f"   {event['date']} - {event['action']} {event['stock']} {event.get('reason', '')}")

    def analyze(self):
        """主分析方法"""
        try:
            session_dir = self.get_latest_session_dir()
            report = self.generate_blacklist_report(session_dir)
            self.print_blacklist_report(report)
            return report
        except Exception as e:
            print(f"❌ 分析失败: {e}")
            return None