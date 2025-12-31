"""
Worker Data Manager - 子进程数据管理器

职责：
1. 管理数据缓存（按记录数切片加载）
2. 管理切片状态（slice_state）和时间 cursor（time_cursor）
3. 提供数据加载和过滤接口
4. 确保 required_data 与 base entity 时间轴对齐

注意：
- 这是子进程中的数据管理器，在子进程中实例化
- 负责所有数据加载、缓存、过滤逻辑
- BaseTagWorker 通过此管理器获取数据，专注于 tag 计算
"""
from typing import Dict, Any, List, Optional
import logging
from app.data_manager import DataManager

logger = logging.getLogger(__name__)


class WorkerDataManager:
    """
    Worker Data Manager - 子进程数据管理器
    
    职责：
    1. 管理数据缓存（按记录数切片，每次1000条）
    2. 管理切片状态（slice_state）和时间 cursor（time_cursor）
    3. 提供数据加载和过滤接口
    4. 确保 required_data 与 base entity 时间轴对齐
    
    使用方式：
        data_mgr = WorkerDataManager(
            entity_id='000001.SZ',
            entity_type='stock',
            base_term='daily',
            required_terms=['weekly'],
            required_data=['corporate_finance'],
            data_slice_size=1000
        )
        
        # 确保数据已加载
        data_mgr.ensure_data_loaded(as_of_date='20240101')
        
        # 过滤数据到指定日期
        filtered_data = data_mgr.filter_data_to_date(as_of_date='20240101')
    """
    
    def __init__(
        self,
        entity_id: str,
        entity_type: str,
        base_term: str,
        required_terms: List[str],
        required_data: List[str],
        data_slice_size: int = 1000,
        data_mgr: DataManager = None
    ):
        """
        初始化 Worker Data Manager
        
        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            base_term: 基础周期（如 "daily"）
            required_terms: 需要的其他周期（如 ["weekly", "monthly"]）
            required_data: 需要的数据源（如 ["corporate_finance", "market_value"]）
            data_slice_size: 数据切片大小（记录数，默认1000）
            data_mgr: DataManager 实例（可选，如果不提供则自动初始化单例）
        """
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.base_term = base_term
        self.required_terms = required_terms or []
        self.required_data = required_data or []
        self.data_slice_size = data_slice_size
        
        # 初始化 DataManager（单例模式）
        if data_mgr is None:
            self.data_mgr = DataManager(is_verbose=False)
        else:
            self.data_mgr = data_mgr
        
        # 数据缓存（按需加载）
        self.data_cache = {}  # 当前加载的数据切片
        
        # 切片状态记录：记录每个数据源已加载到的全局记录索引
        # 格式：{data_source_key: {term_or_key: global_index}}
        # 例如：{'klines': {'daily': 1000, 'weekly': 500}, 'finance': 200}
        self.slice_state = self._init_slice_state()
        
        # 时间 cursor：用于缓存每个数据源的当前索引位置（相对于当前缓存）
        # 格式：{data_source_key: {term_or_key: current_index}}
        # 例如：{'klines': {'daily': 100, 'weekly': 50}, 'finance': 20}
        self.time_cursor = self._init_time_cursor()
    
    def _init_time_cursor(self) -> Dict[str, Any]:
        """初始化 time_cursor"""
        cursor = {}
        kline_terms = set([self.base_term] + self.required_terms)
        cursor['klines'] = {term: 0 for term in kline_terms}
        for data_type in self.required_data:
            cursor[data_type] = 0
        return cursor
    
    def _init_slice_state(self) -> Dict[str, Any]:
        """初始化切片状态"""
        state = {}
        kline_terms = set([self.base_term] + self.required_terms)
        state['klines'] = {term: 0 for term in kline_terms}
        # required_data 不记录 slice_state（因为它们按时间范围加载）
        return state
    
    def ensure_data_loaded(self, as_of_date: str):
        """
        确保当前 as_of_date 所需的数据已加载到缓存中
        
        按需加载数据切片（每次1000条记录），避免内存爆炸
        
        检查逻辑：
        1. 如果缓存为空，加载第一个切片
        2. 如果当前切片的 cursor 接近末尾（剩余记录 < 20%），加载下一个切片
        3. 如果当前 as_of_date 的数据不在缓存中（需要更早的数据），加载新切片
        
        Args:
            as_of_date: 当前业务日期
        """
        # 检查是否需要加载新切片
        need_load = False
        
        # 情况1：缓存为空
        if not self.data_cache:
            need_load = True
        else:
            # 情况2：检查 base_term 的 cursor 是否接近缓存末尾
            base_cursor = self.time_cursor.get('klines', {}).get(self.base_term, 0)
            base_data = self.data_cache.get('klines', {}).get(self.base_term, [])
            
            if base_data:
                current_cache_size = len(base_data)
                remaining = current_cache_size - base_cursor
                threshold = max(10, int(current_cache_size * 0.2))  # 至少保留10条，或20%
                
                if remaining < threshold:
                    need_load = True
                else:
                    # 情况3：检查当前 as_of_date 的数据是否在缓存中
                    last_record = base_data[-1] if base_data else None
                    if last_record and last_record.get('date', '') < as_of_date:
                        need_load = True
            else:
                need_load = True
        
        if need_load:
            # 加载新数据切片
            new_slice = self._load_data_slice()
            
            # 合并到现有缓存
            if not self.data_cache:
                self.data_cache = new_slice
            else:
                # 合并 K 线数据
                if 'klines' in new_slice:
                    if 'klines' not in self.data_cache:
                        self.data_cache['klines'] = {}
                    for term, new_data in new_slice['klines'].items():
                        if term in self.data_cache['klines']:
                            self.data_cache['klines'][term].extend(new_data)
                        else:
                            self.data_cache['klines'][term] = new_data
                
                # 合并其他数据源（required_data，需要去重）
                for key, new_data in new_slice.items():
                    if key != 'klines':
                        if key in self.data_cache:
                            if isinstance(new_data, list) and isinstance(self.data_cache[key], list):
                                # 去重合并
                                existing_data = self.data_cache[key]
                                if existing_data:
                                    unique_key = self._get_unique_key_for_data_type(key)
                                    existing_keys = {
                                        self._extract_unique_key(record, unique_key)
                                        for record in existing_data
                                        if self._extract_unique_key(record, unique_key)
                                    }
                                    
                                    for record in new_data:
                                        record_key = self._extract_unique_key(record, unique_key)
                                        if record_key and record_key not in existing_keys:
                                            existing_data.append(record)
                                            existing_keys.add(record_key)
                                    
                                    self.data_cache[key] = existing_data
                                else:
                                    self.data_cache[key] = new_data
                            else:
                                self.data_cache[key] = new_data
                        else:
                            self.data_cache[key] = new_data
            
            # 更新 slice_state（只更新 base entity）
            self._update_slice_state(new_slice)
    
    def _load_data_slice(self) -> Dict[str, Any]:
        """
        加载数据切片（按记录数，每次1000条）
        
        加载策略：
        1. Base entity（klines）按记录数切片（1000条）
        2. Required data 按时间范围加载（与 base entity 对齐）
        """
        historical_data = {}
        
        # 1. 加载 K 线数据（base entity + required_terms）
        kline_terms = set([self.base_term] + self.required_terms)
        klines = {}
        
        for term in kline_terms:
            try:
                global_offset = self.slice_state.get('klines', {}).get(term, 0)
                kline_model = self.data_mgr.get_model('stock_kline')
                if kline_model:
                    kline_data = kline_model.load(
                        condition="id = %s AND term = %s",
                        params=(self.entity_id, term),
                        order_by="date ASC",
                        limit=self.data_slice_size,
                        offset=global_offset
                    )
                else:
                    kline_data = []
                klines[term] = kline_data or []
            except Exception as e:
                logger.warning(f"加载 K 线数据失败: entity_id={self.entity_id}, term={term}, error={e}")
                klines[term] = []
        
        historical_data['klines'] = klines
        
        # 2. 从 base entity 的切片中提取时间范围
        base_kline_data = klines.get(self.base_term, [])
        if base_kline_data:
            first_date = base_kline_data[0].get('date', '') if base_kline_data else ''
            last_date = base_kline_data[-1].get('date', '') if base_kline_data else ''
            time_range = (first_date, last_date)
        else:
            time_range = (None, None)
        
        # 3. 加载 required_data（按时间范围，与 base entity 对齐）
        for data_type in self.required_data:
            try:
                if not time_range[0] or not time_range[1]:
                    historical_data[data_type] = []
                    continue
                
                start_date, end_date = time_range
                
                if data_type == 'corporate_finance':
                    finance_model = self.data_mgr.get_model('corporate_finance')
                    if finance_model:
                        start_quarter = self._date_to_quarter(start_date)
                        end_quarter = self._date_to_quarter(end_date)
                        finance_data = finance_model.load(
                            condition="id = %s AND quarter >= %s AND quarter <= %s",
                            params=(self.entity_id, start_quarter, end_quarter),
                            order_by="quarter ASC"
                        )
                    else:
                        finance_data = []
                    historical_data['finance'] = finance_data
                
                elif data_type == 'market_value':
                    market_value_model = self.data_mgr.get_model('market_value')
                    if market_value_model:
                        market_value_data = market_value_model.load(
                            condition="id = %s AND date BETWEEN %s AND %s",
                            params=(self.entity_id, start_date, end_date),
                            order_by="date ASC"
                        )
                    else:
                        market_value_data = []
                    historical_data['market_value'] = market_value_data
                
                else:
                    # 通用处理：尝试通过 model 加载
                    model = self.data_mgr.get_model(data_type)
                    if model:
                        try:
                            other_data = model.load(
                                condition="id = %s AND date BETWEEN %s AND %s",
                                params=(self.entity_id, start_date, end_date),
                                order_by="date ASC"
                            )
                            historical_data[data_type] = other_data
                        except Exception:
                            logger.warning(f"无法按时间范围加载 {data_type} 数据，字段可能不匹配")
                            historical_data[data_type] = []
                    else:
                        historical_data[data_type] = []
                
            except Exception as e:
                logger.warning(f"加载 {data_type} 数据失败: entity_id={self.entity_id}, error={e}")
                historical_data[data_type] = []
        
        return historical_data
    
    def _update_slice_state(self, new_slice: Dict[str, Any]):
        """更新切片状态（只更新 base entity）"""
        if 'klines' in new_slice:
            for term, data_list in new_slice['klines'].items():
                if term in self.slice_state.get('klines', {}):
                    self.slice_state['klines'][term] += len(data_list)
                else:
                    self.slice_state.setdefault('klines', {})[term] = len(data_list)
    
    def filter_data_to_date(self, as_of_date: str) -> Dict[str, Any]:
        """
        使用 time_cursor 高效过滤数据到指定日期（避免"上帝模式"）
        
        从上次 cursor 位置继续遍历，避免重复扫描已处理的数据。
        
        Args:
            as_of_date: 业务日期（YYYYMMDD）
        
        Returns:
            Dict[str, Any]: 过滤后的数据
        """
        # 确保数据已加载
        self.ensure_data_loaded(as_of_date)
        
        filtered_data = {}
        
        # 1. 过滤 K 线数据（使用 cursor 优化）
        if 'klines' in self.data_cache:
            filtered_klines = {}
            for term, kline_list in self.data_cache['klines'].items():
                start_idx = self.time_cursor.get('klines', {}).get(term, 0)
                
                filtered_records = []
                current_idx = start_idx
                
                while current_idx < len(kline_list):
                    record = kline_list[current_idx]
                    record_date = record.get('date', '')
                    
                    if record_date <= as_of_date:
                        filtered_records.append(record)
                        current_idx += 1
                    else:
                        break
                
                # 更新 cursor
                if 'klines' not in self.time_cursor:
                    self.time_cursor['klines'] = {}
                self.time_cursor['klines'][term] = current_idx
                
                filtered_klines[term] = filtered_records
            
            filtered_data['klines'] = filtered_klines
        
        # 2. 过滤其他数据源（使用 cursor 优化）
        for key, data_list in self.data_cache.items():
            if key == 'klines':
                continue
            
            if isinstance(data_list, list):
                start_idx = self.time_cursor.get(key, 0)
                date_field = 'date' if key != 'finance' else 'quarter'
                
                filtered_records = []
                current_idx = start_idx
                
                while current_idx < len(data_list):
                    record = data_list[current_idx]
                    record_date = record.get(date_field, '')
                    
                    if self._compare_date(record_date, as_of_date):
                        filtered_records.append(record)
                        current_idx += 1
                    else:
                        break
                
                self.time_cursor[key] = current_idx
                filtered_data[key] = filtered_records
            else:
                filtered_data[key] = data_list
        
        return filtered_data
    
    def get_trading_dates(self, start_date: str, end_date: str) -> List[str]:
        """
        获取交易日列表（基于 base entity 的时间轴）
        
        Args:
            start_date: 起始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
        
        Returns:
            List[str]: 交易日列表（YYYYMMDD 格式）
        """
        # 方案1：从 DataManager 获取交易日历（推荐）
        if self.data_mgr and hasattr(self.data_mgr, 'get_trading_dates'):
            trading_dates = self.data_mgr.get_trading_dates(start_date, end_date)
            if trading_dates:
                return trading_dates
        
        # 方案2：从数据缓存中提取（如果已加载）
        if self.data_cache and 'klines' in self.data_cache:
            base_kline = self.data_cache['klines'].get(self.base_term, [])
            if base_kline:
                all_dates = sorted(set(record.get('date', '') for record in base_kline if record.get('date')))
                trading_dates = [
                    date for date in all_dates
                    if start_date <= date <= end_date
                ]
                return trading_dates
        
        # 如果都失败，返回空列表
        logger.warning(f"无法获取交易日列表: entity_id={self.entity_id}, start_date={start_date}, end_date={end_date}")
        return []
    
    def _date_to_quarter(self, date_str: str) -> str:
        """将日期（YYYYMMDD）转换为季度（YYYYQ[1-4]）"""
        if not date_str or len(date_str) != 8:
            return ''
        year = int(date_str[:4])
        month = int(date_str[4:6])
        quarter = (month - 1) // 3 + 1
        return f"{year}Q{quarter}"
    
    def _get_unique_key_for_data_type(self, data_type: str) -> str:
        """获取数据源类型的唯一键字段名"""
        if data_type == 'corporate_finance':
            return 'quarter'
        else:
            return 'date'
    
    def _extract_unique_key(self, record: Dict[str, Any], unique_key: str) -> Optional[str]:
        """从记录中提取唯一键值"""
        return record.get(unique_key)
    
    def _compare_date(self, date1: str, date2: str) -> bool:
        """比较日期（date1 <= date2）"""
        if len(date1) == 8 and len(date2) == 8:
            return date1 <= date2
        # TODO: 实现季度等其他格式的比较
        return True
