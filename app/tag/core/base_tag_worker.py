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
from app.tag.core.models.tag_model import TagModel

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
        # tag_definitions 从字典转换为 TagModel 对象
        tag_defs_dict = job_payload.get('tag_definitions', [])
        self.tag_definitions = [TagModel.from_dict(t) for t in tag_defs_dict]
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
    
    # ==================== 生命周期方法 ====================
    
    def process_entity(self) -> Dict[str, Any]:
        """
        处理单个 entity 的 tag 计算（子进程 worker）
        
        这是子进程的主要入口方法，由 ProcessWorker 调用。
        
        流程：
        1. 预处理（_preprocess）：获取交易日列表，调用 on_before_execute_tagging
        2. 执行标签计算（_execute_tagging）：遍历每个日期，计算 tags
        3. 后处理（_postprocess）：批量保存结果，调用 on_after_execute_tagging
        
        Returns:
            Dict[str, Any]: 执行结果统计信息
                {
                    "entity_id": str,
                    "entity_type": str,
                    "scenario_name": str,
                    "total_dates": int,
                    "processed_dates": int,
                    "total_tags_created": int,
                    "errors": List[str],
                    "success": bool
                }
        """
        try:
            # 1. 预处理
            self._preprocess()
            
            # 2. 执行标签计算
            result = self._execute_tagging()
            
            # 3. 后处理
            self._postprocess(result)
            
            return result
        except Exception as e:
            logger.error(
                f"处理 entity 失败: entity_id={self.entity_id}, "
                f"scenario_name={self.scenario_name}, error={e}",
                exc_info=True
            )
            return {
                "entity_id": self.entity_id,
                "entity_type": self.entity_type,
                "scenario_name": self.scenario_name,
                "total_dates": 0,
                "processed_dates": 0,
                "total_tags_created": 0,
                "errors": [str(e)],
                "success": False
            }
    
    def _preprocess(self):
        """
        预处理阶段
        
        1. 获取交易日列表
        2. 调用 on_before_execute_tagging 钩子
        """
        # 获取交易日列表
        start_date = self.job_payload.get('start_date')
        end_date = self.job_payload.get('end_date')
        self.trading_dates = self.data_manager.get_trading_dates(start_date, end_date)
        
        # 调用执行前钩子
        self.on_before_execute_tagging()
    
    def _execute_tagging(self) -> Dict[str, Any]:
        """
        执行标签计算阶段
        
        遍历每个交易日，对每个日期：
        1. 过滤数据到 as_of_date（保证一致性，不包含未来数据）
        2. 对每个 tag 调用 calculate_tag()
        3. 收集结果
        4. 调用 on_as_of_date_calculate_complete 钩子
        
        Returns:
            Dict[str, Any]: 执行结果统计信息
        """
        # 初始化结果统计
        total_dates = len(self.trading_dates)
        processed_dates = 0
        total_tags_created = 0
        errors = []
        tag_values_to_save = []  # 收集所有要保存的 tag values
        
        # 遍历每个交易日
        for as_of_date in self.trading_dates:
            try:
                # 1. 过滤数据到 as_of_date（保证一致性，不包含未来数据）
                filtered_data = self.data_manager.filter_data_to_date(as_of_date)
                
                # 2. 对每个 tag 调用 calculate_tag()
                for tag_config in self.tags_config:
                    tag_meta = tag_config.get('tag_meta', {})
                    tag_name = tag_meta.get('name', '')
                    
                    # 找到对应的 tag_definition
                    tag_definition = None
                    for tag_def in self.tag_definitions:
                        if tag_def.tag_name == tag_name:
                            tag_definition = tag_def
                            break
                    
                    if not tag_definition:
                        logger.warning(
                            f"未找到 tag definition: tag_name={tag_name}, "
                            f"entity_id={self.entity_id}, as_of_date={as_of_date}"
                        )
                        continue
                    
                    try:
                        # 调用用户实现的 calculate_tag 方法
                        tag_result = self.calculate_tag(
                            entity_id=self.entity_id,
                            entity_type=self.entity_type,
                            as_of_date=as_of_date,
                            historical_data=filtered_data,
                            tag_config=tag_config
                        )
                        
                        # 如果返回结果，创建 tag value
                        if tag_result is not None:
                            tag_value = {
                                "entity_id": self.entity_id,
                                "entity_type": self.entity_type,
                                "tag_definition_id": tag_definition.id,
                                "as_of_date": as_of_date,
                                "value": tag_result.get("value", ""),
                                "start_date": tag_result.get("start_date"),
                                "end_date": tag_result.get("end_date"),
                            }
                            tag_values_to_save.append(tag_value)
                            total_tags_created += 1
                            
                            # 调用 tag 创建后钩子
                            self.on_tag_created(
                                tag_name=tag_name,
                                as_of_date=as_of_date,
                                tag_value=tag_value,
                                tag_result=tag_result
                            )
                    
                    except Exception as e:
                        error_msg = (
                            f"计算 tag 失败: tag_name={tag_name}, "
                            f"entity_id={self.entity_id}, as_of_date={as_of_date}, error={e}"
                        )
                        logger.error(error_msg, exc_info=True)
                        errors.append(error_msg)
                        
                        # 调用错误处理钩子
                        should_continue = self.on_calculate_error(
                            tag_name=tag_name,
                            as_of_date=as_of_date,
                            error=e,
                            tag_config=tag_config
                        )
                        
                        if not should_continue:
                            # 如果钩子返回 False，停止处理该 tag
                            break
                
                # 3. 调用每个日期计算完成钩子
                self.on_as_of_date_calculate_complete(
                    as_of_date=as_of_date,
                    filtered_data=filtered_data,
                    tag_values_count=len(tag_values_to_save)
                )
                
                processed_dates += 1
                
            except Exception as e:
                error_msg = (
                    f"处理日期失败: entity_id={self.entity_id}, "
                    f"as_of_date={as_of_date}, error={e}"
                )
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
        
        # 保存所有 tag values（批量保存）
        self._tag_values_to_save = tag_values_to_save
        
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "scenario_name": self.scenario_name,
            "total_dates": total_dates,
            "processed_dates": processed_dates,
            "total_tags_created": total_tags_created,
            "errors": errors,
            "success": len(errors) == 0
        }
    
    def _postprocess(self, result: Dict[str, Any]):
        """
        后处理阶段
        
        1. 批量保存 tag values
        2. 调用 on_after_execute_tagging 钩子
        """
        # 批量保存 tag values
        if hasattr(self, '_tag_values_to_save') and self._tag_values_to_save:
            self._batch_save_tag_values(self._tag_values_to_save)
        
        # 调用执行后钩子
        self.on_after_execute_tagging(result)
    
    def _batch_save_tag_values(self, tag_values: List[Dict[str, Any]]):
        """
        批量保存 tag values
        
        Args:
            tag_values: Tag value 列表
        """
        if not tag_values:
            return
        
        try:
            self.tag_data_service.batch_save_tag_values(tag_values)
            logger.debug(
                f"批量保存 tag values 成功: entity_id={self.entity_id}, "
                f"count={len(tag_values)}"
            )
        except Exception as e:
            logger.error(
                f"批量保存 tag values 失败: entity_id={self.entity_id}, "
                f"count={len(tag_values)}, error={e}",
                exc_info=True
            )
            raise
    
    # ==================== 钩子函数（用户可重写） ====================
    
    def on_init(self):
        """
        初始化钩子
        
        在 __init__ 完成后调用，用户可以在这里进行自定义初始化。
        默认实现为空。
        """
        pass
    
    def on_before_execute_tagging(self):
        """
        执行标签计算前的钩子
        
        在获取交易日列表后、开始遍历日期前调用。
        用户可以在这里进行预处理，如初始化 tracker 等。
        默认实现为空。
        """
        pass
    
    @abstractmethod
    def calculate_tag(
        self,
        entity_id: str,
        entity_type: str,
        as_of_date: str,
        historical_data: Dict[str, Any],
        tag_config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        计算 tag（用户必须实现）
        
        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            as_of_date: 业务日期（YYYYMMDD格式）
            historical_data: 历史数据字典，包含：
                - klines: {term: [records]}  # K线数据
                - corporate_finance: [records]  # 财报数据（如果有）
                - market_value: [records]  # 市值数据（如果有）
                - 其他 required_data
            tag_config: Tag配置（已合并calculator和tag配置）
                - tag_meta: Tag元信息
                - base_term: 基础周期
                - required_terms: 需要的其他周期
                - required_data: 需要的数据源
                - core: 业务配置
                - performance: 性能配置
        
        Returns:
            Dict[str, Any] 或 None:
                - 如果返回None，不创建tag
                - 如果返回字典，格式：
                    {
                        "value": str,  # Tag值（必填）
                        "start_date": str,  # 可选，起始日期（YYYYMMDD）
                        "end_date": str,  # 可选，结束日期（YYYYMMDD）
                    }
        """
        pass
    
    def on_tag_created(
        self,
        tag_name: str,
        as_of_date: str,
        tag_value: Dict[str, Any],
        tag_result: Dict[str, Any]
    ):
        """
        Tag 创建后的钩子
        
        在 calculate_tag 返回结果并创建 tag value 后调用。
        用户可以在这里进行自定义处理，如记录日志、更新 tracker 等。
        
        Args:
            tag_name: Tag名称
            as_of_date: 业务日期
            tag_value: 创建的 tag value 字典
            tag_result: calculate_tag 返回的结果
        """
        pass
    
    def on_as_of_date_calculate_complete(
        self,
        as_of_date: str,
        filtered_data: Dict[str, Any],
        tag_values_count: int
    ):
        """
        每个日期计算完成后的钩子
        
        在处理完一个日期的所有 tags 后调用。
        用户可以在这里进行自定义处理，如更新 tracker、记录进度等。
        
        Args:
            as_of_date: 业务日期
            filtered_data: 过滤后的历史数据
            tag_values_count: 该日期创建的 tag values 数量
        """
        pass
    
    def on_calculate_error(
        self,
        tag_name: str,
        as_of_date: str,
        error: Exception,
        tag_config: Dict[str, Any]
    ) -> bool:
        """
        计算错误钩子
        
        在 calculate_tag 抛出异常时调用。
        用户可以在这里进行错误处理，如记录日志、发送通知等。
        
        Args:
            tag_name: Tag名称
            as_of_date: 业务日期
            error: 异常对象
            tag_config: Tag配置
        
        Returns:
            bool: 是否继续处理（True=继续，False=停止）
        """
        return True
    
    def should_continue_on_error(self, error: Exception) -> bool:
        """
        错误时是否继续（已废弃，使用 on_calculate_error 代替）
        
        为了向后兼容保留，但建议使用 on_calculate_error。
        """
        return True
    
    def on_after_execute_tagging(self, result: Dict[str, Any]):
        """
        执行标签计算后的钩子
        
        在所有日期处理完成后、批量保存结果后调用。
        用户可以在这里进行清理工作，如释放资源、记录统计信息等。
        
        Args:
            result: 执行结果统计信息
        """
        pass