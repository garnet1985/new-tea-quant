"""
Tag Worker Data Manager - 数据加载和缓存管理

负责从 settings 解析数据需求，管理数据缓存（chunk 或全量），提供数据加载和过滤接口。
"""
from typing import Dict, Any, List, Optional
import logging
from core.modules.data_manager import DataManager

logger = logging.getLogger(__name__)


class TagWorkerDataManager:
    """
    数据管理器：负责数据加载、缓存和过滤
    
    策略：
    - Kline 数据：支持 chunk 模式（滑动窗口，最多 2 个 chunk）或全量模式
    - Required data：全量加载（数据量小，不做 chunk）
    """
    
    def __init__(
        self,
        entity_id: str,
        entity_type: str,
        settings: Dict[str, Any],
        data_mgr: DataManager = None
    ):
        """初始化数据管理器"""
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.settings = settings
        
        # 从 settings 解析数据需求
        self._parse_data_requirements()
        
        # 初始化 DataManager（单例模式）
        if data_mgr is None:
            self.data_mgr = DataManager(is_verbose=False)
        else:
            self.data_mgr = data_mgr
        
        self.data_cache = {}
        self.chunk_count = 0
        self.slice_state = self._init_slice_state()
    
    def _parse_data_requirements(self):
        """从 settings 解析数据需求和配置"""
        target_entity = self.settings.get('target_entity', {})
        target_entity_type = target_entity.get('type', '') if isinstance(target_entity, dict) else target_entity
        
        self.base_term = self._extract_term_from_entity_type(target_entity_type)
        self.is_base_kline = self.base_term is not None
        
        if not self.is_base_kline:
            self.base_data_source = self._extract_data_source_from_entity_type(target_entity_type)
            self.base_term = 'daily'  # 默认使用日线数据
        else:
            self.base_data_source = None
        
        required_entities = self.settings.get('required_entities', [])
        self.required_terms = []
        self.required_data = []
        
        for entity in required_entities:
            entity_type = entity.get('type', '') if isinstance(entity, dict) else entity
            term = self._extract_term_from_entity_type(entity_type)
            if term and term != self.base_term:
                self.required_terms.append(term)
            else:
                data_source = self._extract_data_source_from_entity_type(entity_type)
                if data_source:
                    self.required_data.append(data_source)
        
        performance = self.settings.get('performance', {})
        self.data_slice_size = performance.get('data_chunk_size', 500)
        
        if self.data_slice_size < 300:
            raise ValueError(
                f"data_chunk_size 不能小于 300，当前值: {self.data_slice_size}。"
                f"请增加 chunk size 或设置 use_chunk=false 使用全量加载。"
            )
        
        self.use_chunk = performance.get('use_chunk', True)
        if not isinstance(self.use_chunk, bool):
            logger.warning(f"use_chunk 必须是布尔值，当前值: {self.use_chunk}，使用默认值 True")
            self.use_chunk = True
        
        update_mode_str = self.settings.get('update_mode') or performance.get('update_mode', 'incremental')
        from core.modules.tag.core.enums import TagUpdateMode
        try:
            self.update_mode = TagUpdateMode(update_mode_str)
        except ValueError:
            logger.warning(f"无效的 update_mode: {update_mode_str}，使用默认值 INCREMENTAL")
            self.update_mode = TagUpdateMode.INCREMENTAL
        
        if self.update_mode == TagUpdateMode.INCREMENTAL:
            self.incremental_required_records = self.settings.get('incremental_required_records_before_as_of_date', 0)
            if not isinstance(self.incremental_required_records, int) or self.incremental_required_records < 0:
                logger.warning(f"incremental_required_records_before_as_of_date 必须是非负整数，当前值: {self.incremental_required_records}，使用默认值 0")
                self.incremental_required_records = 0
            
            if self.use_chunk and self.incremental_required_records > self.data_slice_size:
                raise ValueError(
                    f"incremental_required_records_before_as_of_date ({self.incremental_required_records}) "
                    f"超过了第一个 chunk 的宽度 (data_chunk_size={self.data_slice_size})。"
                    f"请增加 data_chunk_size 或设置 use_chunk=false 使用全量加载。"
                )
        else:
            self.incremental_required_records = 0
    
    def _extract_term_from_entity_type(self, entity_type: str) -> Optional[str]:
        """从 EntityType 提取 term（daily/weekly/monthly），非 kline 返回 None"""
        if not entity_type:
            return None
        if 'kline_daily' in entity_type:
            return 'daily'
        if 'kline_weekly' in entity_type:
            return 'weekly'
        if 'kline_monthly' in entity_type:
            return 'monthly'
        return None
    
    def _extract_data_source_from_entity_type(self, entity_type: str) -> Optional[str]:
        """从 EntityType 提取数据源名称，kline 类型返回 None"""
        if not entity_type or 'kline' in entity_type:
            return None
        return entity_type
    
    def _init_slice_state(self) -> Dict[str, Any]:
        """初始化切片状态（只记录 kline 数据）"""
        kline_terms = set([self.base_term] + self.required_terms) if self.is_base_kline else set(self.required_terms)
        return {'klines': {term: 0 for term in kline_terms}} if kline_terms else {}
    
    def _get_base_data(self) -> List[Dict]:
        """获取 base data（根据类型从缓存中获取）"""
        if self.is_base_kline:
            return self.data_cache.get('klines', {}).get(self.base_term, [])
        return self.data_cache.get(self.base_data_source, [])
    
    def _get_record_date(self, record: Dict, is_last: bool = False) -> Optional[str]:
        """从记录中提取日期字段，支持 date 和 quarter"""
        if not record:
            return None
        if self.is_base_kline:
            return record.get('date', '')
        
        date_str = record.get('date') or record.get('quarter', '')
        if not date_str or len(date_str) <= 4:
            return date_str
        
        if date_str[4] == 'Q':
            year, quarter = int(date_str[:4]), int(date_str[5])
            month = quarter * 3 if is_last else (quarter - 1) * 3 + 1
            day = (31 if month in [3, 6, 9, 12] else 30) if is_last else 1
            return f"{year}{month:02d}{day:02d}"
        
        return date_str
    
    def ensure_data_loaded(self, as_of_date: str):
        """确保 as_of_date 所需的数据已加载到缓存中"""
        if not self.data_cache:
            need_load = True
        else:
            base_data = self._get_base_data()
            if not base_data:
                need_load = True
            else:
                last_date = self._get_record_date(base_data[-1], is_last=True)
                need_load = last_date and as_of_date and last_date < as_of_date
        
        if need_load:
            if self.use_chunk and self.is_base_kline:
                if self.chunk_count >= 2:
                    self._remove_first_chunk()
                new_slice = self._load_data_slice()
                self._merge_klines_to_cache(new_slice)
                self._update_slice_state(new_slice)
            elif not self.use_chunk and self.is_base_kline:
                self._load_all_klines_upto(as_of_date)
        
        if not self.is_base_kline:
            self._load_base_data_upto(as_of_date)
        self._load_required_data_upto(as_of_date)
    
    def _merge_klines_to_cache(self, new_slice: Dict[str, Any]):
        """合并 K 线数据到缓存"""
        if not self.data_cache:
            self.data_cache = {'klines': {}}
            self.chunk_count = 0
        
        if 'klines' in new_slice:
            self.data_cache.setdefault('klines', {})
            for term, new_data in new_slice['klines'].items():
                self.data_cache['klines'].setdefault(term, []).extend(new_data)
            self.chunk_count += 1
    
    def _find_as_of_index(self, base_data: List[Dict], as_of_date: str) -> Optional[int]:
        """找到 as_of_date 在 base_data 中的索引位置"""
        for i, record in enumerate(base_data):
            record_date = record.get('date', '')
            if record_date == as_of_date:
                return i
            if record_date and as_of_date and record_date > as_of_date:
                return i - 1
        return None
    
    def _ensure_incremental_lookback_data(self, as_of_date: str):
        """在 INCREMENTAL 模式下，确保 base data 往前 N 条记录也在缓存中"""
        base_data = self._get_base_data()
        if not base_data:
            return
        
        as_of_index = self._find_as_of_index(base_data, as_of_date)
        if as_of_index is None:
            return
        
        required_start_index = as_of_index - self.incremental_required_records + 1
        if required_start_index < 0 and self.is_base_kline:
            first_date = self._get_record_date(base_data[0], is_last=False)
            if first_date:
                max_records = abs(required_start_index) + self.data_slice_size
                new_slice = self._load_earlier_data_by_date(first_date, max_records)
                self._merge_earlier_klines_to_cache(new_slice)
    
    def _merge_earlier_klines_to_cache(self, new_slice: Dict[str, Any]):
        """合并更早的 K 线数据到缓存开头（用于 lookback）"""
        if 'klines' not in new_slice:
            return
        if 'klines' not in self.data_cache:
            self.data_cache['klines'] = {}
        for term, new_data in new_slice['klines'].items():
            if term in self.data_cache['klines']:
                existing_dates = {r.get('date') for r in self.data_cache['klines'][term]}
                unique_new_data = [r for r in new_data if r.get('date') not in existing_dates]
                if unique_new_data:
                    self.data_cache['klines'][term] = unique_new_data + self.data_cache['klines'][term]
            else:
                self.data_cache['klines'][term] = new_data
    
    def _load_earlier_data_by_date(self, end_date: str, max_records: int) -> Dict[str, Any]:
        """通过日期范围查询加载更早的数据（不更新 slice_state）"""
        kline_model = self.data_mgr.get_table("sys_stock_kline_daily")
        if not kline_model:
            return {'klines': {}}
        
        klines = {}
        for term in set([self.base_term] + self.required_terms):
            try:
                kline_data = kline_model.load(
                    condition="id = %s AND term = %s AND date < %s",
                    params=(self.entity_id, term, end_date),
                    order_by="date ASC",
                    limit=max_records
                )
                klines[term] = kline_data or []
            except Exception as e:
                logger.warning(f"加载更早的 K 线数据失败: entity_id={self.entity_id}, term={term}, error={e}")
                klines[term] = []
        
        return {'klines': klines}
    
    def _remove_first_chunk(self):
        """删除第一个 chunk（保持最多2个chunk）"""
        if 'klines' in self.data_cache:
            for term in self.data_cache['klines']:
                kline_list = self.data_cache['klines'][term]
                if len(kline_list) > self.data_slice_size:
                    self.data_cache['klines'][term] = kline_list[self.data_slice_size:]
        self.chunk_count = 1
    
    def _load_all_klines_upto(self, as_of_date: str):
        """全量加载 K 线数据到指定日期（use_chunk=false）"""
        kline_model = self.data_mgr.get_table("sys_stock_kline_daily")
        if not kline_model:
            return
        
        klines = {}
        for term in set([self.base_term] + self.required_terms):
            try:
                kline_data = kline_model.load(
                    condition="id = %s AND term = %s AND date <= %s",
                    params=(self.entity_id, term, as_of_date),
                    order_by="date ASC"
                )
                klines[term] = kline_data or []
            except Exception as e:
                logger.warning(f"全量加载 K 线数据失败: entity_id={self.entity_id}, term={term}, error={e}")
                klines[term] = []
        
        self.data_cache.setdefault('klines', {}).update(klines)
        self.chunk_count = 0
    
    def _load_data_slice(self) -> Dict[str, Any]:
        """加载 K 线数据切片（按记录数）"""
        kline_model = self.data_mgr.get_table("sys_stock_kline_daily")
        if not kline_model:
            return {'klines': {}}
        
        klines = {}
        for term in set([self.base_term] + self.required_terms):
            try:
                offset = self.slice_state.get('klines', {}).get(term, 0)
                kline_data = kline_model.load(
                    condition="id = %s AND term = %s",
                    params=(self.entity_id, term),
                    order_by="date ASC",
                    limit=self.data_slice_size,
                    offset=offset
                )
                klines[term] = kline_data or []
            except Exception as e:
                logger.warning(f"加载 K 线数据失败: entity_id={self.entity_id}, term={term}, error={e}")
                klines[term] = []
        
        return {'klines': klines}
    
    def _load_base_data_upto(self, as_of_date: str):
        """加载非 kline 类型的 base data"""
        if self.is_base_kline:
            return
        
        lookback_start_date = None
        if self.incremental_required_records > 0:
            base_data = self.data_cache.get(self.base_data_source, [])
            if base_data:
                lookback_start_date = self._get_record_date(base_data[0], is_last=False)
        
        try:
            model = self.data_mgr.get_table(self.base_data_source)
            if model:
                data = self._load_data_by_date_range(model, self.base_data_source, lookback_start_date, as_of_date)
                self.data_cache[self.base_data_source] = data or []
            else:
                self.data_cache[self.base_data_source] = []
        except Exception as e:
            logger.warning(f"加载 base data 失败: entity_id={self.entity_id}, data_source={self.base_data_source}, error={e}")
            self.data_cache[self.base_data_source] = []
    
    def _load_required_data_upto(self, as_of_date: str):
        """加载 required_data 到指定日期"""
        lookback_start_date = None
        if self.incremental_required_records > 0:
            base_data = self._get_base_data()
            if base_data:
                lookback_start_date = self._get_record_date(base_data[0], is_last=False)
        
        for data_type in self.required_data:
            try:
                model = self.data_mgr.get_table(data_type)
                if model:
                    data = self._load_data_by_date_range(model, data_type, lookback_start_date, as_of_date)
                    self.data_cache[data_type] = data or []
                else:
                    self.data_cache[data_type] = []
            except Exception as e:
                logger.warning(f"加载 {data_type} 数据失败: entity_id={self.entity_id}, error={e}")
                self.data_cache[data_type] = []
    
    def _load_data_by_date_range(self, model, data_type: str, start_date: Optional[str], end_date: str) -> List[Dict]:
        """按日期范围加载数据（支持季度和日期类型）"""
        if data_type == 'corporate_finance':
            end_quarter = self._date_to_quarter(end_date)
            if start_date:
                start_quarter = self._date_to_quarter(start_date)
                return model.load(
                    condition="id = %s AND quarter >= %s AND quarter <= %s",
                    params=(self.entity_id, start_quarter, end_quarter),
                    order_by="quarter ASC"
                )
            return model.load(
                condition="id = %s AND quarter <= %s",
                params=(self.entity_id, end_quarter),
                order_by="quarter ASC"
            )
        
        if start_date:
            return model.load(
                condition="id = %s AND date >= %s AND date <= %s",
                params=(self.entity_id, start_date, end_date),
                order_by="date ASC"
            )
        return model.load(
            condition="id = %s AND date <= %s",
            params=(self.entity_id, end_date),
            order_by="date ASC"
        )
    
    def _update_slice_state(self, new_slice: Dict[str, Any]):
        """更新切片状态"""
        if 'klines' in new_slice:
            for term, data_list in new_slice['klines'].items():
                self.slice_state.setdefault('klines', {})[term] = \
                    self.slice_state.get('klines', {}).get(term, 0) + len(data_list)
    
    def filter_data_to_date(self, as_of_date: str) -> Dict[str, Any]:
        """过滤数据到指定日期（避免看到未来数据）"""
        self.ensure_data_loaded(as_of_date)
        filtered_data = {}
        
        if 'klines' in self.data_cache:
            filtered_klines = {}
            for term, kline_list in self.data_cache['klines'].items():
                filtered_klines[term] = [
                    r for r in kline_list
                    if r.get('date', '') and r.get('date', '') <= as_of_date
                ]
            filtered_data['klines'] = filtered_klines
        
        for key, data_list in self.data_cache.items():
            if key == 'klines' or not isinstance(data_list, list):
                if key != 'klines':
                    filtered_data[key] = data_list
                continue
            
            date_field = 'quarter' if key == 'corporate_finance' else 'date'
            filtered_records = []
            
            for record in data_list:
                record_date = record.get(date_field, '')
                if not record_date or not as_of_date:
                    continue
                
                if date_field == 'quarter':
                    record_year, record_quarter = int(record_date[:4]), int(record_date[5])
                    as_of_year, as_of_month = int(as_of_date[:4]), int(as_of_date[4:6])
                    as_of_quarter = (as_of_month - 1) // 3 + 1
                    if record_year < as_of_year or (record_year == as_of_year and record_quarter <= as_of_quarter):
                        filtered_records.append(record)
                    else:
                        break
                else:
                    if record_date <= as_of_date:
                        filtered_records.append(record)
                    else:
                        break
            
            filtered_data[key] = filtered_records
        
        return filtered_data
    
    def initialize_for_incremental(self, start_date: str):
        """在 INCREMENTAL 模式下初始化数据加载"""
        if not self.is_base_kline:
            return
        
        if self.use_chunk:
            kline_model = self.data_mgr.get_table("sys_stock_kline_daily")
            if not kline_model:
                logger.warning(f"无法获取 kline model，跳过初始化")
                return
            
            kline_terms = set([self.base_term] + self.required_terms)
            initial_offset = {}
            
            for term in kline_terms:
                try:
                    all_data_before = kline_model.load(
                        condition="id = %s AND term = %s AND date < %s",
                        params=(self.entity_id, term, start_date),
                        order_by="date ASC"
                    )
                    initial_offset[term] = len(all_data_before) if all_data_before else 0
                except Exception as e:
                    logger.warning(f"查询 {term} 的初始 offset 失败: {e}")
                    initial_offset[term] = 0
            
            previous_slice = {}
            if self.incremental_required_records > 0:
                for term in kline_terms:
                    prev_offset = max(0, initial_offset[term] - self.data_slice_size)
                    try:
                        prev_data = kline_model.load(
                            condition="id = %s AND term = %s",
                            params=(self.entity_id, term),
                            order_by="date ASC",
                            limit=self.data_slice_size,
                            offset=prev_offset
                        )
                        previous_slice[term] = prev_data or []
                    except Exception as e:
                        logger.warning(f"加载前一个 chunk 失败: {term}, error={e}")
                        previous_slice[term] = []
            
            current_slice = {}
            for term in kline_terms:
                try:
                    curr_data = kline_model.load(
                        condition="id = %s AND term = %s",
                        params=(self.entity_id, term),
                        order_by="date ASC",
                        limit=self.data_slice_size,
                        offset=initial_offset[term]
                    )
                    current_slice[term] = curr_data or []
                except Exception as e:
                    logger.warning(f"加载当前 chunk 失败: {term}, error={e}")
                    current_slice[term] = []
            
            if not self.data_cache:
                self.data_cache = {'klines': {}}
            
            if self.incremental_required_records > 0 and previous_slice:
                for term in kline_terms:
                    self.data_cache['klines'][term] = previous_slice.get(term, []) + current_slice.get(term, [])
                self.chunk_count = 2
            else:
                for term in kline_terms:
                    self.data_cache['klines'][term] = current_slice.get(term, [])
                self.chunk_count = 1
            
            for term in kline_terms:
                self.slice_state.setdefault('klines', {})[term] = initial_offset[term] + len(current_slice.get(term, []))
        else:
            self._load_all_klines_upto(start_date)
    
    def get_trading_dates(self, start_date: str, end_date: str) -> List[str]:
        """获取交易日列表"""
        if not self.data_cache or 'klines' not in self.data_cache:
            initial_slice = self._load_data_slice()
            if initial_slice and 'klines' in initial_slice:
                if not self.data_cache:
                    self.data_cache = {'klines': {}}
                for term, new_data in initial_slice['klines'].items():
                    self.data_cache['klines'].setdefault(term, []).extend(new_data)
                self.chunk_count = 1
        
        base_kline = self.data_cache.get('klines', {}).get(self.base_term, [])
        if base_kline:
            all_dates = sorted(set(r.get('date', '') for r in base_kline if r.get('date')))
            if start_date and end_date:
                trading_dates = [d for d in all_dates if start_date <= d <= end_date]
                if trading_dates:
                    return trading_dates
        
        logger.warning(f"无法获取交易日列表: entity_id={self.entity_id}, start_date={start_date}, end_date={end_date}")
        return []
    
    def _date_to_quarter(self, date_str: str) -> str:
        """将日期（YYYYMMDD）转换为季度（YYYYQ[1-4]）"""
        from core.utils.date.date_utils import DateUtils
        try:
            return DateUtils.date_to_quarter(date_str)
        except (ValueError, AttributeError):
            return ''
