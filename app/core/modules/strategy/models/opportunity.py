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
    
    用户创建时只需要提供：
    - stock: Dict[str, Any] - 股票信息（包含 id, name 等）
    - record_of_today: Dict[str, Any] - 当天的K线记录（包含 date, close 等）
    - extra_fields: Optional[Dict[str, Any]] - 策略特定的额外信息（可选）
    
    框架会自动填充：
    - opportunity_id, strategy_name, strategy_version, scan_date, status 等
    
    生命周期：
    1. Scanner 创建 -> status = 'active'
    2. Simulator 更新 -> status = 'closed'
    """
    
    # ===== 用户提供的核心字段 =====
    stock: Dict[str, Any]            # 股票信息（legacy 兼容）
    record_of_today: Dict[str, Any]   # 当天的K线记录（legacy 兼容）
    extra_fields: Optional[Dict[str, Any]] = None  # 策略特定的额外信息
    
    # ===== 框架自动填充的字段（用户不需要关心）=====
    opportunity_id: str = ''         # 机会唯一ID（UUID，框架自动生成）
    stock_id: str = ''               # 股票代码（从 stock['id'] 提取）
    stock_name: str = ''             # 股票名称（从 stock['name'] 提取）
    strategy_name: str = ''          # 策略名称（框架自动填充）
    strategy_version: str = ''       # 策略版本（框架自动填充）
    scan_date: str = ''              # 扫描日期（框架自动填充）
    trigger_date: str = ''           # 触发日期（从 record_of_today['date'] 提取）
    trigger_price: float = 0.0       # 触发价格（从 record_of_today['close'] 提取）
    
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
    
    # ===== 止盈止损追踪状态（Simulator 内部使用）=====
    protect_loss_active: bool = False        # 保本止损是否激活
    dynamic_loss_active: bool = False        # 动态止损是否激活
    dynamic_loss_highest: Optional[float] = None  # 动态止损的最高点
    triggered_stop_loss_idx: int = -1        # 已触发的止损阶段索引
    triggered_take_profit_idx: int = -1      # 已触发的止盈阶段索引
    roi: Optional[float] = None              # 收益率（price_return 的别名）
    
    # ===== OpportunityEnumerator 专用字段 =====
    completed_targets: Optional[list] = None  # 完成的目标列表（枚举器使用）
        # [
        #   {
        #     "date": "20230115",
        #     "price": 11.0,
        #     "reason": "take_profit_stage1",
        #     "roi": 0.10
        #   }
        # ]
    
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
        # 如果 stock 是 None 或空，尝试从 stock_id 自动加载（延迟加载，避免循环依赖）
        # 注意：这里不自动加载，因为需要 DataManager，应该在 Worker 中提前加载
        
        # 从 stock 和 record_of_today 提取字段（如果用户没有提供）
        if not self.stock_id and self.stock:
            self.stock_id = self.stock.get('id', '')
        if not self.stock_name and self.stock:
            self.stock_name = self.stock.get('name', '')
        if not self.trigger_date and self.record_of_today:
            self.trigger_date = self.record_of_today.get('date', '')
        if not self.trigger_price and self.record_of_today:
            self.trigger_price = self.record_of_today.get('close', 0.0)
        
        # 确保 stock 字典包含完整字段（如果缺少）
        if self.stock:
            # 确保有 id
            if 'id' not in self.stock and self.stock_id:
                self.stock['id'] = self.stock_id
            # 确保有 name
            if 'name' not in self.stock and self.stock_name:
                self.stock['name'] = self.stock_name
            # 确保有 industry, type, exchange_center（如果缺失，设为空字符串）
            if 'industry' not in self.stock:
                self.stock['industry'] = self.stock.get('industry', '')
            if 'type' not in self.stock:
                self.stock['type'] = self.stock.get('type', '')
            if 'exchange_center' not in self.stock:
                self.stock['exchange_center'] = self.stock.get('exchange_center', '')
        
        # 初始化可选字段
        if self.extra_fields is None:
            self.extra_fields = {}
        if self.metadata is None:
            self.metadata = {}
        
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
        
        # 如果没有 opportunity_id，框架会在使用时自动生成（见 enrich_from_framework）
    
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
    # 止盈止损方法（Simulator/Enumerator 使用）
    # =========================================================================
    
    def check_targets(
        self,
        current_kline: Dict[str, Any],
        goal_config: Dict[str, Any]
    ) -> bool:
        """
        检查止盈止损目标
        
        Args:
            current_kline: 当天的 K 线数据
            goal_config: 止盈止损配置
        
        Returns:
            is_completed: 是否完成（触发止盈/止损）
        """
        current_price = current_kline['close']
        current_date = current_kline['date']
        
        # 计算持有天数和收益率
        holding_days = self._calculate_holding_days(self.trigger_date, current_date)
        price_return = (current_price - self.trigger_price) / self.trigger_price
        
        # 更新追踪数据
        self.max_price = max(self.max_price or 0, current_price)
        self.min_price = min(self.min_price or float('inf'), current_price)
        
        # 1. 检查到期平仓
        expiration_config = goal_config.get('expiration', {})
        if expiration_config:
            fixed_period = expiration_config.get('fixed_period', 0)
            if fixed_period > 0 and holding_days >= fixed_period:
                self._settle(current_date, current_price, 'expiration', price_return)
                return True
        
        # 2. 检查保本止损
        if self.protect_loss_active:
            protect_loss_config = goal_config.get('protect_loss', {})
            protect_ratio = protect_loss_config.get('ratio', 0)
            
            if price_return <= protect_ratio:
                self._settle(current_date, current_price, 'protect_loss', price_return)
                return True
        
        # 3. 检查动态止损
        if self.dynamic_loss_active:
            dynamic_loss_config = goal_config.get('dynamic_loss', {})
            dynamic_ratio = dynamic_loss_config.get('ratio', -0.1)
            
            # 更新最高点
            if not self.dynamic_loss_highest:
                self.dynamic_loss_highest = self.trigger_price
            self.dynamic_loss_highest = max(self.dynamic_loss_highest, current_price)
            
            # 检查回撤
            dynamic_threshold = (current_price - self.dynamic_loss_highest) / self.dynamic_loss_highest
            if dynamic_threshold <= dynamic_ratio:
                self._settle(current_date, current_price, 'dynamic_loss', price_return)
                return True
        
        # 4. 检查分段止损
        stop_loss_stages = goal_config.get('stop_loss', {}).get('stages', [])
        for idx, stage in enumerate(stop_loss_stages):
            if idx <= self.triggered_stop_loss_idx:
                continue
            
            stage_ratio = stage.get('ratio', 0)
            if price_return <= stage_ratio:
                # 触发止损
                self.triggered_stop_loss_idx = idx
                
                # 判断是否清仓
                if stage.get('close_invest', False):
                    # reason: 优先使用 stage 的 name，如果没有则使用 ratio 生成
                    stage_name = stage.get('name')
                    if stage_name:
                        reason = stage_name
                    else:
                        ratio_percent = int(stage_ratio * 100)
                        reason = f"stop_loss_{ratio_percent}%"
                    self._settle(current_date, current_price, reason, price_return)
                    return True
        
        # 5. 检查分段止盈
        take_profit_stages = goal_config.get('take_profit', {}).get('stages', [])
        for idx, stage in enumerate(take_profit_stages):
            if idx <= self.triggered_take_profit_idx:
                continue
            
            stage_ratio = stage.get('ratio', 0)
            if price_return >= stage_ratio:
                # 触发止盈
                self.triggered_take_profit_idx = idx
                
                # 执行动作
                actions = stage.get('actions', [])
                if 'set_protect_loss' in actions:
                    self.protect_loss_active = True
                if 'set_dynamic_loss' in actions:
                    self.dynamic_loss_active = True
                    self.dynamic_loss_highest = current_price
                
                # ⭐ 记录止盈目标达成
                # reason: 优先使用 stage 的 name，如果没有则使用 ratio 生成
                stage_name = stage.get('name')
                if stage_name:
                    reason = stage_name
                else:
                    ratio_percent = int(stage_ratio * 100)
                    reason = f"take_profit_{ratio_percent}%"
                
                # 判断是否清仓
                if stage.get('close_invest', False):
                    # 如果清仓，由 _settle 统一记录到 completed_targets
                    self._settle(current_date, current_price, reason, price_return)
                    return True
                else:
                    # 如果不清仓（只有 sell_ratio 或没有 close_invest），记录目标达成但继续持有
                    if not self.completed_targets:
                        self.completed_targets = []
                    self.completed_targets.append({
                        'date': current_date,
                        'price': current_price,
                        'reason': reason,
                        'roi': price_return
                    })
                    # 继续持有，不返回 True
        
        # 未完成，继续持有
        return False
    
    def settle(
        self,
        last_kline: Dict[str, Any],
        reason: str = 'backtest_end'
    ):
        """
        强制结算（回测结束时）
        
        Args:
            last_kline: 最后一个交易日的 K 线
            reason: 结算原因
        """
        current_price = last_kline['close']
        current_date = last_kline['date']
        price_return = (current_price - self.trigger_price) / self.trigger_price
        
        self._settle(current_date, current_price, reason, price_return)
    
    def _settle(
        self,
        sell_date: str,
        sell_price: float,
        sell_reason: str,
        roi: float
    ):
        """
        内部结算方法
        
        Args:
            sell_date: 卖出日期
            sell_price: 卖出价格
            sell_reason: 卖出原因
            roi: 收益率
        """
        self.sell_date = sell_date
        self.sell_price = sell_price
        self.sell_reason = sell_reason
        self.status = 'completed'
        self.roi = roi
        
        # 添加到 completed_targets
        if not self.completed_targets:
            self.completed_targets = []
        
        self.completed_targets.append({
            'date': sell_date,
            'price': sell_price,
            'reason': sell_reason,
            'roi': roi
        })
    
    def _calculate_holding_days(self, start_date: str, end_date: str) -> int:
        """
        计算持有天数
        
        Args:
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
        
        Returns:
            持有天数
        """
        try:
            start = datetime.strptime(start_date, '%Y%m%d')
            end = datetime.strptime(end_date, '%Y%m%d')
            return (end - start).days
        except Exception:
            return 0
    
    # =========================================================================
    # 框架辅助方法
    # =========================================================================
    
    def enrich_from_framework(
        self,
        strategy_name: str,
        strategy_version: str = '1.0',
        opportunity_id: Optional[str] = None
    ):
        """
        框架调用：自动填充框架字段
        
        Args:
            strategy_name: 策略名称
            strategy_version: 策略版本
            opportunity_id: 机会ID（如果不提供，自动生成UUID）
        """
        import uuid
        
        self.strategy_name = strategy_name
        self.strategy_version = strategy_version
        self.scan_date = datetime.now().strftime('%Y%m%d')
        
        if not self.opportunity_id:
            if opportunity_id:
                self.opportunity_id = opportunity_id
            else:
                self.opportunity_id = str(uuid.uuid4())
        
        # 确保从 stock 和 record_of_today 提取的字段已填充
        if not self.stock_id and self.stock:
            self.stock_id = self.stock.get('id', '')
        if not self.stock_name and self.stock:
            self.stock_name = self.stock.get('name', '')
        if not self.trigger_date and self.record_of_today:
            self.trigger_date = self.record_of_today.get('date', '')
        if not self.trigger_price and self.record_of_today:
            self.trigger_price = self.record_of_today.get('close', 0.0)
    
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
