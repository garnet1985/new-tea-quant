#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
均线收敛机器学习分析
使用mark_period找到所有收敛区间，分析后续表现，训练ML模型
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

class ConvergenceMLAnalysis:
    def __init__(self):
        self.db = DatabaseManager()
        self.data_loader = DataLoader(self.db)
        self.rtb = ReverseTrendBet(db=self.db, is_verbose=False)
        
    def find_convergence_periods(self, stock_id: str, convergence_threshold: float = 0.08) -> List[Dict]:
        """
        找到指定股票的均线收敛区间
        
        Args:
            stock_id: 股票ID
            convergence_threshold: 收敛阈值（MA标准差/收盘价的比值）
            
        Returns:
            List[Dict]: 收敛区间列表
        """
        print(f"🔍 分析股票 {stock_id} 的收敛区间...")
        
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
        
        # 定义收敛条件函数
        def is_convergent(record):
            ma5 = record.get('ma5')
            ma10 = record.get('ma10') 
            ma20 = record.get('ma20')
            ma60 = record.get('ma60')
            close = record.get('close')
            
            if not all([ma5, ma10, ma20, ma60, close]):
                return False
            
            # 计算MA标准差
            ma_values = [ma5, ma10, ma20, ma60]
            ma_std = np.std(ma_values)
            convergence_ratio = ma_std / close
            
            return convergence_ratio < convergence_threshold
        
        # 使用mark_period找到收敛区间
        convergence_periods = self.rtb.mark_period(
            records=weekly_data,
            condition_func=is_convergent,
            min_period_length=2,  # 至少2周
            return_format="dict"
        )
        
        print(f"📊 {stock_id} 找到 {len(convergence_periods)} 个收敛区间")
        return convergence_periods
    
    def extract_period_features(self, period: Dict, weekly_data: List[Dict]) -> Dict[str, float]:
        """
        从收敛区间提取特征
        
        Args:
            period: 收敛区间信息
            weekly_data: 完整的周线数据
            
        Returns:
            Dict[str, float]: 特征字典
        """
        records = period.get('records', [])
        if len(records) < 2:
            return {}
        
        # 基础区间信息
        start_record = records[0]
        end_record = records[-1]
        duration = len(records)
        
        # 价格特征
        start_price = start_record.get('close', 0)
        end_price = end_record.get('close', 0)
        max_price = max([r.get('close', 0) for r in records])
        min_price = min([r.get('close', 0) for r in records])
        
        # MA特征
        start_ma5 = start_record.get('ma5', 0)
        start_ma10 = start_record.get('ma10', 0)
        start_ma20 = start_record.get('ma20', 0)
        start_ma60 = start_record.get('ma60', 0)
        
        end_ma5 = end_record.get('ma5', 0)
        end_ma10 = end_record.get('ma10', 0)
        end_ma20 = end_record.get('ma20', 0)
        end_ma60 = end_record.get('ma60', 0)
        
        # 计算MA斜率（20周变化率）
        def calculate_slope(start_val, end_val, periods=20):
            if start_val == 0:
                return 0
            return (end_val - start_val) / start_val / periods * 100
        
        # 成交量特征
        volumes = [r.get('volume', 0) for r in records]
        avg_volume = np.mean(volumes) if volumes else 0
        
        # 计算收敛程度
        ma_values = [end_ma5, end_ma10, end_ma20, end_ma60]
        ma_std = np.std(ma_values)
        convergence_ratio = ma_std / end_price if end_price > 0 else 0
        
        features = {
            # 基础特征
            'duration_weeks': duration,
            'price_change_pct': ((end_price - start_price) / start_price * 100) if start_price > 0 else 0,
            'price_range_pct': ((max_price - min_price) / start_price * 100) if start_price > 0 else 0,
            'convergence_ratio': convergence_ratio,
            
            # MA斜率特征
            'ma5_slope': calculate_slope(start_ma5, end_ma5, duration),
            'ma10_slope': calculate_slope(start_ma10, end_ma10, duration),
            'ma20_slope': calculate_slope(start_ma20, end_ma20, duration),
            'ma60_slope': calculate_slope(start_ma60, end_ma60, duration),
            
            # 相对位置特征
            'position_in_range': (end_price - min_price) / (max_price - min_price) if max_price > min_price else 0.5,
            'close_to_ma20': ((end_price - end_ma20) / end_ma20 * 100) if end_ma20 > 0 else 0,
            'close_to_ma60': ((end_price - end_ma60) / end_ma60 * 100) if end_ma60 > 0 else 0,
            
            # 成交量特征
            'volume_ratio': avg_volume / np.mean([r.get('volume', 0) for r in weekly_data[-20:]]) if len(weekly_data) >= 20 else 1,
        }
        
        return features
    
    def calculate_future_performance(self, period: Dict, weekly_data: List[Dict], lookforward_weeks: int = 10) -> Dict[str, float]:
        """
        计算收敛区间后续表现
        
        Args:
            period: 收敛区间信息
            weekly_data: 完整的周线数据
            lookforward_weeks: 向前观察周数
            
        Returns:
            Dict[str, float]: 后续表现指标
        """
        end_idx = period.get('end_idx', 0)
        end_price = period.get('records', [])[-1].get('close', 0)
        
        # 获取后续数据
        future_data = weekly_data[end_idx + 1:end_idx + 1 + lookforward_weeks]
        
        if len(future_data) < lookforward_weeks:
            return {'max_return': 0, 'min_return': 0, 'final_return': 0, 'is_profitable': False}
        
        # 计算后续价格变化
        future_prices = [r.get('close', 0) for r in future_data]
        max_price = max(future_prices)
        min_price = min(future_prices)
        final_price = future_prices[-1]
        
        max_return = (max_price - end_price) / end_price * 100 if end_price > 0 else 0
        min_return = (min_price - end_price) / end_price * 100 if end_price > 0 else 0
        final_return = (final_price - end_price) / end_price * 100 if end_price > 0 else 0
        
        # 定义成功标准（10周内涨幅超过10%）
        is_profitable = max_return >= 10
        
        return {
            'max_return': max_return,
            'min_return': min_return,
            'final_return': final_return,
            'is_profitable': is_profitable,
            'max_return_5w': (max(future_prices[:5]) - end_price) / end_price * 100 if len(future_prices) >= 5 and end_price > 0 else 0,
            'max_return_20w': max_return,  # 20周最大涨幅
        }
    
    def analyze_stock(self, stock_id: str) -> List[Dict]:
        """
        分析单个股票的所有收敛区间
        
        Args:
            stock_id: 股票ID
            
        Returns:
            List[Dict]: 包含特征和标签的数据列表
        """
        print(f"\n🔍 开始分析股票: {stock_id}")
        
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
        
        # 找到收敛区间
        convergence_periods = self.find_convergence_periods(stock_id, convergence_threshold=0.08)
        
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
        
        print(f"✅ {stock_id} 分析完成，获得 {len(analysis_data)} 个样本")
        return analysis_data
    
    def analyze_multiple_stocks(self, stock_ids: List[str]) -> pd.DataFrame:
        """
        分析多只股票的收敛区间
        
        Args:
            stock_ids: 股票ID列表
            
        Returns:
            pd.DataFrame: 包含所有样本的DataFrame
        """
        print(f"🚀 开始分析 {len(stock_ids)} 只股票的收敛区间...")
        
        all_data = []
        
        for stock_id in stock_ids:
            try:
                stock_data = self.analyze_stock(stock_id)
                all_data.extend(stock_data)
            except Exception as e:
                print(f"❌ 分析 {stock_id} 时出错: {e}")
                continue
        
        if not all_data:
            print("❌ 没有获得任何数据")
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        print(f"📊 总共获得 {len(df)} 个收敛区间样本")
        
        # 基本统计
        profitable_count = df['is_profitable'].sum()
        win_rate = profitable_count / len(df) * 100
        avg_max_return = df['max_return'].mean()
        
        print(f"📈 整体胜率: {win_rate:.1f}% ({profitable_count}/{len(df)})")
        print(f"📈 平均最大涨幅: {avg_max_return:.1f}%")
        
        return df
    
    def train_ml_model(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        训练机器学习模型
        
        Args:
            df: 包含特征和标签的DataFrame
            
        Returns:
            Dict[str, Any]: 模型和评估结果
        """
        print("\n🤖 开始训练机器学习模型...")
        
        # 准备特征和标签
        feature_columns = [
            'duration_weeks', 'price_change_pct', 'price_range_pct', 'convergence_ratio',
            'ma5_slope', 'ma10_slope', 'ma20_slope', 'ma60_slope',
            'position_in_range', 'close_to_ma20', 'close_to_ma60', 'volume_ratio'
        ]
        
        X = df[feature_columns].fillna(0)
        y = df['is_profitable'].astype(int)
        
        print(f"📊 特征维度: {X.shape}")
        print(f"📊 标签分布: {y.value_counts().to_dict()}")
        
        # 分割训练和测试集
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        # 训练多个模型
        models = {
            'RandomForest': RandomForestClassifier(n_estimators=100, random_state=42),
            'XGBoost': xgb.XGBClassifier(n_estimators=100, random_state=42, eval_metric='logloss')
        }
        
        results = {}
        
        for name, model in models.items():
            print(f"\n🔧 训练 {name} 模型...")
            
            # 训练模型
            model.fit(X_train, y_train)
            
            # 预测
            y_pred = model.predict(X_test)
            
            # 评估
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
                'classification_report': classification_report(y_test, y_pred, output_dict=True)
            }
        
        return results

def main():
    """主函数"""
    analyzer = ConvergenceMLAnalysis()
    
    # 测试股票列表（可以根据需要调整）
    test_stocks = [
        '000001.SZ',  # 平安银行
        '000002.SZ',  # 万科A
        '000006.SZ',  # 深振业A
        '000007.SZ',  # 全新好
        '000011.SZ',  # 深物业A
    ]
    
    # 分析多只股票
    df = analyzer.analyze_multiple_stocks(test_stocks)
    
    if df.empty:
        print("❌ 没有获得数据，无法继续分析")
        return
    
    # 保存原始数据
    output_file = '/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/convergence_ml_data.csv'
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"💾 数据已保存到: {output_file}")
    
    # 训练机器学习模型
    ml_results = analyzer.train_ml_model(df)
    
    # 输出总结
    print("\n" + "="*50)
    print("🎯 收敛区间机器学习分析总结")
    print("="*50)
    
    for model_name, result in ml_results.items():
        print(f"\n📊 {model_name} 模型:")
        print(f"   准确率: {result['accuracy']:.3f}")
        
        if result['feature_importance'] is not None:
            print(f"   重要特征: {result['feature_importance'].head(3)['feature'].tolist()}")

if __name__ == "__main__":
    main()
