#!/usr/bin/env python3
"""
标签质量评估器

职责：
- 评估标签计算的质量
- 分析标签分布和覆盖率
- 提供标签优化建议
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger
from utils.db.db_manager import DatabaseManager


class LabelEvaluator:
    """
    标签质量评估器
    
    职责：
    - 评估标签覆盖率
    - 分析标签分布
    - 检测标签异常
    - 提供优化建议
    """
    
    def __init__(self, db: DatabaseManager):
        """
        初始化标签评估器
        
        Args:
            db: 数据库管理器实例
        """
        self.db = db
    
    def evaluate_quality(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        评估标签质量
        
        Args:
            target_date: 目标日期 (YYYY-MM-DD)
            
        Returns:
            Dict: 标签质量评估结果
        """
        if target_date is None:
            target_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"开始评估标签质量: {target_date}")
        
        evaluation = {
            'target_date': target_date,
            'coverage': self._evaluate_coverage(target_date),
            'distribution': self._evaluate_distribution(target_date),
            'consistency': self._evaluate_consistency(target_date),
            'anomalies': self._detect_anomalies(target_date),
            'recommendations': []
        }
        
        # 生成优化建议
        evaluation['recommendations'] = self._generate_recommendations(evaluation)
        
        logger.info(f"标签质量评估完成: {target_date}")
        return evaluation
    
    def _evaluate_coverage(self, target_date: str) -> Dict[str, Any]:
        """
        评估标签覆盖率
        
        Args:
            target_date: 目标日期
            
        Returns:
            Dict: 覆盖率评估结果
        """
        try:
            # 获取总股票数
            stock_list_table = self.db.get_table_instance('stock_list')
            total_stocks = len(stock_list_table.load_filtered_stock_list())
            
            # 获取有标签的股票数
            sql = """
            SELECT COUNT(DISTINCT stock_id) as labeled_stocks
            FROM stock_labels 
            WHERE label_date <= %s
            """
            
            result = self.db.execute_query(sql, (target_date,))
            labeled_stocks = result[0]['labeled_stocks'] if result else 0
            
            # 计算覆盖率
            coverage_rate = labeled_stocks / total_stocks if total_stocks > 0 else 0
            
            return {
                'total_stocks': total_stocks,
                'labeled_stocks': labeled_stocks,
                'coverage_rate': coverage_rate,
                'status': 'good' if coverage_rate > 0.8 else 'poor' if coverage_rate < 0.5 else 'fair'
            }
            
        except Exception as e:
            logger.error(f"评估标签覆盖率失败: {target_date}, {e}")
            return {'error': str(e)}
    
    def _evaluate_distribution(self, target_date: str) -> Dict[str, Any]:
        """
        评估标签分布
        
        Args:
            target_date: 目标日期
            
        Returns:
            Dict: 分布评估结果
        """
        try:
            # 获取各标签的使用频率
            sql = """
            SELECT labels FROM stock_labels 
            WHERE label_date <= %s
            ORDER BY label_date DESC
            """
            
            result = self.db.execute_query(sql, (target_date,))
            
            label_counts = {}
            if result:
                for row in result:
                    labels = row['labels'].split(',') if row['labels'] else []
                    for label in labels:
                        label = label.strip()
                        if label:
                            label_counts[label] = label_counts.get(label, 0) + 1
            
            # 分析分布
            total_labels = sum(label_counts.values())
            distribution = {}
            
            for label_id, count in label_counts.items():
                percentage = count / total_labels if total_labels > 0 else 0
                distribution[label_id] = {
                    'count': count,
                    'percentage': percentage,
                    'status': 'balanced' if 0.1 <= percentage <= 0.4 else 'imbalanced'
                }
            
            return {
                'total_labels': total_labels,
                'unique_labels': len(label_counts),
                'distribution': distribution,
                'status': 'good' if len(distribution) > 5 else 'poor'
            }
            
        except Exception as e:
            logger.error(f"评估标签分布失败: {target_date}, {e}")
            return {'error': str(e)}
    
    def _evaluate_consistency(self, target_date: str) -> Dict[str, Any]:
        """
        评估标签一致性
        
        Args:
            target_date: 目标日期
            
        Returns:
            Dict: 一致性评估结果
        """
        try:
            # 检查标签变化频率
            sql = """
            SELECT stock_id, COUNT(*) as change_count
            FROM stock_labels 
            WHERE label_date <= %s
            GROUP BY stock_id
            HAVING COUNT(*) > 1
            ORDER BY change_count DESC
            """
            
            result = self.db.execute_query(sql, (target_date,))
            
            high_change_stocks = []
            if result:
                for row in result:
                    if row['change_count'] > 3:  # 变化次数超过3次
                        high_change_stocks.append({
                            'stock_id': row['stock_id'],
                            'change_count': row['change_count']
                        })
            
            # 计算一致性指标
            total_stocks_with_labels = len(self.db.execute_query(
                "SELECT DISTINCT stock_id FROM stock_labels WHERE label_date <= %s", (target_date,)
            ))
            
            consistency_rate = 1 - (len(high_change_stocks) / total_stocks_with_labels) if total_stocks_with_labels > 0 else 1
            
            return {
                'total_stocks_with_labels': total_stocks_with_labels,
                'high_change_stocks': len(high_change_stocks),
                'consistency_rate': consistency_rate,
                'status': 'good' if consistency_rate > 0.8 else 'poor' if consistency_rate < 0.5 else 'fair',
                'problematic_stocks': high_change_stocks[:10]  # 只返回前10个
            }
            
        except Exception as e:
            logger.error(f"评估标签一致性失败: {target_date}, {e}")
            return {'error': str(e)}
    
    def _detect_anomalies(self, target_date: str) -> Dict[str, Any]:
        """
        检测标签异常
        
        Args:
            target_date: 目标日期
            
        Returns:
            Dict: 异常检测结果
        """
        try:
            anomalies = {
                'missing_labels': [],
                'duplicate_labels': [],
                'invalid_labels': []
            }
            
            # 检测缺失标签
            sql = """
            SELECT s.id as stock_id
            FROM stock_list s
            LEFT JOIN stock_labels sl ON s.id = sl.stock_id AND sl.label_date <= %s
            WHERE sl.stock_id IS NULL
            LIMIT 20
            """
            
            result = self.db.execute_query(sql, (target_date,))
            if result:
                anomalies['missing_labels'] = [row['stock_id'] for row in result]
            
            # 检测重复标签
            sql = """
            SELECT stock_id, label_date, COUNT(*) as duplicate_count
            FROM stock_labels 
            WHERE label_date <= %s
            GROUP BY stock_id, label_date
            HAVING COUNT(*) > 1
            LIMIT 10
            """
            
            result = self.db.execute_query(sql, (target_date,))
            if result:
                anomalies['duplicate_labels'] = [row for row in result]
            
            # 检测无效标签
            sql = """
            SELECT DISTINCT labels FROM stock_labels 
            WHERE label_date <= %s
            """
            
            result = self.db.execute_query(sql, (target_date,))
            if result:
                invalid_labels = []
                for row in result:
                    labels = row['labels'].split(',') if row['labels'] else []
                    for label in labels:
                        label = label.strip()
                        if label and not self._is_valid_label(label):
                            invalid_labels.append(label)
                
                anomalies['invalid_labels'] = list(set(invalid_labels))
            
            return anomalies
            
        except Exception as e:
            logger.error(f"检测标签异常失败: {target_date}, {e}")
            return {'error': str(e)}
    
    def _is_valid_label(self, label_id: str) -> bool:
        """
        检查标签ID是否有效
        
        Args:
            label_id: 标签ID
            
        Returns:
            bool: 是否有效
        """
        try:
            sql = "SELECT 1 FROM label_definitions WHERE label_id = %s AND is_active = TRUE"
            result = self.db.execute_query(sql, (label_id,))
            return len(result) > 0
        except:
            return False
    
    def _generate_recommendations(self, evaluation: Dict[str, Any]) -> List[str]:
        """
        生成优化建议
        
        Args:
            evaluation: 评估结果
            
        Returns:
            List[str]: 优化建议列表
        """
        recommendations = []
        
        # 基于覆盖率的建议
        coverage = evaluation.get('coverage', {})
        if coverage.get('coverage_rate', 0) < 0.8:
            recommendations.append(f"标签覆盖率较低({coverage.get('coverage_rate', 0):.1%})，建议增加标签计算频率")
        
        # 基于分布的建议
        distribution = evaluation.get('distribution', {})
        if distribution.get('unique_labels', 0) < 5:
            recommendations.append("标签种类较少，建议增加更多维度的标签")
        
        # 基于一致性的建议
        consistency = evaluation.get('consistency', {})
        if consistency.get('consistency_rate', 1) < 0.8:
            recommendations.append("标签一致性较差，建议检查标签计算逻辑")
        
        # 基于异常的建议
        anomalies = evaluation.get('anomalies', {})
        if anomalies.get('missing_labels'):
            recommendations.append(f"发现{len(anomalies['missing_labels'])}只股票缺少标签，建议补充计算")
        
        if anomalies.get('invalid_labels'):
            recommendations.append(f"发现{len(anomalies['invalid_labels'])}个无效标签，建议清理")
        
        return recommendations
