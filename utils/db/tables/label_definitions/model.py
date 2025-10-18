"""
标签定义表模型定义
"""
from typing import Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class LabelDefinition:
    """标签定义记录"""
    label_id: str
    label_name: str
    label_category: str
    label_description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'label_id': self.label_id,
            'label_name': self.label_name,
            'label_category': self.label_category,
            'label_description': self.label_description,
            'is_active': self.is_active,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'LabelDefinition':
        """从字典创建实例"""
        return cls(
            label_id=data['label_id'],
            label_name=data['label_name'],
            label_category=data['label_category'],
            label_description=data.get('label_description'),
            is_active=data.get('is_active', True),
            created_at=data.get('created_at')
        )
