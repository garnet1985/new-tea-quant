#!/usr/bin/env python3
"""
标签定义管理

职责：
- 标签定义的初始化和管理
- 标签分类的维护
- 标签元数据的查询
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger
from utils.db.db_manager import DatabaseManager


class LabelDefinitions:
    """
    标签定义管理
    
    职责：
    - 初始化标签定义数据
    - 管理标签分类
    - 提供标签元数据查询
    """
    
    def __init__(self, db: DatabaseManager):
        """
        初始化标签定义管理
        
        Args:
            db: 数据库管理器实例
        """
        self.db = db
        self._definitions = self._load_definitions()
    
    def _load_definitions(self) -> Dict[str, Dict[str, Any]]:
        """
        加载标签定义
        
        Returns:
            Dict: 标签定义字典
        """
        try:
            sql = """
            SELECT label_id, label_name, label_category, label_description, is_active
            FROM label_definitions 
            WHERE is_active = TRUE
            """
            
            result = self.db.execute_query(sql)
            
            definitions = {}
            if result:
                for row in result:
                    definitions[row['label_id']] = {
                        'name': row['label_name'],
                        'category': row['label_category'],
                        'description': row['label_description'],
                        'is_active': row['is_active']
                    }
            
            return definitions
            
        except Exception as e:
            logger.error(f"加载标签定义失败: {e}")
            return {}
    
    def get_definition(self, label_id: str) -> Optional[Dict[str, Any]]:
        """
        获取标签定义
        
        Args:
            label_id: 标签ID
            
        Returns:
            Dict: 标签定义信息
        """
        return self._definitions.get(label_id)
    
    def get_definitions_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        根据分类获取标签定义
        
        Args:
            category: 标签分类
            
        Returns:
            List[Dict]: 标签定义列表
        """
        definitions = []
        for label_id, definition in self._definitions.items():
            if definition['category'] == category:
                definitions.append({
                    'label_id': label_id,
                    **definition
                })
        
        return definitions
    
    def get_labels_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        根据分类获取标签定义（兼容新架构）
        
        Args:
            category: 标签分类
            
        Returns:
            List[Dict]: 标签定义列表
        """
        return self.get_definitions_by_category(category)
    
    def get_all_categories(self) -> List[str]:
        """
        获取所有标签分类
        
        Returns:
            List[str]: 标签分类列表
        """
        categories = set()
        for definition in self._definitions.values():
            categories.add(definition['category'])
        
        return sorted(list(categories))
    
    def initialize_default_definitions(self):
        """
        初始化默认标签定义
        """
        logger.info("开始初始化默认标签定义")
        
        default_definitions = [
            # 市值标签
            ('LARGE_CAP', '大盘股', 'MARKET_CAP', '市值≥100亿'),
            ('MID_CAP', '中盘股', 'MARKET_CAP', '市值30-100亿'),
            ('SMALL_CAP', '小盘股', 'MARKET_CAP', '市值<30亿'),
            
            # 行业标签
            ('GROWTH', '成长股', 'INDUSTRY', '成长性行业，如科技、医药等'),
            ('VALUE', '价值股', 'INDUSTRY', '价值型行业，如银行、保险等'),
            ('CYCLE', '周期股', 'INDUSTRY', '周期性行业，如钢铁、煤炭等'),
            ('DEFENSIVE', '防御股', 'INDUSTRY', '防御性行业，如食品、公用事业等'),
            
            # 波动性标签
            ('HIGH_VOL', '高波动', 'VOLATILITY', '年化波动率>30%'),
            ('MID_VOL', '中波动', 'VOLATILITY', '年化波动率15-30%'),
            ('LOW_VOL', '低波动', 'VOLATILITY', '年化波动率<15%'),
            
            # 成交量标签
            ('HIGH_ACTIVE', '高活跃', 'VOLUME', '日均成交额>5亿'),
            ('MID_ACTIVE', '中活跃', 'VOLUME', '日均成交额1-5亿'),
            ('LOW_ACTIVE', '低活跃', 'VOLUME', '日均成交额<1亿'),
        ]
        
        try:
            # 清空现有定义
            self.db.execute("DELETE FROM label_definitions")
            
            # 插入默认定义
            sql = """
            INSERT INTO label_definitions (label_id, label_name, label_category, label_description, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            current_time = datetime.now()
            for label_id, label_name, label_category, label_description in default_definitions:
                self.db.execute(sql, (label_id, label_name, label_category, label_description, True, current_time))
            
            # 重新加载定义
            self._definitions = self._load_definitions()
            
            logger.info(f"默认标签定义初始化完成: {len(default_definitions)}个标签")
            
        except Exception as e:
            logger.error(f"初始化默认标签定义失败: {e}")
    
    def add_definition(self, label_id: str, label_name: str, label_category: str, 
                      label_description: str = None):
        """
        添加新的标签定义
        
        Args:
            label_id: 标签ID
            label_name: 标签名称
            label_category: 标签分类
            label_description: 标签描述
        """
        try:
            sql = """
            INSERT INTO label_definitions (label_id, label_name, label_category, label_description, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                label_name = %s,
                label_category = %s,
                label_description = %s,
                is_active = %s
            """
            
            current_time = datetime.now()
            self.db.execute(sql, (label_id, label_name, label_category, label_description, True, current_time,
                                label_name, label_category, label_description, True))
            
            # 重新加载定义
            self._definitions = self._load_definitions()
            
            logger.info(f"添加标签定义成功: {label_id}")
            
        except Exception as e:
            logger.error(f"添加标签定义失败: {label_id}, {e}")
    
    def update_definition(self, label_id: str, **kwargs):
        """
        更新标签定义
        
        Args:
            label_id: 标签ID
            **kwargs: 要更新的字段
        """
        try:
            if not kwargs:
                return
            
            set_clauses = []
            values = []
            
            for key, value in kwargs.items():
                if key in ['label_name', 'label_category', 'label_description', 'is_active']:
                    set_clauses.append(f"{key} = %s")
                    values.append(value)
            
            if not set_clauses:
                return
            
            values.append(label_id)
            sql = f"UPDATE label_definitions SET {', '.join(set_clauses)} WHERE label_id = %s"
            
            self.db.execute(sql, values)
            
            # 重新加载定义
            self._definitions = self._load_definitions()
            
            logger.info(f"更新标签定义成功: {label_id}")
            
        except Exception as e:
            logger.error(f"更新标签定义失败: {label_id}, {e}")
    
    def delete_definition(self, label_id: str):
        """
        删除标签定义
        
        Args:
            label_id: 标签ID
        """
        try:
            sql = "DELETE FROM label_definitions WHERE label_id = %s"
            self.db.execute(sql, (label_id,))
            
            # 重新加载定义
            self._definitions = self._load_definitions()
            
            logger.info(f"删除标签定义成功: {label_id}")
            
        except Exception as e:
            logger.error(f"删除标签定义失败: {label_id}, {e}")
