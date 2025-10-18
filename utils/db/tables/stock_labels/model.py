"""
股票标签表模型定义
"""
from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class StockLabel:
    """股票标签记录"""
    stock_id: str
    label_date: datetime
    labels: str  # 标签ID字符串，用逗号分隔
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def get_label_list(self) -> List[str]:
        """解析标签字符串为标签列表"""
        if not self.labels:
            return []
        return [label.strip() for label in self.labels.split(',') if label.strip()]
    
    def set_label_list(self, label_list: List[str]):
        """设置标签列表为标签字符串"""
        self.labels = ','.join(label_list)
    
    def has_label(self, label_id: str) -> bool:
        """检查是否包含指定标签"""
        return label_id in self.get_label_list()
    
    def add_label(self, label_id: str):
        """添加标签"""
        current_labels = self.get_label_list()
        if label_id not in current_labels:
            current_labels.append(label_id)
            self.set_label_list(current_labels)
    
    def remove_label(self, label_id: str):
        """移除标签"""
        current_labels = self.get_label_list()
        if label_id in current_labels:
            current_labels.remove(label_id)
            self.set_label_list(current_labels)
