#!/usr/bin/env python3
"""
Opportunity Model - 投资机会模型

职责：
- 表示投资机会
- Scanner 阶段：记录触发信息
- Simulator 阶段：记录回测结果
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class Opportunity:
    """
    投资机会（唯一核心对象）
    
    生命周期：
    1. Scanner 创建 -> status = 'active'
    2. Simulator 更新 -> status = 'closed'
    """
    
    # ===== 基本信息 =====
    opportunity_id: str              # 机会唯一ID（UUID）
    stock_id: str                    # 股票代码
    stock_name: str                  # 股票名称
    strategy_name: str               # 策略名称
    strategy_version: str            # 策略版本
    
    # ===== Scanner 阶段字段 =====
    scan_date: str                   # 扫描日期（YYYYMMDD）
    trigger_date: str                # 触发日期（买入信号日期）
    trigger_price: float             # 触发价格（买入价格）
    trigger_conditions: Dict[str, Any]  # 触发条件（JSON）
    expected_return: Optional[float] = None  # 预期收益率
    confidence: Optional[float] = None       # 置信度（0-1）
    
    # ===== Simulator 阶段字段 =====
    sell_date: Optional[str] = None          # 卖出日期
    sell_price: Optional[float] = None       # 卖出价格
    sell_reason: Optional[str] = None        # 卖出原因（止盈/止损/到期）
    
    # ===== 收益分析（基于价格）=====
    price_return: Optional[float] = None     # 价格收益率 = (sell_price - trigger_price) / trigger_price
    holding_days: Optional[int] = None       # 持有天数
    max_price: Optional[float] = None        # 持有期间最高价
    min_price: Optional[float] = None        # 持有期间最低价
    max_drawdown: Optional[float] = None     # 最大回撤（基于价格）
    
    # ===== 持有期追踪 =====
    tracking: Optional[Dict[str, Any]] = None  # 持有期间的详细追踪数据
        # {
        #   "daily_prices": [10.50, 10.60, ...],
        #   "daily_returns": [0, 0.01, ...],
        #   "max_reached_date": "20251225",
        #   "min_reached_date": "20251222"
        # }
    
    # ===== 状态管理 =====
    status: str = 'active'                   # 状态（active/testing/closed/expired）
    expired_date: Optional[str] = None       # 失效日期
    expired_reason: Optional[str] = None     # 失效原因
    
    # ===== 版本控制 =====
    config_hash: str = ''                    # 策略配置的 hash
    
    # ===== 元数据 =====
    created_at: str = ''                     # 创建时间（ISO 格式）
    updated_at: str = ''                     # 更新时间（ISO 格式）
    metadata: Dict[str, Any] = None          # 其他元数据（JSON）
    
    def __post_init__(self):
        """初始化后处理"""
        if self.metadata is None:
            self.metadata = {}
        
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
    
    # =========================================================================
    # 业务方法
    # =========================================================================
    
    def is_valid(self) -> bool:
        """验证机会是否有效"""
        return self.status == 'active'
    
    def is_closed(self) -> bool:
        """是否已回测完成"""
        return self.status == 'closed'
    
    def calculate_annual_return(self) -> float:
        """
        计算年化收益率
        
        Returns:
            annual_return: 年化收益率（假设 250 个交易日）
        """
        if not self.price_return or not self.holding_days:
            return 0.0
        return self.price_return * (250 / self.holding_days)
    
    # =========================================================================
    # 序列化方法
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转为字典（用于 JSON 存储和多进程传递）
        
        Returns:
            dict: 所有字段的字典
        """
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Opportunity':
        """
        从字典创建（用于反序列化）
        
        Args:
            data: 字典数据
        
        Returns:
            Opportunity: 实例
        """
        return cls(**data)
