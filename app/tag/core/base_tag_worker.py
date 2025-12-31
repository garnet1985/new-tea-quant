"""
Tag Worker 基类

职责：
1. 初始化（加载 settings，初始化 DataManager 和 TagDataService）
2. 数据加载（钩子函数，默认实现支持股票，从数据库加载）
3. 计算钩子（calculate_tag，用户实现）
4. 子进程 worker 方法（process_entity，处理单个 entity）
5. 其他钩子（初始化、清理、错误处理）

注意：
- Tag 系统是预计算系统，数据应该从数据库（通过 DataManager）加载
- 不使用第三方数据源（DataSourceManager）
- 配置验证和处理逻辑已提取到 SettingsManager
- 元信息管理、版本变更处理等已移到 TagMetaManager
- 这是子进程 worker 基类，会在子进程中实例化
- 包含 tracker 等子进程状态管理
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple, Type
import inspect
import logging
from app.tag.core.enums import UpdateMode
from app.tag.core.components.settings_management.setting_manager import SettingsManager
from app.data_manager import DataManager

logger = logging.getLogger(__name__)


class BaseTagWorker(ABC):
    """
    Tag Worker 基类（子进程 worker）
    
    职责：
    1. 初始化（加载 settings，初始化 DataManager 和 TagDataService）
    2. 数据加载（钩子函数，默认实现支持股票，从数据库加载）
    3. 计算钩子（calculate_tag，用户实现）
    4. 子进程 worker 方法（process_entity，处理单个 entity）
    5. 其他钩子（初始化、清理、错误处理）
    
    注意：
    - Tag 系统是预计算系统，数据应该从数据库（通过 DataManager）加载
    - 不使用第三方数据源（DataSourceManager）
    - 元信息管理、版本变更处理等已移到 TagMetaManager
    - 这是子进程 worker，会在子进程中实例化
    - 包含 tracker 等子进程状态管理
    """
    
    def __init__(self, job_payload: Dict[str, Any]):
        """
        初始化 TagWorker
        
        Args:
            job_payload: Job payload 字典，包含：
                - entity_id: 实体ID
                - entity_type: 实体类型
                - scenario_name: Scenario 名称
                - scenario_version: Scenario 版本
                - tag_definitions: Tag Definition 列表
                - start_date: 起始日期
                - end_date: 结束日期
                - settings: Settings 字典（完整的 settings 配置）
        
        注意：
        - DataManager 是单例模式，自动初始化
        - 在子进程中实例化，进程结束后自动清理
        """
        self.job_payload = job_payload
        
        # 从 payload 提取常用字段
        self.entity_id = job_payload.get('entity_id')
        self.entity_type = job_payload.get('entity_type', 'stock')
        self.tag_definitions = job_payload.get('tag_definitions', [])
        self.settings = job_payload.get('settings', {})
        
        # 初始化服务
        self.data_mgr = DataManager(is_verbose=False)
        self.tag_data_service = self.data_mgr.get_tag_service()
        
        # 状态管理
        self.tracker = {}  # 用于存储计算过程中的临时状态
        
        # 处理 settings，提取配置
        self._extract_settings()
        
        # 初始化数据管理器（负责所有数据加载、缓存、过滤逻辑）
        from app.tag.core.components.worker_helper.worker_data_manager import WorkerDataManager
        self.data_manager = WorkerDataManager(
            entity_id=self.entity_id,
            entity_type=self.entity_type,
            base_term=self.base_term,
            required_terms=self.required_terms,
            required_data=self.required_data,
            data_slice_size=1000,  # 每次加载1000条记录
            data_mgr=self.data_mgr
        )
        
        # 调用初始化钩子
        self.on_init()
    
    def _extract_settings(self):
        """从 settings 中提取配置到实例变量"""
        calculator_config = self.settings.get('calculator', {})
        scenario_config = self.settings.get('scenario', {})
        
        # 基础配置
        self.scenario_name = scenario_config.get('name', '')
        self.scenario_version = scenario_config.get('version', '1.0')
        self.base_term = calculator_config.get('base_term', 'daily')
        self.required_terms = calculator_config.get('required_terms', [])
        self.required_data = calculator_config.get('required_data', [])
        
        # 业务配置
        self.core = calculator_config.get('core', {})
        self.performance = calculator_config.get('performance', {})
        
        # 处理 tags 配置（合并 worker 级别和 tag 级别）
        self.tags_config = []
        tags_info = self.settings.get('tags', [])
        for tag_info in tags_info:
            tag_config = {
                'tag_meta': tag_info,
                'base_term': self.base_term,
                'required_terms': self.required_terms,
                'required_data': self.required_data,
                'core': self.core,
                'performance': self.performance,
            }
            self.tags_config.append(tag_config)
    
    # ========================================================================
    # 子进程 Worker 方法（主执行流程）
    # ========================================================================
    
    def run(self):
        """
        运行 Tag Worker（主入口）
        
        执行流程：
        1. 预处理：加载全量历史数据
        2. 执行 tagging：遍历时间轴，计算所有 tags
        3. 后处理：批量保存、清理资源
        """
        self._preprocess()
        self._execute_tagging()
        self._postprocess()
    
    def _preprocess(self):
        """
        预处理：初始化数据管理器
        
        注意：
        - 数据加载逻辑已迁移到 WorkerDataManager
        - 这里只获取交易日列表，不加载数据
        """
        # 获取交易日列表（基于 base entity 的时间轴）
        self.trading_dates = self.data_manager.get_trading_dates(
            self.job_payload.get('start_date'),
            self.job_payload.get('end_date')
        )
        
        self.on_before_execute_tagging()
    
    def _execute_tagging(self):
        """
        执行 tagging：遍历时间轴，计算所有 tags
        
        流程：
        1. 遍历 base entity 的每个交易日（as_of_date）
        2. 按需加载数据切片（避免内存爆炸）
        3. 使用 time_cursor 高效过滤数据到当前日期（避免重复遍历）
        4. 对每个 tag 调用 calculate_tag_values() 计算
        5. 收集所有 tag values，最后批量保存
        """
        all_tag_values = []  # 收集所有 tag 值，最后批量保存
        
        for as_of_date in self.trading_dates:
            # 1. 使用数据管理器获取过滤后的数据（自动处理数据加载和过滤）
            #    数据管理器会：
            #    - 按需加载数据切片（避免内存爆炸）
            #    - 使用 cursor 高效过滤数据到当前日期（避免重复遍历）
            filtered_data = self.data_manager.filter_data_to_date(as_of_date)
            
            # 2. 对每个 tag 进行计算
            for tag_def, tag_config in zip(self.tag_definitions, self.tags_config):
                try:
                    # calculate_tag 返回 tag values 列表（可能为空）
                    tag_values = self.calculate_tag_values(
                        entity_id=self.entity_id,
                        entity_type=self.entity_type,
                        as_of_date=as_of_date,
                        historical_data=filtered_data,  # 已过滤到 as_of_date
                        tag_definition=tag_def,  # 当前计算的 tag definition
                        tag_config=tag_config  # 对应的 tag 配置
                    )
                    
                    if tag_values:
                        # 为每个 tag value 添加必要信息
                        for tag_value in tag_values:
                            tag_value['tag_definition_id'] = tag_def['id']
                            tag_value['entity_id'] = self.entity_id
                            tag_value['entity_type'] = self.entity_type
                            tag_value['as_of_date'] = as_of_date
                            all_tag_values.append(tag_value)
                            
                            # 调用钩子（单个 tag 创建后）
                            self.on_tag_created(tag_value, self.entity_id, as_of_date)
                    
                except Exception as e:
                    # 错误处理
                    self.on_calculate_error(self.entity_id, as_of_date, e, tag_def)
                    if not self.should_continue_on_error():
                        raise  # 中断计算
            
            # 调用钩子（单个 as_of_date 计算完成后）
            self.on_as_of_date_calculate_complete(as_of_date)
        
        # 3. 批量保存所有 tag 值（减少 IO 频率）
        if all_tag_values:
            self._batch_save_tag_values(all_tag_values)
    
    def _postprocess(self):
        """
        后处理：清理资源、统计信息等
        """
        self.on_after_execute_tagging()
    
    # ========================================================================
    # 用户需要实现的方法
    # ========================================================================
    
    @abstractmethod
    def calculate_tag_values(
        self,
        entity_id: str,
        entity_type: str,
        as_of_date: str,
        historical_data: Dict[str, Any],
        tag_definition: Dict[str, Any],
        tag_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        计算 tag 值（用户实现）
        
        注意：
        - 一个 worker 可能产生多个 tags，因此返回列表
        - 如果当前 as_of_date 不产生 tag，返回空列表 []
        - historical_data 已经过滤到 as_of_date，确保只使用历史数据
        
        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            as_of_date: 业务日期（YYYYMMDD）
            historical_data: 历史数据字典（已过滤到 as_of_date）
                - historical_data["klines"]: K 线数据字典，key 为 term（如 "daily", "weekly"）
                - historical_data["finance"]: 财务数据（如果 required_data 包含 "corporate_finance"）
                - 其他数据源...
            tag_definition: Tag Definition 字典（从数据库加载）
            tag_config: Tag 配置（已合并 worker 和 tag 配置）
        
        Returns:
            List[Dict[str, Any]]: Tag 值列表，每个元素格式：
                {
                    'value': str,  # 标签值（必需）
                    'start_date': str,  # 可选，起始日期（YYYYMMDD）
                    'end_date': str,  # 可选，结束日期（YYYYMMDD）
                }
                如果当前 as_of_date 不产生 tag，返回空列表 []
        """
        pass
    
    # ========================================================================
    # 数据保存方法
    # ========================================================================
    
    def _batch_save_tag_values(self, tag_values: List[Dict[str, Any]]):
        """
        批量保存 tag 值
        
        Args:
            tag_values: Tag 值列表，每个元素包含：
                - tag_definition_id: int
                - entity_id: str
                - entity_type: str
                - as_of_date: str
                - value: str
                - start_date: str (可选)
                - end_date: str (可选)
        """
        if not tag_values:
            return
        
        try:
            self.tag_data_service.batch_save_tag_values(tag_values)
            logger.debug(f"批量保存 tag 值成功: entity_id={self.entity_id}, count={len(tag_values)}")
        except Exception as e:
            logger.error(f"批量保存 tag 值失败: entity_id={self.entity_id}, error={e}", exc_info=True)
            raise
    
    # ========================================================================
    # 钩子函数（用户可选实现）
    # ========================================================================
    
    def on_init(self):
        """
        初始化钩子（在 __init__ 最后调用）
        
        用于：
        - 初始化缓存
        - 预加载数据
        - 其他初始化操作
        """
        pass
    
    def on_before_execute_tagging(self):
            # 加载新数据切片（从 slice_state 记录的索引开始）
            new_slice = self._load_data_slice(
                entity_id=self.entity_id,
                entity_type=self.entity_type,
                base_term=self.base_term,
                required_terms=self.required_terms,
                required_data=self.required_data
            )
            
            # 合并到现有缓存（追加新数据）
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
                
                # 合并其他数据源（required_data）
                # 注意：required_data 是按时间范围加载的，可能会有时间范围重叠
                # 需要去重或合并，避免重复数据
                for key, new_data in new_slice.items():
                    if key != 'klines':
                        if key in self.data_cache:
                            if isinstance(new_data, list) and isinstance(self.data_cache[key], list):
                                # 合并列表，需要去重（根据唯一键，如 date 或 quarter）
                                existing_data = self.data_cache[key]
                                # 创建现有数据的唯一键集合（用于快速查找）
                                if existing_data:
                                    # 根据数据源类型选择唯一键
                                    unique_key = self._get_unique_key_for_data_type(key)
                                    existing_keys = {
                                        self._extract_unique_key(record, unique_key)
                                        for record in existing_data
                                        if self._extract_unique_key(record, unique_key)
                                    }
                                    
                                    # 只添加不重复的新数据
                                    for record in new_data:
                                        record_key = self._extract_unique_key(record, unique_key)
                                        if record_key and record_key not in existing_keys:
                                            existing_data.append(record)
                                            existing_keys.add(record_key)
                                    
                                    self.data_cache[key] = existing_data
                                else:
                                    self.data_cache[key] = new_data
                            else:
                                # 非列表类型，直接替换
                                self.data_cache[key] = new_data
                        else:
                            self.data_cache[key] = new_data
            
            # 更新 slice_state（记录已加载到的全局索引）
            self._update_slice_state(new_slice)
            
            # 注意：time_cursor 不需要重置
            # time_cursor 记录的是在整个 data_cache 中的索引位置（不是相对于单个切片的）
            # 由于我们追加数据到缓存，cursor 可以继续使用，指向合并后的数据位置
            # _filter_data_to_date_with_cursor 会从 cursor 位置继续遍历
    
    def _load_data_slice(
        self,
        entity_id: str,
        entity_type: str,
        base_term: str,
        required_terms: List[str],
        required_data: List[str]
    ) -> Dict[str, Any]:
        """
        加载数据切片（按记录数，每次1000条）
        
        加载策略：
        1. Base entity（klines）按记录数切片（1000条）
           - 从 slice_state 记录的全局索引开始
           - 使用 offset 和 limit 精准切片
        
        2. Required data 按时间范围加载（与 base entity 对齐）
           - 从 base entity 的切片中提取时间范围（第一条和最后一条记录的日期）
           - 根据这个时间范围加载 required_data，确保时间轴对齐
        
        这样设计的原因：
        - Base entity 是时间轴，按记录数切片可以精准控制内存
        - Required data 需要与 base entity 的时间范围对齐，才能正确过滤到 as_of_date
        - 如果 required data 也按记录数切片，可能导致时间轴不对齐
        
        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            base_term: 基础周期
            required_terms: 需要的其他周期
            required_data: 需要的数据源
        
        Returns:
            Dict[str, Any]: 数据切片，格式与 _load_full_historical_data 相同
        """
        historical_data = {}
        
        # 1. 加载 K 线数据（base entity + required_terms）
        kline_terms = set([base_term] + (required_terms or []))
        klines = {}
        
        for term in kline_terms:
            try:
                # 从 slice_state 获取当前已加载到的全局索引
                global_offset = self.slice_state.get('klines', {}).get(term, 0)
                
                # 直接使用 model 加载数据切片（支持 offset 和 limit）
                kline_model = self.data_mgr.get_model('stock_kline')
                if kline_model:
                    # 按记录数切片：从 global_offset 开始，加载 data_slice_size 条记录
                    # 注意：需要按日期排序，确保数据顺序正确
                    # 还需要按 term 过滤（stock_kline 表中有 term 字段）
                    condition = "id = %s AND term = %s"
                    params = (entity_id, term)
                    
                    kline_data = kline_model.load(
                        condition=condition,
                        params=params,
                        order_by="date ASC",  # 按日期升序，确保数据顺序
                        limit=self.data_slice_size,
                        offset=global_offset
                    )
                else:
                    kline_data = []
                klines[term] = kline_data or []
            except Exception as e:
                logger.warning(f"加载 K 线数据失败: entity_id={entity_id}, term={term}, error={e}")
                klines[term] = []
        
        historical_data['klines'] = klines
        
        # 2. 从 base entity 的切片中提取时间范围
        #    用于加载 required_data，确保时间轴对齐
        base_kline_data = klines.get(base_term, [])
        if base_kline_data:
            # 获取第一条和最后一条记录的日期
            first_date = base_kline_data[0].get('date', '') if base_kline_data else ''
            last_date = base_kline_data[-1].get('date', '') if base_kline_data else ''
            time_range = (first_date, last_date)
        else:
            # 如果 base entity 没有数据，无法确定时间范围
            time_range = (None, None)
        
        # 3. 加载 required_data 里的其他 entity 数据
        #    根据 base entity 的时间范围加载，确保时间轴对齐
        for data_type in (required_data or []):
            try:
                if not time_range[0] or not time_range[1]:
                    # 如果无法确定时间范围，跳过加载
                    historical_data[data_type] = []
                    continue
                
                start_date, end_date = time_range
                
                if data_type == 'corporate_finance':
                    # 加载财务数据（按时间范围，与 base entity 对齐）
                    # 财务数据通常是按季度存储，需要加载覆盖该时间范围的所有季度数据
                    finance_model = self.data_mgr.get_model('corporate_finance')
                    if finance_model:
                        # 将日期范围转换为季度范围
                        start_quarter = self._date_to_quarter(start_date)
                        end_quarter = self._date_to_quarter(end_date)
                        
                        # 加载该季度范围内的所有财务数据
                        # 注意：财务数据可能不是每个季度都有，所以加载所有覆盖该时间范围的季度
                        finance_data = finance_model.load(
                            condition="id = %s AND quarter >= %s AND quarter <= %s",
                            params=(entity_id, start_quarter, end_quarter),
                            order_by="quarter ASC"
                        )
                    else:
                        finance_data = []
                    historical_data['finance'] = finance_data
                
                elif data_type == 'market_value':
                    # 加载市值数据（按时间范围，与 base entity 对齐）
                    market_value_model = self.data_mgr.get_model('market_value')
                    if market_value_model:
                        market_value_data = market_value_model.load(
                            condition="id = %s AND date BETWEEN %s AND %s",
                            params=(entity_id, start_date, end_date),
                            order_by="date ASC"
                        )
                    else:
                        market_value_data = []
                    historical_data['market_value'] = market_value_data
                
                # 其他数据源...
                # 通用处理：如果有对应的 model，按时间范围加载
                else:
                    # 尝试通过 model 加载
                    model = self.data_mgr.get_model(data_type)
                    if model:
                        # 假设有 date 字段
                        try:
                            other_data = model.load(
                                condition="id = %s AND date BETWEEN %s AND %s",
                                params=(entity_id, start_date, end_date),
                                order_by="date ASC"
                            )
                            historical_data[data_type] = other_data
                        except Exception:
                            # 如果失败，可能是字段名不同，记录警告
                            logger.warning(f"无法按时间范围加载 {data_type} 数据，字段可能不匹配")
                            historical_data[data_type] = []
                    else:
                        historical_data[data_type] = []
                
            except Exception as e:
                logger.warning(f"加载 {data_type} 数据失败: entity_id={entity_id}, error={e}")
                historical_data[data_type] = []
        
        return historical_data
    
    def _date_to_quarter(self, date_str: str) -> str:
        """
        将日期（YYYYMMDD）转换为季度（YYYYQ[1-4]）
        
        Args:
            date_str: 日期字符串（YYYYMMDD）
        
        Returns:
            str: 季度字符串（YYYYQ[1-4]），例如 "2024Q1"
        """
        if not date_str or len(date_str) != 8:
            return ''
        
        year = int(date_str[:4])
        month = int(date_str[4:6])
        
        # 计算季度
        quarter = (month - 1) // 3 + 1
        return f"{year}Q{quarter}"
    
    def _get_unique_key_for_data_type(self, data_type: str) -> str:
        """
        获取数据源类型的唯一键字段名
        
        Args:
            data_type: 数据源类型（如 'finance', 'market_value'）
        
        Returns:
            str: 唯一键字段名（如 'date', 'quarter'）
        """
        # 根据数据源类型返回对应的唯一键字段
        if data_type == 'corporate_finance':
            return 'quarter'  # 财务数据按季度
        else:
            return 'date'  # 其他数据源默认按日期
    
    def _extract_unique_key(self, record: Dict[str, Any], unique_key: str) -> Optional[str]:
        """
        从记录中提取唯一键值
        
        Args:
            record: 数据记录字典
            unique_key: 唯一键字段名
        
        Returns:
            Optional[str]: 唯一键值，如果不存在返回 None
        """
        return record.get(unique_key)
    
    def _update_slice_state(self, new_slice: Dict[str, Any]):
        """
        更新切片状态（记录已加载到的全局索引）
        
        注意：
        - 只更新 base entity（klines）的 slice_state，因为它是按记录数切片的
        - required_data 不更新 slice_state，因为它们按时间范围加载，不需要记录索引
        
        Args:
            new_slice: 新加载的数据切片
        """
        # 只更新 K 线数据的 slice_state（base entity 按记录数切片）
        if 'klines' in new_slice:
            for term, data_list in new_slice['klines'].items():
                if term in self.slice_state.get('klines', {}):
                    # 增加已加载的记录数
                    self.slice_state['klines'][term] += len(data_list)
                else:
                    self.slice_state.setdefault('klines', {})[term] = len(data_list)
        
        # required_data 不更新 slice_state，因为它们按时间范围加载
        # 每次加载时都根据 base entity 的时间范围重新加载
    
    def _load_full_historical_data(
        self,
        entity_id: str,
        entity_type: str,
        base_term: str,
        required_terms: List[str],
        required_data: List[str],
        end_date: str = None
    ) -> Dict[str, Any]:
        """
        加载全量历史数据
        
        加载两种数据：
        1. Base entity 数据（如股票日线）- 作为时间轴
        2. Required data 里的 entity 数据（如财务数据、市值等）
        
        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            base_term: 基础周期（如 "daily"）
            required_terms: 需要的其他周期（如 ["weekly", "monthly"]）
            required_data: 需要的数据源（如 ["corporate_finance", "market_value"]）
            end_date: 截止日期（YYYYMMDD），加载到此日期的所有历史数据
        
        Returns:
            Dict[str, Any]: 历史数据字典，格式：
                {
                    "klines": {
                        "daily": List[Dict],  # base entity 数据
                        "weekly": List[Dict],  # required_terms
                        ...
                    },
                    "finance": List[Dict],  # 如果 required_data 包含 "corporate_finance"
                    "market_value": List[Dict],  # 如果 required_data 包含 "market_value"
                    ...
                }
        """
        historical_data = {}
        
        # 1. 加载 K 线数据（base entity + required_terms）
        kline_terms = set([base_term] + (required_terms or []))
        klines = {}
        
        for term in kline_terms:
            try:
                # 通过 DataManager 加载 K 线数据
                stock_service = self.data_mgr.get_data_service('stock_related.stock')
                if stock_service:
                    kline_data = stock_service.load_kline(
                        stock_id=entity_id,
                        term=term,
                        end_date=end_date
                    )
                else:
                    # 备用方案：直接使用 model
                    kline_model = self.data_mgr.get_model('stock_kline')
                    if kline_model:
                        # TODO: 实现按 term 和 end_date 过滤的查询
                        kline_data = []
                    else:
                        kline_data = []
                klines[term] = kline_data or []
            except Exception as e:
                logger.warning(f"加载 K 线数据失败: entity_id={entity_id}, term={term}, error={e}")
                klines[term] = []
        
        historical_data['klines'] = klines
        
        # 2. 加载 required_data 里的其他 entity 数据
        for data_type in (required_data or []):
            try:
                if data_type == 'corporate_finance':
                    # 加载财务数据
                    finance_service = self.data_mgr.get_data_service('corporate_finance')
                    if finance_service:
                        # TODO: 实现按 end_date 过滤的财务数据加载
                        # 财务数据通常是按季度，需要特殊处理
                        finance_data = []
                    else:
                        finance_data = []
                    historical_data['finance'] = finance_data
                
                elif data_type == 'market_value':
                    # 加载市值数据
                    # TODO: 实现市值数据加载
                    historical_data['market_value'] = []
                
                # 其他数据源...
                
            except Exception as e:
                logger.warning(f"加载 {data_type} 数据失败: entity_id={entity_id}, error={e}")
                historical_data[data_type] = []
        
        return historical_data
    
    def _filter_data_to_date_with_cursor(
        self,
        historical_data: Dict[str, Any],
        as_of_date: str
    ) -> Dict[str, Any]:
        """
        使用 time_cursor 高效过滤数据到指定日期（避免"上帝模式"）
        
        从上次 cursor 位置继续遍历，避免重复扫描已处理的数据。
        这是性能优化的关键：不再每次都从头遍历，而是从上次位置继续。
        
        Args:
            historical_data: 当前数据切片（从 _load_data_slice 加载）
            as_of_date: 业务日期（YYYYMMDD）
        
        Returns:
            Dict[str, Any]: 过滤后的数据，格式与 historical_data 相同
        """
        filtered_data = {}
        
        # 1. 过滤 K 线数据（使用 cursor 优化）
        if 'klines' in historical_data:
            filtered_klines = {}
            for term, kline_list in historical_data['klines'].items():
                # 从 cursor 位置继续遍历
                cursor_key = f'klines.{term}'
                start_idx = self.time_cursor.get('klines', {}).get(term, 0)
                
                # 从上次位置继续，找到所有 date <= as_of_date 的记录
                filtered_records = []
                current_idx = start_idx
                
                while current_idx < len(kline_list):
                    record = kline_list[current_idx]
                    record_date = record.get('date', '')
                    
                    if record_date <= as_of_date:
                        filtered_records.append(record)
                        current_idx += 1
                    else:
                        # 遇到第一个超过 as_of_date 的记录，停止
                        break
                
                # 更新 cursor
                if 'klines' not in self.time_cursor:
                    self.time_cursor['klines'] = {}
                self.time_cursor['klines'][term] = current_idx
                
                filtered_klines[term] = filtered_records
            
            filtered_data['klines'] = filtered_klines
        
        # 2. 过滤其他数据源（使用 cursor 优化）
        for key, data_list in historical_data.items():
            if key == 'klines':
                continue  # 已处理
            
            if isinstance(data_list, list):
                # 从 cursor 位置继续遍历
                start_idx = self.time_cursor.get(key, 0)
                
                # 根据数据源类型选择日期字段
                date_field = 'date'  # 默认
                if key == 'finance':
                    # 财务数据可能需要按季度处理
                    # TODO: 实现财务数据的日期过滤逻辑
                    date_field = 'quarter'  # 示例
                
                filtered_records = []
                current_idx = start_idx
                
                while current_idx < len(data_list):
                    record = data_list[current_idx]
                    record_date = record.get(date_field, '')
                    
                    if self._compare_date(record_date, as_of_date):
                        filtered_records.append(record)
                        current_idx += 1
                    else:
                        # 遇到第一个超过 as_of_date 的记录，停止
                        break
                
                # 更新 cursor
                self.time_cursor[key] = current_idx
                filtered_data[key] = filtered_records
            else:
                filtered_data[key] = data_list
        
        return filtered_data
    
    def _filter_data_to_date(
        self,
        historical_data: Dict[str, Any],
        as_of_date: str
    ) -> Dict[str, Any]:
        """
        过滤数据到指定日期（避免"上帝模式"）- 旧版本，不使用 cursor
        
        注意：此方法已废弃，保留仅用于兼容。新代码应使用 _filter_data_to_date_with_cursor。
        """
        filtered_data = {}
        
        # 1. 过滤 K 线数据（按 date 字段）
        if 'klines' in historical_data:
            filtered_klines = {}
            for term, kline_list in historical_data['klines'].items():
                # 筛选 date <= as_of_date 的记录
                filtered_klines[term] = [
                    record for record in kline_list
                    if record.get('date', '') <= as_of_date
                ]
            filtered_data['klines'] = filtered_klines
        
        # 2. 过滤其他数据源（按各自的日期字段）
        for key, data_list in historical_data.items():
            if key == 'klines':
                continue  # 已处理
            
            if isinstance(data_list, list):
                # 根据数据源类型选择日期字段
                date_field = 'date'  # 默认
                if key == 'finance':
                    # 财务数据可能需要按季度处理
                    # TODO: 实现财务数据的日期过滤逻辑
                    date_field = 'quarter'  # 示例
                
                filtered_data[key] = [
                    record for record in data_list
                    if self._compare_date(record.get(date_field, ''), as_of_date)
                ]
            else:
                filtered_data[key] = data_list
        
        return filtered_data
    
    def _compare_date(self, date1: str, date2: str) -> bool:
        """
        比较日期（date1 <= date2）
        
        支持不同格式的日期比较：
        - YYYYMMDD
        - YYYYQ[1-4] (季度)
        - 其他格式...
        """
        # 简单实现：字符串比较（适用于 YYYYMMDD）
        if len(date1) == 8 and len(date2) == 8:
            return date1 <= date2
        
        # TODO: 实现季度等其他格式的比较
        return True
    
    def _get_trading_dates(self, start_date: str, end_date: str) -> List[str]:
        """
        获取交易日列表（基于 base entity 的时间轴）
        
        注意：由于使用切片加载，不能从 full_historical_data 中提取。
        改为从 DataManager 获取交易日历，或从第一次加载的数据切片中提取。
        
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
        
        # 方案2：从第一次加载的数据切片中提取（如果 DataManager 不支持）
        # 先加载一个小的数据切片来获取交易日列表
        if not hasattr(self, 'data_cache') or not self.data_cache:
            # 加载第一个切片（从 start_date 到 start_date + 1年）
            temp_end_date = self._add_years_to_date(start_date, 1)
            if temp_end_date > end_date:
                temp_end_date = end_date
            
            temp_slice = self._load_data_slice(
                entity_id=self.entity_id,
                entity_type=self.entity_type,
                base_term=self.base_term,
                required_terms=self.required_terms,
                required_data=self.required_data,
                start_date=start_date,
                end_date=temp_end_date
            )
            
            # 从切片中提取交易日
            if 'klines' in temp_slice:
                base_kline = temp_slice['klines'].get(self.base_term, [])
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
    
    def _add_years_to_date(self, date_str: str, years: int) -> str:
        """
        在日期上添加年数
        
        Args:
            date_str: 日期字符串（YYYYMMDD）
            years: 要添加的年数
        
        Returns:
            str: 新的日期字符串（YYYYMMDD）
        """
        if len(date_str) != 8:
            return date_str
        
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        
        new_year = year + years
        return f"{new_year:04d}{month:02d}{day:02d}"
    
    def _batch_save_tag_values(self, tag_values: List[Dict[str, Any]]):
        """
        批量保存 tag 值
        
        Args:
            tag_values: Tag 值列表，每个元素包含：
                - tag_definition_id: int
                - entity_id: str
                - entity_type: str
                - as_of_date: str
                - value: str
                - start_date: str (可选)
                - end_date: str (可选)
        """
        if not tag_values:
            return
        
        try:
            self.tag_data_service.batch_save_tag_values(tag_values)
            logger.debug(f"批量保存 tag 值成功: entity_id={self.entity_id}, count={len(tag_values)}")
        except Exception as e:
            logger.error(f"批量保存 tag 值失败: entity_id={self.entity_id}, error={e}", exc_info=True)
            raise
    
    # ========================================================================
    # 钩子函数（用户可选实现）
    # ========================================================================
    
    def on_init(self):
        """
        初始化钩子（在 __init__ 最后调用）
        
        用于：
        - 初始化缓存
        - 预加载数据
        - 其他初始化操作
        """
        pass
    
    def on_before_execute_tagging(self):
        """
        开始执行 tagging 前的钩子（数据加载完成后）
        
        用于：
        - 数据预处理
        - 初始化计算状态
        - 其他准备工作
        """
        pass
    
    def on_tag_created(self, tag_value: Dict[str, Any], entity_id: str, as_of_date: str):
        """
        单个 tag 创建后的钩子
        
        Args:
            tag_value: 创建的 tag 值字典
            entity_id: 实体ID
            as_of_date: 业务日期
        """
        pass
    
    def on_as_of_date_calculate_complete(self, as_of_date: str):
        """
        单个 as_of_date 计算完成后的钩子
        
        Args:
            as_of_date: 业务日期
        """
        pass
    
    def on_calculate_error(
        self,
        entity_id: str,
        as_of_date: str,
        error: Exception,
        tag_definition: Dict[str, Any]
    ):
        """
        计算错误钩子
        
        Args:
            entity_id: 实体ID
            as_of_date: 业务日期
            error: 异常对象
            tag_definition: Tag Definition 字典
        """
        logger.error(
            f"计算 tag 失败: entity_id={entity_id}, as_of_date={as_of_date}, "
            f"tag={tag_definition.get('name')}, error={error}",
            exc_info=True
        )
    
    def should_continue_on_error(self) -> bool:
        """
        错误时是否继续（默认 True）
        
        Returns:
            True: 遇到错误时继续计算下一个时间点
            False: 遇到错误时中断计算
        """
        return True
    
    def on_after_execute_tagging(self):
        """
        执行 tagging 完成后的钩子
        
        用于：
        - 记录统计信息
        - 清理资源
        - 其他收尾操作
        """
        pass