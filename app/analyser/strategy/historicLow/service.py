#!/usr/bin/env python3
"""
历史低点策略服务类
提供策略相关的工具方法和数据处理
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger


class HistoricLowService:
    """历史低点策略服务类"""
    
    def __init__(self):
        pass
    
    def analyze_meta(self, meta_of_today: Optional[Dict[str, Any]]) -> Tuple[bool, bool]:
        """
        分析元数据
        
        Args:
            meta_of_today: 今天的元数据
            
        Returns:
            Tuple[bool, bool]: (has_cache, should_simulate)
        """
        if not meta_of_today:
            return False, True
        
        date_of_today = meta_of_today.get('date_of_today', '')
        last_opportunity_update_time = meta_of_today.get('last_opportunity_update_time', '')
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 检查是否有缓存
        has_cache = date_of_today == today
        
        # 检查是否需要模拟
        should_simulate = self._should_simulate(meta_of_today)
        
        return has_cache, should_simulate
    
    def parse_cache(self, strategy_meta: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        解析缓存数据
        
        Args:
            strategy_meta: 策略元数据列表
            
        Returns:
            List[Dict[str, Any]]: 解析后的机会列表
        """
        if not strategy_meta:
            return []
        
        meta_of_today = strategy_meta[0]
        last_suggested_stock_codes = meta_of_today.get('last_suggested_stock_codes', '')
        
        if not last_suggested_stock_codes:
            return []
        
        opportunities = []
        cache_strings = last_suggested_stock_codes.split('$|$')
        
        for cache_string in cache_strings:
            if not cache_string:
                continue
            
            try:
                # 解析缓存字符串
                cache_data = self._parse_cache_string(cache_string)
                if cache_data:
                    opportunities.append(cache_data)
            except Exception as e:
                logger.error(f"解析缓存字符串时出错: {e}")
                continue
        
        return opportunities
    
    def _should_simulate(self, meta_of_today: Dict[str, Any]) -> bool:
        """
        判断是否需要模拟
        
        Args:
            meta_of_today: 今天的元数据
            
        Returns:
            bool: 是否需要模拟
        """
        if not meta_of_today:
            return True
        
        # 检查是否在模拟期间
        today = datetime.now()
        last_simulate_date = meta_of_today.get('last_simulate_date', '')
        
        if not last_simulate_date:
            return True
        
        try:
            last_date = datetime.strptime(last_simulate_date, '%Y-%m-%d')
            days_diff = (today - last_date).days
            
            # 如果超过7天没有模拟，则需要模拟
            return days_diff > 7
        except Exception as e:
            logger.error(f"解析模拟日期时出错: {e}")
            return True
    
    def _parse_cache_string(self, cache_string: str) -> Optional[Dict[str, Any]]:
        """
        解析缓存字符串
        
        Args:
            cache_string: 缓存字符串
            
        Returns:
            Optional[Dict[str, Any]]: 解析后的数据
        """
        try:
            # 这里需要根据实际的缓存格式进行解析
            # 示例格式：{"c":"000001","m":"SZ","n":"平安银行","b":10.5,"w":15.75,"l":8.4,"hl":9.8,"hd":"20250701","ht":60}
            import json
            cache_data = json.loads(cache_string)
            
            return {
                'stock': {
                    'code': cache_data.get('c', ''),
                    'market': cache_data.get('m', ''),
                    'name': cache_data.get('n', '')
                },
                'goal': {
                    'suggesting_purchase_price': cache_data.get('b', 0),
                    'win': cache_data.get('w', 0),
                    'loss': cache_data.get('l', 0)
                },
                'ref': {
                    'lowest_price': cache_data.get('hl', 0),
                    'date_time': cache_data.get('hd', ''),
                    'last_for_months': cache_data.get('ht', 0)
                }
            }
        except Exception as e:
            logger.error(f"解析缓存字符串失败: {cache_string}, 错误: {e}")
            return None
    
    @staticmethod
    def get_k_lines_before_date(date: str, lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取指定日期之前的K线数据
        
        Args:
            date: 日期字符串 (YYYY-MM-DD)
            lines: K线数据列表
            
        Returns:
            Dict[str, Any]: 包含结果和当天记录的字典
        """
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d')
            results = []
            record_of_today = None
            
            for line in lines:
                line_date = datetime.strptime(line['date'], '%Y-%m-%d')
                
                if line_date < target_date:
                    results.append(line)
                elif line_date == target_date:
                    record_of_today = line
                    break
            
            return {
                'results': results,
                'record_of_today': record_of_today
            }
        except Exception as e:
            logger.error(f"获取K线数据时出错: {e}")
            return {'results': [], 'record_of_today': None}
    
    @staticmethod
    def is_win(record: Dict[str, Any], win_price_threshold: float) -> bool:
        """
        判断是否盈利
        
        Args:
            record: K线记录
            win_price_threshold: 盈利价格阈值
            
        Returns:
            bool: 是否盈利
        """
        return record.get('highest', 0) > win_price_threshold
    
    @staticmethod
    def is_loss(record: Dict[str, Any], loss_price_threshold: float) -> bool:
        """
        判断是否亏损
        
        Args:
            record: K线记录
            loss_price_threshold: 亏损价格阈值
            
        Returns:
            bool: 是否亏损
        """
        return record.get('lowest', 0) < loss_price_threshold
    
    @staticmethod
    def to_percent(num: float, total: float, digit: int = 2) -> str:
        """
        转换为百分比
        
        Args:
            num: 分子
            total: 分母
            digit: 小数位数
            
        Returns:
            str: 百分比字符串
        """
        if total == 0:
            return f"{0:.{digit}f}%"
        return f"{(num * 100 / total):.{digit}f}%"
    
    @staticmethod
    def decimal_to_percent(decimal: float, digit: int = 2) -> str:
        """
        小数转百分比
        
        Args:
            decimal: 小数
            digit: 小数位数
            
        Returns:
            str: 百分比字符串
        """
        return f"{(decimal * 100):.{digit}f}%"
    
    @staticmethod
    def percent_to_decimal(percent: str) -> float:
        """
        百分比转小数
        
        Args:
            percent: 百分比字符串
            
        Returns:
            float: 小数
        """
        return float(percent.replace('%', '')) / 100
    
    @staticmethod
    def get_rate(samples: List[Dict[str, Any]], prop: str, win_enum: str = 'win') -> float:
        """
        获取比率
        
        Args:
            samples: 样本列表
            prop: 属性名
            win_enum: 胜利枚举值
            
        Returns:
            float: 比率
        """
        if not samples:
            return 0
        
        total_wins = sum(1 for sample in samples if sample.get(prop) == win_enum)
        return total_wins / len(samples)
    
    @staticmethod
    def get_annually_return(roi: float, days: int) -> float:
        """
        计算年化收益率
        
        Args:
            roi: 投资回报率
            days: 天数
            
        Returns:
            float: 年化收益率
        """
        if days <= 0:
            return 0
        return (pow(1 + roi / 100, 365 / days) - 1) * 100
    
    @staticmethod
    def get_monthly_return(roi: float, days: int) -> float:
        """
        计算月化收益率
        
        Args:
            roi: 投资回报率
            days: 天数
            
        Returns:
            float: 月化收益率
        """
        if days <= 0:
            return 0
        return (pow(1 + roi / 100, 30 / days) - 1) * 100
    
    @staticmethod
    def log(message: str, level: int = 1) -> None:
        """
        日志输出
        
        Args:
            message: 消息
            level: 级别
        """
        if level == 1:
            logger.info("=" * 50)
            logger.info(message)
            logger.info("=" * 50)
        elif level == 2:
            logger.info(f"---------------> {message} <---------------")
        elif level == 3:
            logger.info(message)
    
    @staticmethod
    def log_start(job_name: str) -> None:
        """记录开始日志"""
        logger.info(f"---------------> {job_name} started. <---------------")
    
    @staticmethod
    def log_end(job_name: str, level: int = 1) -> None:
        """记录结束日志"""
        logger.info(f"---------------> {job_name} ended. <---------------")
    
    @staticmethod
    def is_in_trading_period(date_of_today: str, period: Dict[str, str] = None) -> bool:
        """
        判断是否在交易期间
        
        Args:
            date_of_today: 今天的日期
            period: 期间设置
            
        Returns:
            bool: 是否在交易期间
        """
        if not period:
            return True
        
        start_date = period.get('start', '')
        end_date = period.get('end', '')
        
        if not start_date or not end_date:
            return True
        
        try:
            today = datetime.strptime(date_of_today, '%Y-%m-%d')
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            
            return start <= today <= end
        except Exception as e:
            logger.error(f"判断交易期间时出错: {e}")
            return True
    
    @staticmethod
    def is_in_simulate_period(date_of_today: str, period: Dict[str, str]) -> bool:
        """
        判断是否在模拟期间
        
        Args:
            date_of_today: 今天的日期
            period: 期间设置
            
        Returns:
            bool: 是否在模拟期间
        """
        return HistoricLowService.is_in_trading_period(date_of_today, period)
    
    @staticmethod
    def has_first_record(date_of_today: str, first_record: str) -> bool:
        """
        判断是否有第一条记录
        
        Args:
            date_of_today: 今天的日期
            first_record: 第一条记录日期
            
        Returns:
            bool: 是否有第一条记录
        """
        if not first_record:
            return False
        
        try:
            today = datetime.strptime(date_of_today, '%Y-%m-%d')
            first = datetime.strptime(first_record, '%Y-%m-%d')
            
            return today >= first
        except Exception as e:
            logger.error(f"判断第一条记录时出错: {e}")
            return False
    
    @staticmethod
    def find_ongoing_opportunity(code: str, on_goings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        查找进行中的机会
        
        Args:
            code: 股票代码
            on_goings: 进行中的机会字典
            
        Returns:
            Optional[Dict[str, Any]]: 进行中的机会
        """
        return on_goings.get(code)
    
    @staticmethod
    def has_reached_min_required_records(records: List[Dict[str, Any]], record_amount_threshold: int) -> bool:
        """
        判断是否达到最小必需记录数
        
        Args:
            records: 记录列表
            record_amount_threshold: 记录数量阈值
            
        Returns:
            bool: 是否达到最小必需记录数
        """
        return len(records) >= record_amount_threshold
    
    @staticmethod
    def check_opportunity_completion(record_of_today: Dict[str, Any], opportunity: Dict[str, Any], status_const: Dict[str, str]) -> str:
        """
        检查机会完成状态
        
        Args:
            record_of_today: 今天的记录
            opportunity: 机会
            status_const: 状态常量
            
        Returns:
            str: 状态
        """
        goal = opportunity.get('goal', {})
        win_price = goal.get('win', 0)
        loss_price = goal.get('loss', 0)
        
        if HistoricLowService.is_win(record_of_today, win_price):
            return status_const.get('WIN', 'win')
        elif HistoricLowService.is_loss(record_of_today, loss_price):
            return status_const.get('LOSS', 'loss')
        else:
            return status_const.get('OPEN', 'open')
    
    @staticmethod
    def check_investment_completion(record_of_today: Dict[str, Any], investment: Dict[str, Any], status_const: Dict[str, str]) -> str:
        """
        检查投资完成状态
        
        Args:
            record_of_today: 今天的记录
            investment: 投资
            status_const: 状态常量
            
        Returns:
            str: 状态
        """
        return HistoricLowService.check_opportunity_completion(record_of_today, investment, status_const)
    
    @staticmethod
    def record_opportunity_result(opportunity: Dict[str, Any], exit_price: float, exit_date: str, exit_extreme_price: float) -> Dict[str, Any]:
        """
        记录机会结果
        
        Args:
            opportunity: 机会
            exit_price: 退出价格
            exit_date: 退出日期
            exit_extreme_price: 退出极端价格
            
        Returns:
            Dict[str, Any]: 结果记录
        """
        goal = opportunity.get('goal', {})
        purchase_price = goal.get('suggesting_purchase_price', 0)
        
        roi = (exit_price - purchase_price) / purchase_price * 100
        
        return {
            'opportunity': opportunity,
            'exit_price': exit_price,
            'exit_date': exit_date,
            'exit_extreme_price': exit_extreme_price,
            'roi': roi
        }
    
    @staticmethod
    def find_ongoing_investment(stock: Dict[str, Any], tracker: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        查找进行中的投资
        
        Args:
            stock: 股票信息
            tracker: 跟踪器
            
        Returns:
            Optional[Dict[str, Any]]: 进行中的投资
        """
        on_going = tracker.get('on_going', {})
        stock_key = f"{stock['code']}.{stock['market']}"
        return on_going.get(stock_key)
    
    @staticmethod
    def get_purchase_size(trade_history: List[Dict[str, Any]], price: float, invest_settings: Dict[str, Any], status_const: Dict[str, str]) -> int:
        """
        获取购买数量
        
        Args:
            trade_history: 交易历史
            price: 价格
            invest_settings: 投资设置
            status_const: 状态常量
            
        Returns:
            int: 购买数量
        """
        # 这里需要根据具体的投资逻辑计算购买数量
        # 暂时返回默认值
        return invest_settings.get('min_purchase_size', 100) 