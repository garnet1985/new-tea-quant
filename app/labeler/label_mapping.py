#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
标签映射定义
定义各种标签的ID、名称、分类和描述
"""

from typing import Dict, List, Any, Optional


class LabelMapping:
    """标签映射管理器"""
    
    # 标签分类定义
    CATEGORIES = {
        'market_cap': '市值规模',
        'industry': '行业分类', 
        'volatility': '波动性',
        'volume': '成交量',
        'financial': '财务指标',
        'technical': '技术指标',
        'growth': '成长性',
        'value': '价值指标'
    }
    
    # 市值规模标签映射
    MARKET_CAP_LABELS = {
        'large_cap': {
            'id': 'large_cap',
            'name': '大盘股',
            'category': 'market_cap',
            'description': '市值大于100亿的股票',
            'threshold': 10000000000  # 100亿（元）
        },
        'mid_cap': {
            'id': 'mid_cap', 
            'name': '中盘股',
            'category': 'market_cap',
            'description': '市值30-100亿的股票',
            'threshold_min': 3000000000,  # 30亿
            'threshold_max': 10000000000  # 100亿
        },
        'small_cap': {
            'id': 'small_cap',
            'name': '小盘股', 
            'category': 'market_cap',
            'description': '市值小于30亿的股票',
            'threshold': 3000000000  # 30亿
        }
    }
    
    # 行业分类标签映射
    INDUSTRY_LABELS = {
        'finance': {
            'id': 'finance',
            'name': '金融业',
            'category': 'industry',
            'description': '银行、保险、证券等金融行业',
            'industries': ['银行', '保险', '证券', '信托', '租赁']
        },
        'technology': {
            'id': 'technology',
            'name': '科技行业',
            'category': 'industry', 
            'description': '信息技术、软件、电子等科技行业',
            'industries': ['软件', '电子', '通信', '计算机', '互联网']
        },
        'consumer': {
            'id': 'consumer',
            'name': '消费行业',
            'category': 'industry',
            'description': '食品饮料、家电、零售等消费行业',
            'industries': ['食品饮料', '家电', '零售', '纺织服装', '汽车']
        },
        'manufacturing': {
            'id': 'manufacturing',
            'name': '制造业',
            'category': 'industry',
            'description': '机械设备、化工、钢铁等制造业',
            'industries': ['机械设备', '化工', '钢铁', '有色金属', '建筑材料']
        },
        'energy': {
            'id': 'energy',
            'name': '能源行业',
            'category': 'industry',
            'description': '石油、煤炭、电力等能源行业',
            'industries': ['石油', '煤炭', '电力', '天然气', '新能源']
        },
        'healthcare': {
            'id': 'healthcare',
            'name': '医疗健康',
            'category': 'industry',
            'description': '医药、医疗器械、医疗服务等',
            'industries': ['医药', '医疗器械', '医疗服务', '生物技术']
        },
        'real_estate': {
            'id': 'real_estate',
            'name': '房地产',
            'category': 'industry',
            'description': '房地产开发、建筑、装饰等',
            'industries': ['房地产开发', '建筑', '装饰', '物业管理']
        }
    }
    
    # 波动性标签映射
    VOLATILITY_LABELS = {
        'high_volatility': {
            'id': 'high_volatility',
            'name': '高波动',
            'category': 'volatility',
            'description': '波动率大于30%的股票',
            'threshold': 0.30
        },
        'medium_volatility': {
            'id': 'medium_volatility',
            'name': '中等波动',
            'category': 'volatility',
            'description': '波动率15-30%的股票',
            'threshold_min': 0.15,
            'threshold_max': 0.30
        },
        'low_volatility': {
            'id': 'low_volatility',
            'name': '低波动',
            'category': 'volatility',
            'description': '波动率小于15%的股票',
            'threshold': 0.15
        }
    }
    
    # 成交量标签映射
    VOLUME_LABELS = {
        'high_volume': {
            'id': 'high_volume',
            'name': '高成交量',
            'category': 'volume',
            'description': '成交量比率大于2.0的股票',
            'threshold': 2.0
        },
        'medium_volume': {
            'id': 'medium_volume',
            'name': '中等成交量',
            'category': 'volume',
            'description': '成交量比率0.5-2.0的股票',
            'threshold_min': 0.5,
            'threshold_max': 2.0
        },
        'low_volume': {
            'id': 'low_volume',
            'name': '低成交量',
            'category': 'volume',
            'description': '成交量比率小于0.5的股票',
            'threshold': 0.5
        }
    }
    
    # 财务指标标签映射
    FINANCIAL_LABELS = {
        'high_pe': {
            'id': 'high_pe',
            'name': '高市盈率',
            'category': 'financial',
            'description': 'PE大于50的股票',
            'threshold': 50
        },
        'medium_pe': {
            'id': 'medium_pe',
            'name': '中等市盈率',
            'category': 'financial',
            'description': 'PE 15-50的股票',
            'threshold_min': 15,
            'threshold_max': 50
        },
        'low_pe': {
            'id': 'low_pe',
            'name': '低市盈率',
            'category': 'financial',
            'description': 'PE小于15的股票',
            'threshold': 15
        },
        'high_pb': {
            'id': 'high_pb',
            'name': '高市净率',
            'category': 'financial',
            'description': 'PB大于5的股票',
            'threshold': 5
        },
        'medium_pb': {
            'id': 'medium_pb',
            'name': '中等市净率',
            'category': 'financial',
            'description': 'PB 1-5的股票',
            'threshold_min': 1,
            'threshold_max': 5
        },
        'low_pb': {
            'id': 'low_pb',
            'name': '低市净率',
            'category': 'financial',
            'description': 'PB小于1的股票',
            'threshold': 1
        }
    }
    
    @classmethod
    def get_all_labels(cls) -> Dict[str, Dict[str, Any]]:
        """
        获取所有标签定义
        
        Returns:
            Dict[str, Dict[str, Any]]: 所有标签定义
        """
        all_labels = {}
        all_labels.update(cls.MARKET_CAP_LABELS)
        all_labels.update(cls.INDUSTRY_LABELS)
        all_labels.update(cls.VOLATILITY_LABELS)
        all_labels.update(cls.VOLUME_LABELS)
        all_labels.update(cls.FINANCIAL_LABELS)
        return all_labels
    
    @classmethod
    def get_labels_by_category(cls, category: str) -> Dict[str, Dict[str, Any]]:
        """
        根据分类获取标签
        
        Args:
            category: 标签分类
            
        Returns:
            Dict[str, Dict[str, Any]]: 该分类下的标签定义
        """
        all_labels = cls.get_all_labels()
        return {label_id: label_def for label_id, label_def in all_labels.items() 
                if label_def.get('category') == category}
    
    @classmethod
    def get_label_by_id(cls, label_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取标签定义
        
        Args:
            label_id: 标签ID
            
        Returns:
            Dict[str, Any]: 标签定义，如果不存在返回None
        """
        all_labels = cls.get_all_labels()
        return all_labels.get(label_id)
    
    @classmethod
    def get_categories(cls) -> Dict[str, str]:
        """
        获取所有分类定义
        
        Returns:
            Dict[str, str]: 分类ID到名称的映射
        """
        return cls.CATEGORIES.copy()
    
    @classmethod
    def validate_label_id(cls, label_id: str) -> bool:
        """
        验证标签ID是否有效
        
        Args:
            label_id: 标签ID
            
        Returns:
            bool: 是否有效
        """
        return cls.get_label_by_id(label_id) is not None
    
    @classmethod
    def get_label_mapping_info(cls) -> Dict[str, Any]:
        """
        获取标签映射的统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        all_labels = cls.get_all_labels()
        
        # 按分类统计
        category_stats = {}
        for category_id, category_name in cls.CATEGORIES.items():
            category_labels = cls.get_labels_by_category(category_id)
            category_stats[category_id] = {
                'name': category_name,
                'count': len(category_labels),
                'labels': list(category_labels.keys())
            }
        
        return {
            'total_labels': len(all_labels),
            'total_categories': len(cls.CATEGORIES),
            'category_stats': category_stats,
            'all_labels': list(all_labels.keys())
        }
