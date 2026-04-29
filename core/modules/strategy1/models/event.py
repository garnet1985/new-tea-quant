#!/usr/bin/env python3
"""
事件模型

定义 Event 数据结构，用于资金分配模拟器的事件流
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Literal, Optional


@dataclass
class Event:
    """事件（trigger 或 target）"""
    event_type: Literal["trigger", "target"]  # 事件类型
    date: str  # YYYYMMDD
    stock_id: str
    opportunity_id: str
    
    # 事件数据
    opportunity: Optional[Dict[str, Any]] = None  # 完整的机会信息（trigger 和 target 都有）
    target: Optional[Dict[str, Any]] = None  # 目标信息（仅 target 事件有）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "event_type": self.event_type,
            "date": self.date,
            "stock_id": self.stock_id,
            "opportunity_id": self.opportunity_id,
        }
        
        if self.opportunity is not None:
            result["opportunity"] = self.opportunity
        
        if self.target is not None:
            result["target"] = self.target
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """从字典创建 Event"""
        return cls(
            event_type=data.get("event_type", "trigger"),
            date=data.get("date", ""),
            stock_id=data.get("stock_id", ""),
            opportunity_id=data.get("opportunity_id", ""),
            opportunity=data.get("opportunity"),
            target=data.get("target"),
        )
    
    def is_trigger(self) -> bool:
        """是否为 trigger 事件"""
        return self.event_type == "trigger"
    
    def is_target(self) -> bool:
        """是否为 target 事件"""
        return self.event_type == "target"
