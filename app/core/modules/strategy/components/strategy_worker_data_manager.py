#!/usr/bin/env python3
"""
Strategy Worker Data Manager - 策略数据管理器

职责：
- 加载 K-line、财务等数据
- 缓存数据（避免重复加载）
- 按日期过滤数据

类比 TagWorkerDataManager
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class StrategyWorkerDataManager:
    """策略数据管理器（类比 TagWorkerDataManager）"""
    
    def __init__(self, stock_id: str, settings: 'StrategySettings', data_mgr: 'DataManager'):
        """
        初始化数据管理器
        
        Args:
            stock_id: 股票代码
            settings: 策略配置
            data_mgr: DataManager 实例
        """
        self.stock_id = stock_id
        self.settings = settings
        self.data_mgr = data_mgr
        
        # 数据缓存
        self.data_cache = {
            'klines': [],
            # 其他数据类型...
        }
    
    # =========================================================================
    # Scanner 数据加载
    # =========================================================================
    
    def load_latest_data(self, lookback: int = None):
        """
        加载最新数据（Scanner 使用）
        
        Args:
            lookback: 历史窗口天数（如果不指定，使用 settings 中的配置）
        
        流程：
        1. 获取最新交易日
        2. 计算开始日期（latest_date - lookback）
        3. 加载 K-line
        4. 加载其他数据（根据 settings.required_entities）
        """
        # 1. 确定 lookback
        if lookback is None:
            lookback = self.settings.min_required_records or 1000
        
        # 2. 获取最新交易日
        latest_date = self._get_latest_trading_date()
        
        # 3. 计算开始日期（使用 lookback 天数）
        start_date = self._get_date_before(latest_date, lookback)
        
        # 4. 加载 K-line
        term = self._extract_term_from_kline_base(self.settings.base_kline_type)
        adjust = self.settings.adjust_type
        
        klines = self._load_klines(start_date, latest_date, term, adjust)
        self.data_cache['klines'] = klines
        
        logger.debug(f"加载最新数据: stock={self.stock_id}, term={term}, "
                    f"records={len(klines)}, date_range={start_date}-{latest_date}")
        
        # 5. 加载其他依赖数据
        for entity_config in self.settings.required_entities:
            entity_type = entity_config.get('type') if isinstance(entity_config, dict) else entity_config
            data = self._load_entity(entity_config, start_date, latest_date)
            self.data_cache[entity_type] = data
    
    # =========================================================================
    # Simulator 数据加载
    # =========================================================================
    
    def load_historical_data(self, start_date: str, end_date: str):
        """
        加载历史数据（Simulator 使用）
        
        Args:
            start_date: 开始日期（trigger_date）
            end_date: 结束日期
        
        流程：
        1. 加载 K-line（从 start_date 到 end_date）
        2. 加载其他数据
        """
        # 1. 加载 K-line
        term = self._extract_term_from_kline_base(self.settings.base_kline_type)
        adjust = self.settings.adjust_type
        
        klines = self._load_klines(start_date, end_date, term, adjust)
        self.data_cache['klines'] = klines
        
        logger.debug(f"加载历史数据: stock={self.stock_id}, term={term}, "
                    f"records={len(klines)}, date_range={start_date}-{end_date}")
        
        # 2. 加载其他依赖数据
        for entity_config in self.settings.required_entities:
            entity_type = entity_config.get('type') if isinstance(entity_config, dict) else entity_config
            data = self._load_entity(entity_config, start_date, end_date)
            self.data_cache[entity_type] = data
    
    # =========================================================================
    # 数据访问接口
    # =========================================================================
    
    def get_klines(self) -> List[Dict[str, Any]]:
        """
        获取 K-line 数据
        
        Returns:
            klines: [
                {'date': '20251219', 'open': 10.0, 'close': 10.5, ...},
                ...
            ]
        """
        return self.data_cache.get('klines', [])
    
    def get_entity_data(self, entity_type: str) -> List[Dict[str, Any]]:
        """
        获取其他实体数据
        
        Args:
            entity_type: 数据类型（如 'corporate_finance'）
        
        Returns:
            data: [...]
        """
        return self.data_cache.get(entity_type, [])
    
    # =========================================================================
    # 私有方法
    # =========================================================================
    
    def _load_klines(
        self, 
        start_date: str, 
        end_date: str, 
        term: str,
        adjust: str = 'qfq'
    ) -> List[Dict[str, Any]]:
        """
        加载 K-line 数据（使用 DataManager API）
        
        Args:
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            term: 周期（daily/weekly/monthly）
            adjust: 复权方式（qfq/hfq/none）
        
        Returns:
            klines: [{'date': '20251219', 'open': 10.0, 'close': 10.5, ...}, ...]
        """
        try:
            # 使用 DataManager 的统一加载接口
            klines = self.data_mgr.load_klines(
                stock_id=self.stock_id,
                term=term,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
                filter_negative=True,
                as_dataframe=False  # 返回 List[Dict]
            )
            
            return klines if klines else []
        
        except Exception as e:
            logger.error(f"加载K线数据失败: stock={self.stock_id}, term={term}, "
                        f"date_range={start_date}-{end_date}, error={e}")
            return []
    
    def _load_entity(
        self, 
        entity_config: Any, 
        start_date: str, 
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        加载其他实体数据
        
        Args:
            entity_config: 实体配置（字典或字符串）
                - 如果是字典：{'type': 'xxx', 'name': 'xxx', ...}
                - 如果是字符串：'xxx'
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            data: [...]
        """
        try:
            # 解析配置
            if isinstance(entity_config, dict):
                entity_type = entity_config.get('type')
                entity_name = entity_config.get('name')
            else:
                entity_type = entity_config
                entity_name = None
            
            # 根据 entity_type 加载不同的数据
            if 'tag' in entity_type.lower():
                # 加载 Tag 数据
                return self._load_tag_data(entity_name, start_date, end_date)
            
            elif 'corporate_finance' in entity_type.lower():
                # 加载财务数据
                return self._load_finance_data(start_date, end_date)
            
            elif 'gdp' in entity_type.lower():
                # 加载宏观数据
                return self._load_macro_data('gdp', start_date, end_date)
            
            else:
                logger.warning(f"未知的实体类型: {entity_type}")
                return []
        
        except Exception as e:
            logger.error(f"加载实体数据失败: type={entity_config}, error={e}")
            return []
    
    def _load_tag_data(self, tag_name: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """加载 Tag 数据"""
        try:
            tag_model = self.data_mgr.get_model('tag_value')
            if not tag_model:
                return []
            
            data = tag_model.load(
                condition="stock_id = %s AND scenario_name = %s AND date >= %s AND date <= %s",
                params=(self.stock_id, tag_name, start_date, end_date),
                order_by="date ASC"
            )
            return data if data else []
        
        except Exception as e:
            logger.error(f"加载Tag数据失败: tag={tag_name}, error={e}")
            return []
    
    def _load_finance_data(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """加载财务数据"""
        try:
            finance_model = self.data_mgr.get_model('corporate_finance')
            if not finance_model:
                return []
            
            data = finance_model.load(
                condition="id = %s AND report_date >= %s AND report_date <= %s",
                params=(self.stock_id, start_date, end_date),
                order_by="report_date ASC"
            )
            return data if data else []
        
        except Exception as e:
            logger.error(f"加载财务数据失败: error={e}")
            return []
    
    def _load_macro_data(self, macro_type: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """加载宏观数据"""
        try:
            macro_model = self.data_mgr.get_model(macro_type)
            if not macro_model:
                return []
            
            data = macro_model.load(
                condition="date >= %s AND date <= %s",
                params=(start_date, end_date),
                order_by="date ASC"
            )
            return data if data else []
        
        except Exception as e:
            logger.error(f"加载宏观数据失败: type={macro_type}, error={e}")
            return []
    
    def _get_latest_trading_date(self) -> str:
        """
        获取最新交易日
        
        Returns:
            latest_date: 最新交易日（YYYYMMDD）
        """
        try:
            # 尝试获取最新K线数据
            stock_service = self.data_mgr.get_data_service('stock_related.stock')
            if stock_service:
                latest_kline = stock_service.load_latest_kline(self.stock_id)
                if latest_kline:
                    return latest_kline['date']
            
            # 如果没有数据，返回当前日期
            logger.warning(f"无法获取最新交易日，使用当前日期: stock={self.stock_id}")
            return datetime.now().strftime('%Y%m%d')
        
        except Exception as e:
            logger.error(f"获取最新交易日失败: stock={self.stock_id}, error={e}")
            return datetime.now().strftime('%Y%m%d')
    
    def _get_date_before(self, date: str, days: int) -> str:
        """
        获取 N 天前的日期（自然日，简化版）
        
        Note: 这里使用自然日计算，确保获取足够的数据
              实际加载时会自动过滤非交易日
        
        Args:
            date: 基准日期（YYYYMMDD）
            days: 天数
        
        Returns:
            earlier_date: N 天前的日期（YYYYMMDD）
        """
        try:
            dt = datetime.strptime(date, '%Y%m%d')
            # 使用自然日 * 1.5 倍，确保有足够的交易日数据
            dt_before = dt - timedelta(days=int(days * 1.5))
            return dt_before.strftime('%Y%m%d')
        
        except Exception as e:
            logger.error(f"计算日期失败: date={date}, days={days}, error={e}")
            return date
    
    def _extract_term_from_kline_base(self, base_kline_type: str) -> str:
        """
        从 base_kline_type 提取周期
        
        Args:
            base_kline_type: 如 'stock_kline_daily' 或 EntityType.STOCK_KLINE_DAILY.value
        
        Returns:
            term: 'daily' or 'weekly' or 'monthly'
        """
        base_str = str(base_kline_type).lower()
        
        if 'daily' in base_str:
            return 'daily'
        elif 'weekly' in base_str:
            return 'weekly'
        elif 'monthly' in base_str:
            return 'monthly'
        
        # 默认返回 daily
        logger.warning(f"无法识别K线周期，使用默认值 daily: {base_kline_type}")
        return 'daily'
