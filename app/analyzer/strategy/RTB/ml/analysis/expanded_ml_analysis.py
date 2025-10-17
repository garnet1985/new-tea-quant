#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扩展样本的收敛区间机器学习分析
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

import pandas as pd
import numpy as np
from typing import List, Dict, Any
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import xgboost as xgb

from app.analyzer.strategy.RTB.RTB import ReverseTrendBet
from app.data_loader import DataLoader
from utils.db.db_manager import DatabaseManager

class ExpandedConvergenceMLAnalysis:
    def __init__(self):
        self.db = DatabaseManager()
        self.data_loader = DataLoader(self.db)
        self.rtb = ReverseTrendBet(db=self.db, is_verbose=False)
        
    def get_diverse_stock_sample(self, target_size: int = 800) -> List[str]:
        """
        获取多样化的股票样本
        
        Args:
            target_size: 目标样本数量
            
        Returns:
            List[str]: 股票ID列表
        """
        print(f"🎯 获取多样化股票样本 (目标: {target_size}只)")
        
        # 获取所有股票
        stock_list_table = self.db.get_table_instance('stock_list')
        all_stocks = stock_list_table.load_filtered_stock_list()
        
        # 按行业分类
        industry_stocks = {}
        for stock in all_stocks:
            industry = stock.get('industry', '其他')
            if industry not in industry_stocks:
                industry_stocks[industry] = []
            industry_stocks[industry].append(stock)
        
        # 选择样本 - 更大规模的随机抽样策略
        selected_stocks = []
        
        # 1. 分层抽样：确保每个行业都有代表
        print(f"📊 发现 {len(industry_stocks)} 个行业")
        
        # 按行业大小排序，优先选择大行业
        industry_sizes = [(industry, len(stocks)) for industry, stocks in industry_stocks.items()]
        industry_sizes.sort(key=lambda x: x[1], reverse=True)
        
        # 为每个行业分配样本数量（按行业大小比例）
        industry_allocations = {}
        remaining_target = target_size
        
        for industry, size in industry_sizes:
            if remaining_target <= 0:
                break
            # 每个行业最多分配 min(行业大小, 剩余目标/剩余行业数*2)
            remaining_industries = len([x for x in industry_sizes if x[0] not in industry_allocations])
            max_allocation = min(size, remaining_target // max(remaining_industries, 1) * 2)
            allocation = min(max_allocation, remaining_target)
            industry_allocations[industry] = allocation
            remaining_target -= allocation
        
        print(f"📊 行业样本分配: {dict(list(industry_allocations.items())[:10])}")
        
        # 2. 从每个行业随机选择股票
        np.random.seed(42)  # 固定随机种子
        
        for industry, allocation in industry_allocations.items():
            if allocation <= 0:
                continue
                
            stocks = industry_stocks[industry]
            np.random.shuffle(stocks)
            
            # 平衡沪深两市
            sh_stocks = [s for s in stocks if s['id'].endswith('.SH')]
            sz_stocks = [s for s in stocks if s['id'].endswith('.SZ')]
            
            # 按比例选择
            sh_count = min(len(sh_stocks), allocation // 2)
            sz_count = min(len(sz_stocks), allocation - sh_count)
            
            for i in range(sh_count):
                if len(selected_stocks) < target_size:
                    selected_stocks.append(sh_stocks[i]['id'])
            
            for i in range(sz_count):
                if len(selected_stocks) < target_size:
                    selected_stocks.append(sz_stocks[i]['id'])
        
        # 3. 如果还不够，完全随机补充
        if len(selected_stocks) < target_size:
            remaining_stocks = [s for s in all_stocks if s['id'] not in selected_stocks]
            np.random.shuffle(remaining_stocks)
            
            for stock in remaining_stocks:
                if len(selected_stocks) >= target_size:
                    break
                selected_stocks.append(stock['id'])
        
        # 分析样本分布
        sz_count = sum(1 for s in selected_stocks if s.endswith('.SZ'))
        sh_count = sum(1 for s in selected_stocks if s.endswith('.SH'))
        
        print(f"📊 选择样本: {len(selected_stocks)}只")
        print(f"📊 深市: {sz_count}只 ({sz_count/len(selected_stocks)*100:.1f}%)")
        print(f"📊 沪市: {sh_count}只 ({sh_count/len(selected_stocks)*100:.1f}%)")
        
        # 行业分布
        industry_count = {}
        for stock_id in selected_stocks:
            stock_info = next((s for s in all_stocks if s['id'] == stock_id), None)
            if stock_info:
                industry = stock_info.get('industry', '其他')
                industry_count[industry] = industry_count.get(industry, 0) + 1
        
        print(f"📊 行业分布: {len(industry_count)}个行业")
        print(f"📊 主要行业: {dict(list(industry_count.items())[:10])}")
        
        return selected_stocks
    
    def analyze_stock(self, stock_id: str) -> List[Dict]:
        """分析单个股票的收敛区间"""
        try:
            print(f"🔍 分析股票: {stock_id}")
            
            # 加载周线数据
            weekly_data = self.data_loader.load_klines(
                stock_id=stock_id,
                term='weekly',
                adjust='qfq',
                filter_negative=True
            )
            
            if not weekly_data or len(weekly_data) < 100:
                print(f"⚠️  {stock_id} 数据不足")
                return []
            
            # 计算技术指标
            from app.analyzer.components.indicators import Indicators
            weekly_data = Indicators.moving_average(weekly_data, 5)
            weekly_data = Indicators.moving_average(weekly_data, 10)
            weekly_data = Indicators.moving_average(weekly_data, 20)
            weekly_data = Indicators.moving_average(weekly_data, 60)
            
            # 定义收敛条件
            def is_convergent(record):
                ma5 = record.get('ma5')
                ma10 = record.get('ma10') 
                ma20 = record.get('ma20')
                ma60 = record.get('ma60')
                close = record.get('close')
                
                if not all([ma5, ma10, ma20, ma60, close]):
                    return False
                
                ma_values = [ma5, ma10, ma20, ma60]
                ma_std = np.std(ma_values)
                convergence_ratio = ma_std / close
                
                return convergence_ratio < 0.08
            
            # 找到收敛区间
            convergence_periods = self.rtb.mark_period(
                records=weekly_data,
                condition_func=is_convergent,
                min_period_length=2,
                return_format="dict"
            )
            
            if not convergence_periods:
                return []
            
            # 提取特征和标签
            analysis_data = []
            
            for period in convergence_periods:
                # 提取特征
                features = self.extract_period_features(period, weekly_data)
                
                # 计算后续表现
                performance = self.calculate_future_performance(period, weekly_data, lookforward_weeks=10)
                
                # 合并数据
                sample_data = {
                    'stock_id': stock_id,
                    'period_start': period.get('start_date'),
                    'period_end': period.get('end_date'),
                    **features,
                    **performance
                }
                
                analysis_data.append(sample_data)
            
            print(f"✅ {stock_id} 找到 {len(analysis_data)} 个收敛区间")
            return analysis_data
            
        except Exception as e:
            print(f"❌ 分析 {stock_id} 时出错: {e}")
            return []
    
    def extract_period_features(self, period: Dict, weekly_data: List[Dict]) -> Dict[str, float]:
        """从收敛区间提取特征"""
        records = period.get('records', [])
        if len(records) < 2:
            return {}
        
        start_record = records[0]
        end_record = records[-1]
        duration = len(records)
        
        # 价格特征
        start_price = start_record.get('close', 0)
        end_price = end_record.get('close', 0)
        max_price = max([r.get('close', 0) for r in records])
        min_price = min([r.get('close', 0) for r in records])
        
        # MA特征
        start_ma20 = start_record.get('ma20', 0)
        start_ma60 = start_record.get('ma60', 0)
        end_ma20 = end_record.get('ma20', 0)
        end_ma60 = end_record.get('ma60', 0)
        
        # 计算MA斜率
        def calculate_slope(start_val, end_val, periods=20):
            if start_val == 0:
                return 0
            return (end_val - start_val) / start_val / periods * 100
        
        # 计算收敛程度
        ma_values = [end_record.get('ma5', 0), end_record.get('ma10', 0), 
                    end_record.get('ma20', 0), end_record.get('ma60', 0)]
        ma_std = np.std(ma_values)
        convergence_ratio = ma_std / end_price if end_price > 0 else 0
        
        # 计算成交量特征
        volumes = [r.get('volume', 0) for r in records if r.get('volume', 0) > 0]
        amounts = [r.get('amount', 0) for r in records if r.get('amount', 0) > 0]
        
        # 计算历史平均成交量（最近100周）
        historical_volumes = [r.get('volume', 0) for r in weekly_data[-100:] if r.get('volume', 0) > 0]
        historical_amounts = [r.get('amount', 0) for r in weekly_data[-100:] if r.get('amount', 0) > 0]
        
        avg_volume = np.mean(volumes) if volumes else 0
        avg_amount = np.mean(amounts) if amounts else 0
        hist_avg_volume = np.mean(historical_volumes) if historical_volumes else 0
        hist_avg_amount = np.mean(historical_amounts) if historical_amounts else 0
        
        # 成交量比率
        volume_ratio = avg_volume / hist_avg_volume if hist_avg_volume > 0 else 1
        amount_ratio = avg_amount / hist_avg_amount if hist_avg_amount > 0 else 1
        
        # 成交量趋势（收敛区间内）
        volume_trend = 0
        amount_trend = 0
        if len(volumes) >= 2:
            volume_trend = (volumes[-1] - volumes[0]) / volumes[0] if volumes[0] > 0 else 0
        if len(amounts) >= 2:
            amount_trend = (amounts[-1] - amounts[0]) / amounts[0] if amounts[0] > 0 else 0
        
        features = {
            'duration_weeks': duration,
            'price_change_pct': ((end_price - start_price) / start_price * 100) if start_price > 0 else 0,
            'price_range_pct': ((max_price - min_price) / start_price * 100) if start_price > 0 else 0,
            'convergence_ratio': convergence_ratio,
            'ma20_slope': calculate_slope(start_ma20, end_ma20, duration),
            'ma60_slope': calculate_slope(start_ma60, end_ma60, duration),
            'position_in_range': (end_price - min_price) / (max_price - min_price) if max_price > min_price else 0.5,
            'close_to_ma20': ((end_price - end_ma20) / end_ma20 * 100) if end_ma20 > 0 else 0,
            
            # 新增成交量特征
            'volume_ratio': volume_ratio,
            'amount_ratio': amount_ratio,
            'volume_trend': volume_trend,
            'amount_trend': amount_trend,
            'avg_volume': avg_volume,
            'avg_amount': avg_amount,
        }
        
        return features
    
    def calculate_future_performance(self, period: Dict, weekly_data: List[Dict], lookforward_weeks: int = 10) -> Dict[str, float]:
        """计算后续表现"""
        end_idx = period.get('end_idx', 0)
        end_price = period.get('records', [])[-1].get('close', 0)
        
        future_data = weekly_data[end_idx + 1:end_idx + 1 + lookforward_weeks]
        
        if len(future_data) < lookforward_weeks:
            return {'max_return': 0, 'min_return': 0, 'final_return': 0, 'is_profitable': False}
        
        future_prices = [r.get('close', 0) for r in future_data]
        max_price = max(future_prices)
        min_price = min(future_prices)
        final_price = future_prices[-1]
        
        max_return = (max_price - end_price) / end_price * 100 if end_price > 0 else 0
        min_return = (min_price - end_price) / end_price * 100 if end_price > 0 else 0
        final_return = (final_price - end_price) / end_price * 100 if end_price > 0 else 0
        
        is_profitable = max_return >= 10
        
        return {
            'max_return': max_return,
            'min_return': min_return,
            'final_return': final_return,
            'is_profitable': is_profitable,
        }
    
    def run_expanded_analysis(self, sample_size: int = 800):
        """运行扩展样本分析"""
        print(f"🚀 开始扩展样本ML分析 (目标样本: {sample_size}只)")
        print("="*60)
        
        # 获取多样化样本
        stock_ids = self.get_diverse_stock_sample(sample_size)
        
        # 分析所有股票
        all_data = []
        success_count = 0
        
        for i, stock_id in enumerate(stock_ids):
            # 每10只股票显示一次进度
            if (i + 1) % 10 == 0 or i == 0:
                print(f"\n进度: {i+1}/{len(stock_ids)} ({success_count}成功)")
            
            try:
                stock_data = self.analyze_stock(stock_id)
                if stock_data:
                    all_data.extend(stock_data)
                    success_count += 1
            except Exception as e:
                if (i + 1) % 50 == 0:  # 每50只显示一次错误
                    print(f"❌ 跳过 {stock_id}: {e}")
                continue
        
        if not all_data:
            print("❌ 没有获得任何数据")
            return None
        
        df = pd.DataFrame(all_data)
        print(f"\n📊 扩展样本分析结果:")
        print(f"📊 成功分析股票: {success_count}/{len(stock_ids)}")
        print(f"📊 总收敛区间样本: {len(df)}")
        print(f"📊 整体胜率: {df['is_profitable'].mean()*100:.1f}%")
        print(f"📊 平均最大涨幅: {df['max_return'].mean():.1f}%")
        
        # 保存数据
        output_file = f'/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/expanded_convergence_ml_data_{sample_size}.csv'
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"💾 数据已保存到: {output_file}")
        
        # 训练ML模型
        if len(df) > 50:  # 至少50个样本才训练模型
            ml_results = self.train_ml_model(df)
            return df, ml_results
        else:
            print("⚠️ 样本数量不足，跳过ML模型训练")
            return df, None
    
    def train_ml_model(self, df: pd.DataFrame) -> Dict[str, Any]:
        """训练ML模型"""
        print("\n🤖 训练扩展样本ML模型...")
        
        feature_columns = [
            'duration_weeks', 'price_change_pct', 'price_range_pct', 'convergence_ratio',
            'ma20_slope', 'ma60_slope', 'position_in_range', 'close_to_ma20',
            'volume_ratio', 'amount_ratio', 'volume_trend', 'amount_trend', 'avg_volume', 'avg_amount'
        ]
        
        X = df[feature_columns].fillna(0)
        y = df['is_profitable'].astype(int)
        
        print(f"📊 特征维度: {X.shape}")
        print(f"📊 标签分布: {y.value_counts().to_dict()}")
        
        # 分割数据
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        # 训练模型
        models = {
            'RandomForest': RandomForestClassifier(n_estimators=100, random_state=42),
            'XGBoost': xgb.XGBClassifier(n_estimators=100, random_state=42, eval_metric='logloss')
        }
        
        results = {}
        
        for name, model in models.items():
            print(f"\n🔧 训练 {name} 模型...")
            
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            accuracy = (y_pred == y_test).mean()
            
            print(f"📊 {name} 准确率: {accuracy:.3f}")
            
            # 特征重要性
            if hasattr(model, 'feature_importances_'):
                feature_importance = pd.DataFrame({
                    'feature': feature_columns,
                    'importance': model.feature_importances_
                }).sort_values('importance', ascending=False)
                
                print(f"🎯 {name} 重要特征:")
                for _, row in feature_importance.head(5).iterrows():
                    print(f"   {row['feature']}: {row['importance']:.3f}")
            
            results[name] = {
                'model': model,
                'accuracy': accuracy,
                'feature_importance': feature_importance if hasattr(model, 'feature_importances_') else None,
            }
        
        return results

def main():
    """主函数"""
    analyzer = ExpandedConvergenceMLAnalysis()
    
    # 运行扩展分析
    result = analyzer.run_expanded_analysis(sample_size=800)
    
    if result:
        df, ml_results = result
        print(f"\n🎉 扩展样本ML分析完成!")
        print(f"📊 样本数量: {len(df)}")
        
        if ml_results:
            print(f"📊 最佳模型准确率: {max(r['accuracy'] for r in ml_results.values()):.3f}")
        
        # 对比小样本结果
        print(f"\n📊 与小样本(5只股票)对比:")
        print(f"   样本数量: {len(df)} vs 62")
        print(f"   胜率: {df['is_profitable'].mean()*100:.1f}% vs 38.7%")
        print(f"   平均涨幅: {df['max_return'].mean():.1f}% vs 11.3%")

if __name__ == "__main__":
    main()
