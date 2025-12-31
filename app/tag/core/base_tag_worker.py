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
        # 注意：data_slice_size 在 _extract_settings 中提取，所以这里需要在 _extract_settings 之后初始化
        from app.tag.core.components.worker_helper.worker_data_manager import WorkerDataManager
        self.data_manager = WorkerDataManager(
            entity_id=self.entity_id,
            entity_type=self.entity_type,
            base_term=self.base_term,
            required_terms=self.required_terms,
            required_data=self.required_data,
            data_slice_size=self.data_slice_size,  # 从 settings 中读取，默认 1000
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
        
        # 数据切片大小配置（从 performance 中读取，默认 1000）
        self.data_slice_size = self.performance.get('data_slice_size', 1000)
        
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