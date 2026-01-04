"""
Tag Worker Data Manager - Tag Worker 数据管理器

职责：
1. 从 settings 解析 target_entity 和 required_entities
2. 管理数据缓存（按记录数切片加载，滑动窗口最多保持 2 个 chunk）
3. 管理切片状态（slice_state，用于决定下一次 DB 查询的 offset）
4. 提供数据加载和过滤接口
5. required_data 全量加载到 as_of_date（不做 chunk，因为数据量小）

注意：
- 这是子进程中的数据管理器，在子进程中实例化
- 负责所有数据加载、缓存、过滤逻辑
- BaseTagWorker 通过此管理器获取数据，专注于 tag 计算流程
"""
from typing import Dict, Any, List, Optional
import logging
from app.core.modules.data_manager import DataManager

logger = logging.getLogger(__name__)


class TagWorkerDataManager:
    """
    Worker Data Manager - 子进程数据管理器
    
    职责：
    1. 管理数据缓存（滑动窗口，最多保持 2 个 chunk）
    2. 管理切片状态（slice_state，DB 维度，用于决定下一次 DB 查询的 offset）
    3. 提供数据加载和过滤接口
    4. required_data 全量加载到 as_of_date（不做 chunk，因为数据量小）
    
    滑动窗口策略：
    - 保持最多 2 个 chunk 的 klines 数据在内存中
    - 支持需要历史数据的计算（如移动平均线）
    - 内存可控（最多 2 * data_slice_size 条记录）
    - 当需要加载第三个 chunk 时，强制删除第一个 chunk（永远只保持 2 个）
    
    required_data 策略：
    - 财报、估值等数据量远小于日线，全量加载不会成为内存瓶颈
    - 每次调用按时间条件查数据库，结果放在 cache（可直接覆盖旧 cache）
    - 不需要分块，逻辑简单可控
    
    使用方式：
        data_mgr = TagWorkerDataManager(
            entity_id='000001.SZ',
            entity_type='stock',
            settings=settings  # 完整的 settings 字典，data_manager 会自动解析
        )
        
        # 获取交易日列表
        trading_dates = data_mgr.get_trading_dates(start_date, end_date)
        
        # 遍历每个日期，获取历史数据（自动按需加载）
        for as_of_date in trading_dates:
            historical_data = data_mgr.filter_data_to_date(as_of_date)
    """
    
    def __init__(
        self,
        entity_id: str,
        entity_type: str,
        settings: Dict[str, Any],
        data_mgr: DataManager = None
    ):
        """
        初始化 Tag Worker Data Manager
        
        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            settings: Settings 字典（完整的 settings 配置）
            data_mgr: DataManager 实例（可选，如果不提供则自动初始化单例）
        """
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
        
        # 数据缓存（滑动窗口，最多保持 2 个 chunk）
        # 这样可以支持需要历史数据的计算（如移动平均线）
        self.data_cache = {}  # 合并后的数据缓存（最多包含 2 个 chunk）
        self.chunk_count = 0  # 当前缓存中的 chunk 数量（最多 2 个）
        
        # 切片状态记录：记录每个数据源已加载到的全局记录索引（DB维度）
        # 格式：{data_source_key: {term_or_key: global_index}}
        # 例如：{'klines': {'daily': 1000, 'weekly': 500}}
        # 注意：只用于决定下一次DB查询的offset，不跟内存删除关联
        self.slice_state = self._init_slice_state()
    
    def _parse_data_requirements(self):
        """
        从 settings 解析数据需求
        
        解析：
        1. target_entity.type -> base_term（主数据源）
        2. required_entities -> required_terms（其他 kline 周期）和 required_data（其他数据源）
        3. performance.data_chunk_size -> data_slice_size
        """
        # 从 target_entity.type 提取 base_term
        target_entity = self.settings.get('target_entity', {})
        if isinstance(target_entity, dict):
            target_entity_type = target_entity.get('type', '')
        else:
            target_entity_type = target_entity
        
        self.base_term = self._extract_term_from_entity_type(target_entity_type) or 'daily'
        
        # 从 required_entities 提取 required_terms 和 required_data
        required_entities = self.settings.get('required_entities', [])
        self.required_terms = []
        self.required_data = []
        
        for entity in required_entities:
            if isinstance(entity, dict):
                entity_type = entity.get('type', '')
            else:
                entity_type = entity
            
            # 判断是 kline 类型还是其他数据源
            term = self._extract_term_from_entity_type(entity_type)
            if term:
                # 是 kline 类型，添加到 required_terms
                if term != self.base_term:  # 避免重复添加 base_term
                    self.required_terms.append(term)
            else:
                # 不是 kline 类型，添加到 required_data
                data_source = self._extract_data_source_from_entity_type(entity_type)
                if data_source:
                    self.required_data.append(data_source)
        
        # 数据切片大小配置（从 performance 中读取，默认 500）
        performance = self.settings.get('performance', {})
        self.data_slice_size = performance.get('data_chunk_size', 500)
    
    def _extract_term_from_entity_type(self, entity_type: str) -> Optional[str]:
        """
        从 EntityType 字符串中提取 term（daily/weekly/monthly）
        
        Args:
            entity_type: EntityType 值（如 "stock_kline_daily", "stock_kline_weekly" 等）
        
        Returns:
            Optional[str]: term 字符串（"daily", "weekly", "monthly"），如果不是 kline 类型则返回 None
        """
        if not entity_type:
            return None
        
        # 提取 kline 类型中的 term
        if 'kline_daily' in entity_type:
            return 'daily'
        elif 'kline_weekly' in entity_type:
            return 'weekly'
        elif 'kline_monthly' in entity_type:
            return 'monthly'
        
        return None
    
    def _extract_data_source_from_entity_type(self, entity_type: str) -> Optional[str]:
        """
        从 EntityType 字符串中提取数据源名称
        
        Args:
            entity_type: EntityType 值（如 "corporate_finance", "gdp" 等）
        
        Returns:
            Optional[str]: 数据源名称，如果是 kline 类型则返回 None
        """
        if not entity_type:
            return None
        
        # 如果是 kline 类型，返回 None
        if 'kline' in entity_type:
            return None
        
        # 直接返回 entity_type 作为数据源名称
        # 例如: "corporate_finance" -> "corporate_finance"
        return entity_type
    
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
        
        滑动窗口策略：保持最多 2 个 chunk 的数据
        - 支持需要历史数据的计算（如移动平均线）
        - 内存可控（最多 2 * data_slice_size 条记录）
        
        检查逻辑：
        1. 如果缓存为空，加载第一个 chunk
        2. 如果当前 as_of_date 的数据不在缓存中（缓存的最后一条记录日期 < as_of_date），加载新 chunk
        3. 如果已有 2 个 chunk，加载新 chunk 时删除第一个 chunk
        
        Args:
            as_of_date: 当前业务日期
        """
        # 检查是否需要加载新切片
        need_load = False
        
        # 情况1：缓存为空
        if not self.data_cache:
            need_load = True
        else:
            # 情况2：检查当前 as_of_date 的数据是否在缓存中
            # 如果缓存的最后一条记录日期 < as_of_date，说明数据用完了，需要加载新切片
            base_data = self.data_cache.get('klines', {}).get(self.base_term, [])
            
            if base_data:
                last_record = base_data[-1] if base_data else None
                last_date = last_record.get('date', '') if last_record else None
                if last_date and as_of_date and last_date < as_of_date:
                    need_load = True
            else:
                # 如果 base_data 为空，需要加载
                need_load = True
        
        if need_load:
            # 如果已有 2 个 chunk，强制删除最旧的 chunk（永远只保持 2 个 chunk）
            if self.chunk_count >= 2:
                self._remove_first_chunk()
            
            # 加载新数据切片（只加载 klines）
            new_slice = self._load_data_slice()
            
            # 合并到现有缓存
            if not self.data_cache:
                self.data_cache = {'klines': {}}
                self.chunk_count = 0
            
            # 合并 K 线数据
            if 'klines' in new_slice:
                if 'klines' not in self.data_cache:
                    self.data_cache['klines'] = {}
                for term, new_data in new_slice['klines'].items():
                    if term in self.data_cache['klines']:
                        self.data_cache['klines'][term].extend(new_data)
                    else:
                        self.data_cache['klines'][term] = new_data
                
                self.chunk_count += 1
            
            # 更新 slice_state（只更新 klines）
            self._update_slice_state(new_slice)
        
        # 加载 required_data（全量加载到 as_of_date，不做chunk）
        self._load_required_data_upto(as_of_date)
    
    def _remove_first_chunk(self):
        """
        删除第一个 chunk 的 K 线数据（滑动窗口）
        
        简化逻辑：强制删除第一个 chunk，永远只保持 2 个 chunk。
        注意：slice_state 记录的是数据库的全局 offset，不应该改变。
        """
        if 'klines' in self.data_cache:
            for term in self.data_cache['klines']:
                kline_list = self.data_cache['klines'][term]
                if len(kline_list) > self.data_slice_size:
                    # 删除第一个 chunk
                    removed_count = min(self.data_slice_size, len(kline_list))
                    self.data_cache['klines'][term] = kline_list[removed_count:]
        
        # 更新 chunk 数量
        self.chunk_count = 1
    
    def _load_data_slice(self) -> Dict[str, Any]:
        """
        加载 K 线数据切片（按记录数，每次 data_slice_size 条）
        
        注意：只加载 klines，required_data 由 _load_required_data_upto 单独处理
        """
        historical_data = {}
        
        # 加载 K 线数据（base entity + required_terms）
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
        return historical_data
    
    def _load_required_data_upto(self, as_of_date: str):
        """
        加载 required_data 到指定日期（全量加载，不做chunk）
        
        策略：
        - 财报、估值等数据量远小于日线，全量加载不会成为内存瓶颈
        - 每次调用按时间条件查数据库，结果放在 cache（可直接覆盖旧 cache）
        - 不需要分块，逻辑简单可控
        """
        for data_type in self.required_data:
            try:
                if data_type == 'corporate_finance':
                    finance_model = self.data_mgr.get_model('corporate_finance')
                    if finance_model:
                        # 加载所有季度数据到 as_of_date
                        end_quarter = self._date_to_quarter(as_of_date)
                        finance_data = finance_model.load(
                            condition="id = %s AND quarter <= %s",
                            params=(self.entity_id, end_quarter),
                            order_by="quarter ASC"
                        )
                        # 直接覆盖 cache（不需要去重，因为每次都是全量查询）
                        self.data_cache['corporate_finance'] = finance_data or []
                    else:
                        self.data_cache['corporate_finance'] = []
                
                elif data_type == 'market_value':
                    market_value_model = self.data_mgr.get_model('market_value')
                    if market_value_model:
                        # 加载所有日期数据到 as_of_date
                        market_value_data = market_value_model.load(
                            condition="id = %s AND date <= %s",
                            params=(self.entity_id, as_of_date),
                            order_by="date ASC"
                        )
                        # 直接覆盖 cache
                        self.data_cache['market_value'] = market_value_data or []
                    else:
                        self.data_cache['market_value'] = []
                
                else:
                    # 通用处理：尝试通过 model 加载
                    model = self.data_mgr.get_model(data_type)
                    if model:
                        try:
                            other_data = model.load(
                                condition="id = %s AND date <= %s",
                                params=(self.entity_id, as_of_date),
                                order_by="date ASC"
                            )
                            self.data_cache[data_type] = other_data or []
                        except Exception:
                            logger.warning(f"无法按时间条件加载 {data_type} 数据，字段可能不匹配")
                            self.data_cache[data_type] = []
                    else:
                        self.data_cache[data_type] = []
                
            except Exception as e:
                logger.warning(f"加载 {data_type} 数据失败: entity_id={self.entity_id}, error={e}")
                self.data_cache[data_type] = []
    
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
        过滤数据到指定日期（避免"上帝模式"）
        
        返回从开始到 as_of_date 的所有历史数据（不是增量数据）。
        
        注意：
        - 返回的是从开始到 as_of_date 的所有数据（用于计算移动平均线等指标）
        - 简化实现：直接从头遍历，不做 cursor 优化（等未来真遇到性能瓶颈再加）
        
        Args:
            as_of_date: 业务日期（YYYYMMDD）
        
        Returns:
            Dict[str, Any]: 过滤后的数据（从开始到 as_of_date 的所有历史数据）
        """
        # 确保数据已加载
        self.ensure_data_loaded(as_of_date)
        
        filtered_data = {}
        
        # 1. 过滤 K 线数据（返回从开始到 as_of_date 的所有数据）
        if 'klines' in self.data_cache:
            filtered_klines = {}
            for term, kline_list in self.data_cache['klines'].items():
                filtered_records = []
                for record in kline_list:
                    record_date = record.get('date', '')
                    # 确保 record_date 和 as_of_date 都不为 None 或空字符串
                    if record_date and as_of_date and record_date <= as_of_date:
                        filtered_records.append(record)
                    elif record_date and as_of_date:
                        # 遇到第一个超过 as_of_date 的记录，停止
                        break
                filtered_klines[term] = filtered_records
            filtered_data['klines'] = filtered_klines
        
        # 2. 过滤其他数据源（返回从开始到 as_of_date 的所有数据）
        for key, data_list in self.data_cache.items():
            if key == 'klines':
                continue
            
            if isinstance(data_list, list):
                date_field = 'date' if key != 'corporate_finance' else 'quarter'
                
                filtered_records = []
                for record in data_list:
                    record_date = record.get(date_field, '')
                    
                    if date_field == 'quarter':
                        # 季度数据：转换为日期比较
                        if record_date and as_of_date:
                            record_year = int(record_date[:4])
                            record_quarter = int(record_date[5])
                            as_of_year = int(as_of_date[:4])
                            as_of_month = int(as_of_date[4:6])
                            as_of_quarter = (as_of_month - 1) // 3 + 1
                            
                            if record_year < as_of_year or (record_year == as_of_year and record_quarter <= as_of_quarter):
                                filtered_records.append(record)
                            else:
                                break
                        else:
                            filtered_records.append(record)
                    else:
                        # 日期数据：直接比较（确保都不为 None 或空字符串）
                        if record_date and as_of_date and record_date <= as_of_date:
                            filtered_records.append(record)
                        elif record_date and as_of_date:
                            break
                
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
        # 注意：DataManager 可能没有 get_trading_dates 方法，需要从其他方式获取
        # 暂时跳过，使用方案2
        # if self.data_mgr and hasattr(self.data_mgr, 'get_trading_dates'):
        #     trading_dates = self.data_mgr.get_trading_dates(start_date, end_date)
        #     if trading_dates:
        #         return trading_dates
        
        # 方案2：从数据缓存中提取（如果已加载）
        if self.data_cache and 'klines' in self.data_cache:
            base_kline = self.data_cache['klines'].get(self.base_term, [])
            if base_kline:
                all_dates = sorted(set(record.get('date', '') for record in base_kline if record.get('date')))
                # 确保 start_date 和 end_date 不为 None
                if start_date and end_date:
                    trading_dates = [
                        date for date in all_dates
                        if start_date <= date <= end_date
                    ]
                else:
                    trading_dates = []
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
