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
        # 从 target_entity.type 提取 base_term 和判断是否是 kline 类型
        target_entity = self.settings.get('target_entity', {})
        if isinstance(target_entity, dict):
            target_entity_type = target_entity.get('type', '')
        else:
            target_entity_type = target_entity
        
        # 判断 base entity 是否是 kline 类型
        self.base_term = self._extract_term_from_entity_type(target_entity_type)
        self.is_base_kline = self.base_term is not None
        
        # 如果不是 kline 类型，base_term 为 None，需要提取数据源名称
        if not self.is_base_kline:
            self.base_data_source = self._extract_data_source_from_entity_type(target_entity_type)
            # 默认使用 'daily' 作为 base_term（用于兼容，但不会实际使用）
            self.base_term = 'daily'
        else:
            self.base_data_source = None
        
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
        
        # 验证 chunk size 最小值（至少 300）
        if self.data_slice_size < 300:
            raise ValueError(
                f"data_chunk_size 不能小于 300，当前值: {self.data_slice_size}。"
                f"请增加 chunk size 或设置 use_chunk=false 使用全量加载。"
            )
        
        # 读取 use_chunk 配置（默认 True）
        self.use_chunk = performance.get('use_chunk', True)
        if not isinstance(self.use_chunk, bool):
            logger.warning(f"use_chunk 必须是布尔值，当前值: {self.use_chunk}，使用默认值 True")
            self.use_chunk = True
        
        # 读取 update_mode 和 incremental_required_records_before_as_of_date
        # 只在 INCREMENTAL 模式下使用此配置
        update_mode_str = self.settings.get('update_mode')
        if not update_mode_str:
            update_mode_str = performance.get('update_mode', 'incremental')
        
        from app.core.modules.tag.core.enums import TagUpdateMode
        try:
            self.update_mode = TagUpdateMode(update_mode_str)
        except ValueError:
            logger.warning(f"无效的 update_mode: {update_mode_str}，使用默认值 INCREMENTAL")
            self.update_mode = TagUpdateMode.INCREMENTAL
        
        # 只在 INCREMENTAL 模式下读取 incremental_required_records_before_as_of_date
        if self.update_mode == TagUpdateMode.INCREMENTAL:
            self.incremental_required_records = self.settings.get('incremental_required_records_before_as_of_date', 0)
            if not isinstance(self.incremental_required_records, int) or self.incremental_required_records < 0:
                logger.warning(f"incremental_required_records_before_as_of_date 必须是非负整数，当前值: {self.incremental_required_records}，使用默认值 0")
                self.incremental_required_records = 0
            
            # 验证：如果 use_chunk=True，incremental_required_records 不能超过第一个 chunk 的宽度
            if self.use_chunk and self.incremental_required_records > 0:
                if self.incremental_required_records > self.data_slice_size:
                    raise ValueError(
                        f"incremental_required_records_before_as_of_date ({self.incremental_required_records}) "
                        f"超过了第一个 chunk 的宽度 (data_chunk_size={self.data_slice_size})。"
                        f"请增加 data_chunk_size 或设置 use_chunk=false 使用全量加载。"
                    )
        else:
            # REFRESH 模式下忽略此配置
            self.incremental_required_records = 0
    
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
        # 只有 kline 类型的数据才需要 slice_state
        # 如果 base entity 是 kline，包含 base_term；否则只包含 required_terms
        if self.is_base_kline:
            kline_terms = set([self.base_term] + self.required_terms)
        else:
            kline_terms = set(self.required_terms)
        
        if kline_terms:
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
        
        在 INCREMENTAL 模式下：
        - 确保 base data 往前 incremental_required_records 条记录也在缓存中
        - 如果不在，需要加载更多数据（可能需要加载多个 chunk）
        
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
            # 根据 base entity 类型获取 base data
            if self.is_base_kline:
                base_data = self.data_cache.get('klines', {}).get(self.base_term, [])
            else:
                # 非 kline 类型的 base entity
                base_data = self.data_cache.get(self.base_data_source, [])
            
            if base_data:
                last_record = base_data[-1] if base_data else None
                # 根据数据源类型获取日期字段
                if self.is_base_kline:
                    last_date = last_record.get('date', '') if last_record else None
                else:
                    # 非 kline 类型，可能是 'date' 或 'quarter' 字段
                    if last_record:
                        last_date = last_record.get('date') or last_record.get('quarter', '')
                        # 如果是 quarter，需要转换为日期（取该季度的最后一天）
                        if last_date and len(last_date) > 4 and last_date[4] == 'Q':
                            # 格式：2024Q1 -> 20240331
                            year = last_date[:4]
                            quarter = int(last_date[5])
                            month = quarter * 3
                            day = 31 if month in [3, 6, 9, 12] else 30
                            last_date = f"{year}{month:02d}{day}"
                    else:
                        last_date = None
                
                if last_date and as_of_date and last_date < as_of_date:
                    need_load = True
            else:
                # 如果 base_data 为空，需要加载
                need_load = True
        
        if need_load:
            # 根据 use_chunk 配置选择加载策略
            if self.use_chunk and self.is_base_kline:
                # Chunk 加载策略（滑动窗口）
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
            elif not self.use_chunk and self.is_base_kline:
                # 全量加载策略（use_chunk=false）
                self._load_all_klines_upto(as_of_date)
            else:
                # 非 kline 类型的 base entity，使用全量加载策略（类似 required_data）
                # 在 _load_base_data_upto 中处理
                pass
        
        # 加载 base data（如果不是 kline 类型）和 required_data
        # 在 INCREMENTAL 模式下，需要根据 base data 的第一个记录时间加载 lookback data
        if not self.is_base_kline:
            # 非 kline 类型的 base entity，需要加载 base data
            self._load_base_data_upto(as_of_date)
        
        # 加载 required_data（全量加载到 as_of_date，不做chunk）
        self._load_required_data_upto(as_of_date)
    
    def _ensure_incremental_lookback_data(self, as_of_date: str):
        """
        在 INCREMENTAL 模式下，确保 base data 往前 N 条记录也在缓存中
        
        逻辑：
        1. 找到 as_of_date 在 base data 中的位置
        2. 检查往前 N 条记录是否在缓存中
        3. 如果不在，需要加载更多数据（可能需要加载多个 chunk）
        
        注意：
        - 如果 base entity 是 kline 类型，从 klines 缓存中获取
        - 如果 base entity 不是 kline 类型，从对应的数据源缓存中获取
        
        Args:
            as_of_date: 当前业务日期
        """
        # 根据 base entity 类型获取 base data
        if self.is_base_kline:
            base_data = self.data_cache.get('klines', {}).get(self.base_term, [])
        else:
            # 非 kline 类型的 base entity
            base_data = self.data_cache.get(self.base_data_source, [])
        
        if not base_data:
            return
        
        # 找到 as_of_date 在 base_data 中的位置
        as_of_index = None
        for i, record in enumerate(base_data):
            record_date = record.get('date', '')
            if record_date == as_of_date:
                as_of_index = i
                break
            elif record_date and as_of_date and record_date > as_of_date:
                # 找到第一个超过 as_of_date 的记录，前一个就是 as_of_date 的位置
                as_of_index = i - 1
                break
        
        # 如果找不到 as_of_date，说明数据还没加载到，不需要检查 lookback
        if as_of_index is None:
            return
        
        # 检查往前 N 条记录是否在缓存中
        required_start_index = as_of_index - self.incremental_required_records + 1
        if required_start_index < 0:
            # 需要往前加载更多数据
            # 获取需要加载的起始日期（从 base_data 的第一个记录往前推算）
            first_record = base_data[0]
            first_date = first_record.get('date', '')
            if not first_date:
                return
            
            # 使用日期范围查询加载更早的数据
            # 计算需要往前加载多少条记录
            records_to_load = abs(required_start_index)
            # 估算需要加载的日期范围（假设每个交易日一条记录）
            # 为了安全，我们加载从数据库开始到 first_date 的所有数据
            # 但限制最大加载数量，避免一次性加载过多数据
            max_records_to_load = records_to_load + self.data_slice_size  # 多加载一些，确保足够
            
            logger.debug(f"需要加载 {records_to_load} 条记录以满足 incremental_required_records={self.incremental_required_records}，将从数据库开始加载到 {first_date}")
            
            # 使用日期范围查询加载更早的数据（不通过 slice_state，直接查询）
            if self.is_base_kline:
                # base entity 是 kline 类型
                new_slice = self._load_earlier_data_by_date(first_date, max_records_to_load)
                
                # 合并到现有缓存（插入到开头）
                if 'klines' in new_slice:
                    if 'klines' not in self.data_cache:
                        self.data_cache['klines'] = {}
                    for term, new_data in new_slice['klines'].items():
                        if term in self.data_cache['klines']:
                            # 插入到开头（保持日期顺序）
                            # 去重：只添加不在缓存中的数据
                            existing_dates = {r.get('date') for r in self.data_cache['klines'][term]}
                            unique_new_data = [r for r in new_data if r.get('date') not in existing_dates]
                            if unique_new_data:
                                self.data_cache['klines'][term] = unique_new_data + self.data_cache['klines'][term]
                        else:
                            self.data_cache['klines'][term] = new_data
                    
                    # 注意：不更新 slice_state，因为这是额外的历史数据加载
                    # slice_state 仍然保持原来的值，用于正常的向前加载
            else:
                # base entity 不是 kline 类型，需要根据数据源类型加载
                logger.warning(f"base entity 不是 kline 类型（{self.base_data_source}），incremental_required_records 的 lookback 功能可能不完全支持")
                # TODO: 实现非 kline 类型的 lookback 数据加载
                # 对于非 kline 类型，可能需要根据数据源的特点实现不同的加载策略
    
    def _load_earlier_data_by_date(self, end_date: str, max_records: int) -> Dict[str, Any]:
        """
        通过日期范围查询加载更早的数据（用于 INCREMENTAL 模式的 lookback）
        
        注意：
        - 这个方法不通过 slice_state，直接使用日期范围查询
        - 用于加载 as_of_date 之前的历史数据
        - 不更新 slice_state，避免与正常的向前加载冲突
        
        Args:
            end_date: 结束日期（不包含，即加载 < end_date 的数据）
            max_records: 最大加载记录数
            
        Returns:
            Dict[str, Any]: 加载的数据切片
        """
        historical_data = {}
        
        # 加载 K 线数据（base entity + required_terms）
        kline_terms = set([self.base_term] + self.required_terms)
        klines = {}
        
        for term in kline_terms:
            try:
                kline_model = self.data_mgr.get_model('stock_kline')
                if kline_model:
                    # 使用日期范围查询，从数据库开始到 end_date
                    kline_data = kline_model.load(
                        condition="id = %s AND term = %s AND date < %s",
                        params=(self.entity_id, term, end_date),
                        order_by="date ASC",
                        limit=max_records
                    )
                else:
                    kline_data = []
                klines[term] = kline_data or []
            except Exception as e:
                logger.warning(f"加载更早的 K 线数据失败: entity_id={self.entity_id}, term={term}, end_date={end_date}, error={e}")
                klines[term] = []
        
        historical_data['klines'] = klines
        return historical_data
    
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
    
    def _load_all_klines_upto(self, as_of_date: str):
        """
        全量加载 K 线数据到指定日期（use_chunk=false 时使用）
        
        策略：
        - 一次性加载所有数据到 as_of_date
        - 不做 chunk，直接覆盖 cache
        - 适用于数据量较小或需要全量数据的场景
        
        Args:
            as_of_date: 业务日期
        """
        historical_data = {}
        
        # 加载 K 线数据（base entity + required_terms）
        kline_terms = set([self.base_term] + self.required_terms)
        klines = {}
        
        for term in kline_terms:
            try:
                kline_model = self.data_mgr.get_model('stock_kline')
                if kline_model:
                    # 全量加载到 as_of_date
                    kline_data = kline_model.load(
                        condition="id = %s AND term = %s AND date <= %s",
                        params=(self.entity_id, term, as_of_date),
                        order_by="date ASC"
                    )
                else:
                    kline_data = []
                klines[term] = kline_data or []
            except Exception as e:
                logger.warning(f"全量加载 K 线数据失败: entity_id={self.entity_id}, term={term}, error={e}")
                klines[term] = []
        
        # 直接覆盖 cache（全量加载）
        if 'klines' not in self.data_cache:
            self.data_cache['klines'] = {}
        self.data_cache['klines'].update(klines)
        
        # 全量加载时，chunk_count 设为 0（不使用 chunk 机制）
        self.chunk_count = 0
    
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
    
    def _load_base_data_upto(self, as_of_date: str):
        """
        加载非 kline 类型的 base data 到指定日期（全量加载，不做chunk）
        
        策略：
        - 非 kline 类型的 base entity 数据量通常较小，全量加载不会成为内存瓶颈
        - 每次调用按时间条件查数据库，结果放在 cache（可直接覆盖旧 cache）
        - 不需要分块，逻辑简单可控
        
        在 INCREMENTAL 模式下：
        - 根据 base data 的第一个记录时间，加载相应的 lookback data
        - 确保 base data 也包含足够的历史数据
        """
        if self.is_base_kline:
            # kline 类型已经在 ensure_data_loaded 中处理
            return
        
        # 获取 lookback_start_date（在 INCREMENTAL 模式下）
        lookback_start_date = None
        if self.incremental_required_records > 0:
            # 检查缓存中是否已有数据
            base_data = self.data_cache.get(self.base_data_source, [])
            if base_data:
                first_record = base_data[0]
                # 根据数据源类型获取日期字段
                first_date = first_record.get('date') or first_record.get('quarter', '')
                # 如果是 quarter，需要转换为日期（取该季度的第一天）
                if first_date and len(first_date) > 4 and first_date[4] == 'Q':
                    # 格式：2024Q1 -> 20240101
                    year = first_date[:4]
                    quarter = int(first_date[5])
                    month = (quarter - 1) * 3 + 1
                    first_date = f"{year}{month:02d}01"
                
                if first_date:
                    lookback_start_date = first_date
                    logger.debug(f"INCREMENTAL 模式：base data 第一个记录时间={lookback_start_date}，将用于加载 base data 的起始时间")
        
        # 确定实际使用的起始日期
        effective_start_date = lookback_start_date if lookback_start_date else None
        
        # 加载 base data
        try:
            model = self.data_mgr.get_model(self.base_data_source)
            if model:
                # 根据数据源类型选择不同的加载策略
                if self.base_data_source == 'corporate_finance':
                    # 季度数据
                    end_quarter = self._date_to_quarter(as_of_date)
                    if effective_start_date:
                        start_quarter = self._date_to_quarter(effective_start_date)
                        base_data = model.load(
                            condition="id = %s AND quarter >= %s AND quarter <= %s",
                            params=(self.entity_id, start_quarter, end_quarter),
                            order_by="quarter ASC"
                        )
                    else:
                        base_data = model.load(
                            condition="id = %s AND quarter <= %s",
                            params=(self.entity_id, end_quarter),
                            order_by="quarter ASC"
                        )
                else:
                    # 日期数据
                    if effective_start_date:
                        base_data = model.load(
                            condition="id = %s AND date >= %s AND date <= %s",
                            params=(self.entity_id, effective_start_date, as_of_date),
                            order_by="date ASC"
                        )
                    else:
                        base_data = model.load(
                            condition="id = %s AND date <= %s",
                            params=(self.entity_id, as_of_date),
                            order_by="date ASC"
                        )
                
                self.data_cache[self.base_data_source] = base_data or []
            else:
                self.data_cache[self.base_data_source] = []
        except Exception as e:
            logger.warning(f"加载 base data 失败: entity_id={self.entity_id}, data_source={self.base_data_source}, error={e}")
            self.data_cache[self.base_data_source] = []
    
    def _load_required_data_upto(self, as_of_date: str):
        """
        加载 required_data 到指定日期（全量加载，不做chunk）
        
        策略：
        - 财报、估值等数据量远小于日线，全量加载不会成为内存瓶颈
        - 每次调用按时间条件查数据库，结果放在 cache（可直接覆盖旧 cache）
        - 不需要分块，逻辑简单可控
        
        在 INCREMENTAL 模式下：
        - 根据 base data 的第一个记录时间，加载相应的 lookback data
        - 确保 required_data 也包含足够的历史数据
        """
        # 在 INCREMENTAL 模式下，获取 base data 的第一个记录时间
        # 用于确定 required_data 的起始加载时间
        lookback_start_date = None
        if self.incremental_required_records > 0:
            # 根据 base entity 类型获取 base data
            if self.is_base_kline:
                base_data = self.data_cache.get('klines', {}).get(self.base_term, [])
            else:
                # 非 kline 类型的 base entity
                base_data = self.data_cache.get(self.base_data_source, [])
            
            if base_data:
                first_record = base_data[0]
                # 根据数据源类型获取日期字段
                if self.is_base_kline:
                    first_date = first_record.get('date', '')
                else:
                    # 非 kline 类型，可能是 'date' 或 'quarter' 字段
                    first_date = first_record.get('date') or first_record.get('quarter', '')
                    # 如果是 quarter，需要转换为日期（取该季度的第一天）
                    if first_date and len(first_date) > 4 and first_date[4] == 'Q':
                        # 格式：2024Q1 -> 20240101
                        year = first_date[:4]
                        quarter = int(first_date[5])
                        month = (quarter - 1) * 3 + 1
                        first_date = f"{year}{month:02d}01"
                
                if first_date:
                    lookback_start_date = first_date
                    logger.debug(f"INCREMENTAL 模式：base data 第一个记录时间={lookback_start_date}，将用于加载 required_data 的起始时间")
        
        # 确定实际使用的起始日期
        # 在 INCREMENTAL 模式下，如果有 lookback_start_date，使用它；否则使用 as_of_date
        # 在 REFRESH 模式下，直接使用 as_of_date
        effective_start_date = lookback_start_date if lookback_start_date else None
        
        for data_type in self.required_data:
            try:
                if data_type == 'corporate_finance':
                    finance_model = self.data_mgr.get_model('corporate_finance')
                    if finance_model:
                        # 加载季度数据
                        # 在 INCREMENTAL 模式下，如果有 lookback_start_date，从对应的季度开始加载
                        end_quarter = self._date_to_quarter(as_of_date)
                        if effective_start_date:
                            start_quarter = self._date_to_quarter(effective_start_date)
                            # 从 start_quarter 到 end_quarter 的所有数据
                            finance_data = finance_model.load(
                                condition="id = %s AND quarter >= %s AND quarter <= %s",
                                params=(self.entity_id, start_quarter, end_quarter),
                                order_by="quarter ASC"
                            )
                        else:
                            # REFRESH 模式：加载所有季度数据到 as_of_date
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
                        # 加载日期数据
                        # 在 INCREMENTAL 模式下，如果有 lookback_start_date，从该日期开始加载
                        if effective_start_date:
                            # 从 lookback_start_date 到 as_of_date 的所有数据
                            market_value_data = market_value_model.load(
                                condition="id = %s AND date >= %s AND date <= %s",
                                params=(self.entity_id, effective_start_date, as_of_date),
                                order_by="date ASC"
                            )
                        else:
                            # REFRESH 模式：加载所有日期数据到 as_of_date
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
                            # 在 INCREMENTAL 模式下，如果有 lookback_start_date，从该日期开始加载
                            if effective_start_date:
                                other_data = model.load(
                                    condition="id = %s AND date >= %s AND date <= %s",
                                    params=(self.entity_id, effective_start_date, as_of_date),
                                    order_by="date ASC"
                                )
                            else:
                                # REFRESH 模式：加载所有日期数据到 as_of_date
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
    
    def initialize_for_incremental(self, start_date: str):
        """
        在 INCREMENTAL 模式下初始化数据加载
        
        策略：
        - 如果 use_chunk=True：加载当前 chunk 和前一个 chunk（共 2 个 chunk）
          * 先找到包含 start_date 的 chunk（通过日期范围查询找到对应的 offset）
          * 加载该 chunk（当前 chunk）
          * 加载前一个 chunk（offset - chunk_size）
        - 如果 use_chunk=False：全量加载到 start_date
        
        Args:
            start_date: 起始日期（INCREMENTAL 模式的开始时间）
        """
        if not self.is_base_kline:
            # 非 kline 类型，不需要特殊初始化
            return
        
        if self.use_chunk:
            # Chunk 模式：加载当前 chunk 和前一个 chunk
            # 1. 先找到包含 start_date 的 chunk 的 offset
            # 通过查询数据库，找到 start_date 之前的记录数，从而确定 offset
            kline_model = self.data_mgr.get_model('stock_kline')
            if not kline_model:
                logger.warning(f"无法获取 kline model，跳过初始化")
                return
            
            # 查询 start_date 之前的记录数，确定 offset
            kline_terms = set([self.base_term] + self.required_terms)
            initial_offset = {}
            
            for term in kline_terms:
                try:
                    # 查询 start_date 之前有多少条记录
                    all_data_before = kline_model.load(
                        condition="id = %s AND term = %s AND date < %s",
                        params=(self.entity_id, term, start_date),
                        order_by="date ASC"
                    )
                    initial_offset[term] = len(all_data_before) if all_data_before else 0
                except Exception as e:
                    logger.warning(f"查询 {term} 的初始 offset 失败: {e}")
                    initial_offset[term] = 0
            
            # 2. 加载前一个 chunk（如果需要）
            previous_slice = {}
            if self.incremental_required_records > 0:
                # 需要前一个 chunk
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
            
            # 3. 加载当前 chunk（包含 start_date 的 chunk）
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
            
            # 4. 合并数据并更新缓存
            if not self.data_cache:
                self.data_cache = {'klines': {}}
            
            if self.incremental_required_records > 0 and previous_slice:
                # 合并前一个 chunk 和当前 chunk
                for term in kline_terms:
                    prev_data = previous_slice.get(term, [])
                    curr_data = current_slice.get(term, [])
                    self.data_cache['klines'][term] = prev_data + curr_data
                self.chunk_count = 2
            else:
                # 只加载当前 chunk
                for term in kline_terms:
                    self.data_cache['klines'][term] = current_slice.get(term, [])
                self.chunk_count = 1
            
            # 5. 更新 slice_state（记录当前 chunk 的结束位置）
            for term in kline_terms:
                if term not in self.slice_state.get('klines', {}):
                    self.slice_state.setdefault('klines', {})[term] = 0
                # 更新到当前 chunk 的结束位置
                self.slice_state['klines'][term] = initial_offset[term] + len(current_slice.get(term, []))
        else:
            # 全量加载模式：直接加载所有数据到 start_date
            self._load_all_klines_upto(start_date)
    
    def get_trading_dates(self, start_date: str, end_date: str) -> List[str]:
        """
        获取交易日列表（基于 base entity 的时间轴）
        
        Args:
            start_date: 起始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
        
        Returns:
            List[str]: 交易日列表（YYYYMMDD 格式）
        """
        # 方案1：从数据缓存中提取（如果已加载）
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
                    if trading_dates:
                        return trading_dates
        
        # 方案2：如果缓存中没有数据，先加载数据再提取交易日
        # 先加载一个 chunk 的数据来获取交易日列表
        if not self.data_cache or 'klines' not in self.data_cache:
            # 加载初始数据切片
            initial_slice = self._load_data_slice()
            if initial_slice and 'klines' in initial_slice:
                if not self.data_cache:
                    self.data_cache = {'klines': {}}
                for term, new_data in initial_slice['klines'].items():
                    if term not in self.data_cache['klines']:
                        self.data_cache['klines'][term] = []
                    self.data_cache['klines'][term].extend(new_data)
                self.chunk_count = 1
        
        # 再次尝试从缓存中提取
        if self.data_cache and 'klines' in self.data_cache:
            base_kline = self.data_cache['klines'].get(self.base_term, [])
            if base_kline:
                all_dates = sorted(set(record.get('date', '') for record in base_kline if record.get('date')))
                if start_date and end_date:
                    trading_dates = [
                        date for date in all_dates
                        if start_date <= date <= end_date
                    ]
                    if trading_dates:
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
