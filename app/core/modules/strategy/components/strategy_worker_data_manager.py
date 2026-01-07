#!/usr/bin/env python3
"""
Strategy Worker Data Manager - 策略数据管理器

职责：
- 加载当前股票的 K-line、财务等数据
- 提供数据访问接口
- 数据生命周期：仅存在于当前 Worker 实例中

重要：不缓存股票级别的数据！
- ✅ 全局缓存（在 StrategyManager 中）：stock_list, GDP, LPR 等宏观数据
- ❌ 不缓存股票数据：K线、财务数据等（内存占用大）
- 📝 当前股票数据存储在 Worker 实例中，Worker 销毁时自动清理

类比 TagWorkerDataManager
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class StrategyWorkerDataManager:
    """
    策略数据管理器（Worker 级别）
    
    重要说明：
    - 此类只管理【当前股票】的数据
    - 数据存储在 Worker 实例中，不是全局缓存
    - Worker 执行完毕后，实例销毁，数据自动清理
    - 通过限制 Worker 数量控制内存使用
    """
    
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
        
        # 当前股票的数据存储（NOT 缓存！）
        # 生命周期：仅在当前 Worker 实例存活期间
        # Worker 销毁时，这些数据自动被垃圾回收
        self._current_data = {
            'klines': [],
            # 其他数据类型...
        }
        
        # 游标状态（用于 Simulator 逐日遍历）
        # 存储各类数据的游标位置和累积数据
        # 格式：{ 'klines': {'cursor': int, 'acc': list}, 'tags': {'cursor': int, 'acc': list}, ... }
        self._cursor_state = {}
    
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
        self._current_data['klines'] = klines
        
        logger.debug(f"加载最新数据: stock={self.stock_id}, term={term}, "
                    f"records={len(klines)}, date_range={start_date}-{latest_date}")
        
        # 5. 加载其他依赖数据（也是临时存储，不缓存）
        for entity_config in self.settings.required_entities:
            entity_type = entity_config.get('type') if isinstance(entity_config, dict) else entity_config
            data = self._load_entity(entity_config, start_date, latest_date)
            self._current_data[entity_type] = data
    
    # =========================================================================
    # Simulator 数据加载
    # =========================================================================
    
    def load_historical_data(self, start_date: str, end_date: str):
        """
        加载历史数据（Simulator 使用）
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
        
        流程：
        1. 加载全量 K-line（从 start_date 到 end_date）
        2. 加载其他全量数据
        3. 初始化游标状态
        
        注意：这里加载全量数据，后续通过游标逐日过滤
        """
        # 1. 加载全量 K-line
        term = self._extract_term_from_kline_base(self.settings.base_kline_type)
        adjust = self.settings.adjust_type
        
        klines = self._load_klines(start_date, end_date, term, adjust)
        self._current_data['klines'] = klines
        
        logger.debug(f"加载历史数据: stock={self.stock_id}, term={term}, "
                    f"records={len(klines)}, date_range={start_date}-{end_date}")
        
        # 2. 加载其他依赖数据（全量）
        for entity_config in self.settings.required_entities:
            entity_type = entity_config.get('type') if isinstance(entity_config, dict) else entity_config
            data = self._load_entity(entity_config, start_date, end_date)
            self._current_data[entity_type] = data
        
        # 3. 初始化游标状态
        self._init_cursor_state()
    
    # =========================================================================
    # 数据访问接口
    # =========================================================================
    
    def get_klines(self) -> List[Dict[str, Any]]:
        """
        获取当前股票的 K-line 数据
        
        注意：这不是缓存，只是当前 Worker 实例的临时数据
        
        Returns:
            klines: [
                {'date': '20251219', 'open': 10.0, 'close': 10.5, ...},
                ...
            ]
        """
        return self._current_data.get('klines', [])
    
    def get_entity_data(self, entity_type: str) -> List[Dict[str, Any]]:
        """
        获取当前股票的其他实体数据
        
        注意：这不是缓存，只是当前 Worker 实例的临时数据
        
        Args:
            entity_type: 数据类型（如 'corporate_finance'）
        
        Returns:
            data: [...]
        """
        return self._current_data.get(entity_type, [])
    
    # =========================================================================
    # 游标机制（Simulator 逐日遍历使用）
    # =========================================================================
    
    def get_data_until(self, date_of_today: str) -> Dict[str, Any]:
        """
        使用游标获取指定日期（含）之前的所有数据
        
        核心思想（参考 legacy）:
        - 维护每类数据的游标位置（cursor）和累积数据（acc）
        - 每次调用只 append 新增的数据，不重新切片
        - 大幅提高效率，避免重复复制
        
        Args:
            date_of_today: 当前虚拟日期（YYYYMMDD）
        
        Returns:
            data_of_today: {
                'klines': [...],
                'tags': [...],
                'corporate_finance': [...],
                ...
            }
        """
        result = {}
        
        # 1. 处理 K线 数据
        klines_state = self._cursor_state.get('klines')
        if klines_state:
            self._advance_cursor_until(
                data_list=self._current_data['klines'],
                state=klines_state,
                date_of_today=date_of_today,
                date_field='date'
            )
            result['klines'] = klines_state['acc']
        
        # 2. 处理其他数据类型
        for entity_type in self._current_data.keys():
            if entity_type == 'klines':
                continue
            
            state = self._cursor_state.get(entity_type)
            if state:
                # 判断日期字段（财务数据用 quarter，其他用 date）
                date_field = 'quarter' if 'finance' in entity_type.lower() else 'date'
                
                self._advance_cursor_until(
                    data_list=self._current_data[entity_type],
                    state=state,
                    date_of_today=date_of_today,
                    date_field=date_field
                )
                result[entity_type] = state['acc']
        
        return result
    
    def _init_cursor_state(self):
        """
        初始化游标状态
        
        为每类数据创建：{'cursor': -1, 'acc': []}
        """
        self._cursor_state = {}
        
        # 初始化 K线 游标
        if 'klines' in self._current_data:
            self._cursor_state['klines'] = {'cursor': -1, 'acc': []}
        
        # 初始化其他数据类型的游标
        for entity_type in self._current_data.keys():
            if entity_type != 'klines':
                self._cursor_state[entity_type] = {'cursor': -1, 'acc': []}
        
        logger.debug(f"初始化游标状态: stock={self.stock_id}, types={list(self._cursor_state.keys())}")
    
    def _advance_cursor_until(
        self, 
        data_list: List[Dict[str, Any]], 
        state: Dict[str, Any], 
        date_of_today: str,
        date_field: str = 'date'
    ):
        """
        推进游标直到指定日期（含）
        
        Args:
            data_list: 全量数据列表
            state: 游标状态 {'cursor': int, 'acc': list}
            date_of_today: 当前日期
            date_field: 日期字段名（'date' 或 'quarter'）
        """
        cursor = state['cursor']
        acc = state['acc']
        
        i = cursor + 1
        n = len(data_list)
        
        while i < n:
            record = data_list[i]
            record_date = record.get(date_field)
            
            # 如果记录日期为空或超过今天，停止
            if not record_date or record_date > date_of_today:
                break
            
            # 追加到累积数据
            acc.append(record)
            i += 1
        
        # 更新游标位置
        state['cursor'] = i - 1
    
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
