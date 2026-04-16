"""
Tag Worker 基类

定义 tag 计算的生命周期流程，提供钩子函数供用户实现业务逻辑。
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple, Type
import inspect
import logging
from core.modules.tag.enums import TagUpdateMode
from core.modules.data_manager import DataManager
from core.modules.tag.models.tag_model import TagModel

logger = logging.getLogger(__name__)


class BaseTagWorker(ABC):
    """Tag Worker 基类（子进程 worker）"""
    
    def __init__(self, job_payload: Dict[str, Any]):
        """初始化 TagWorker"""
        self.job_payload = job_payload
        
        self.entity = {
            'id': job_payload.get('entity_id'),
            'type': job_payload.get('entity_type', 'stock')
        }
        
        scenario_name = job_payload.get('scenario_name', '')
        if not scenario_name:
            scenario_name = job_payload.get('settings', {}).get('name', '')
        
        self.scenario = {
            'name': scenario_name,
            'update_mode': job_payload.get('update_mode')
        }
        
        self.job = {
            'start_date': job_payload.get('start_date'),
            'end_date': job_payload.get('end_date')
        }
        
        tag_defs_dict = job_payload.get('tag_definitions', [])
        self.tag_definitions = [TagModel.from_dict(t) for t in tag_defs_dict]
        self.settings = job_payload.get('settings', {})
        
        self.data_mgr = DataManager(is_verbose=False)
        self.tag_data_service = self.data_mgr.stock.tags
        self.tracker = {}
        self._extract_settings()
        
        from core.modules.data_contract.cache import ContractCacheManager
        from core.modules.tag.components.data_management.tag_data_manager import TagDataManager

        self.tag_data_manager = TagDataManager(
            entity_id=self.entity['id'],
            entity_type=self.entity['type'],
            scenario_name=self.scenario['name'],
            settings=self.settings,
            data_mgr=self.data_mgr,
            contract_cache=ContractCacheManager(),
            global_extra_cache=job_payload.get("global_extra_cache") or {},
        )
        
        self.on_init()
    
    def _extract_settings(self):
        """从 settings 中提取配置"""
        self.config = {
            'core': self.settings.get('core', {}),
            'performance': self.settings.get('performance', {})
        }
    
    # ==================== 生命周期方法 ====================
    
    def process_entity(self) -> Dict[str, Any]:
        """处理单个 entity 的 tag 计算（子进程入口）"""
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
                f"处理 entity 失败: entity_id={self.entity['id']}, "
                f"scenario_name={self.scenario['name']}, error={e}",
                exc_info=True
            )
            return {
                "entity_id": self.entity['id'],
                "entity_type": self.entity['type'],
                "scenario_name": self.scenario['name'],
                "total_dates": 0,
                "processed_dates": 0,
                "total_tags_created": 0,
                "errors": [str(e)],
                "success": False
            }
    
    def _preprocess(self):
        """预处理阶段"""
        self.tag_data_manager.hydrate_row_slots(
            self.job['start_date'],
            self.job['end_date'],
        )
        self.tag_data_manager.rebuild_data_cursor()
        self.trading_dates = self.tag_data_manager.get_trading_dates(
            self.job['start_date'],
            self.job['end_date']
        )
        
        self.on_before_execute_tagging()
    
    def _execute_tagging(self) -> Dict[str, Any]:
        """
        执行标签计算阶段
        
        流程：
        1. 遍历每个交易日
        2. 对每个日期：获取历史数据（委托给 tag_data_manager + DataCursor）
        3. 对每个 tag：调用 calculate_tag()
        4. 收集结果
        5. 调用钩子函数
        
        Returns:
            Dict[str, Any]: 执行结果统计信息
        """
        total_dates = len(self.trading_dates)
        processed_dates = 0
        total_tags_created = 0
        errors = []
        tag_values_to_save = []
        
        for as_of_date in self.trading_dates:
            try:
                # 获取历史数据（由 DataCursor 按 as_of_date 生成前缀视图）
                historical_data = self.tag_data_manager.get_data_until(as_of_date)
                
                # 对每个 tag 调用 calculate_tag()
                for tag_definition in self.tag_definitions:
                    try:
                        # 调用用户实现的 calculate_tag 方法（方案1：最小化参数）
                        tag_result = self.calculate_tag(
                            as_of_date=as_of_date,
                            historical_data=historical_data,
                            tag_definition=tag_definition
                        )
                        
                        # 如果返回结果，创建 tag value
                        if tag_result is not None:
                            tag_value = {
                                "entity_id": self.entity['id'],
                                "entity_type": self.entity['type'],
                                "tag_definition_id": tag_definition.id,
                                "as_of_date": as_of_date,
                                "json_value": tag_result.get("value", ""),  # 使用 json_value 字段名
                                "start_date": tag_result.get("start_date"),
                                "end_date": tag_result.get("end_date"),
                            }
                            tag_values_to_save.append(tag_value)
                            total_tags_created += 1
                            
                            # 调用 tag 创建后钩子
                            self.on_tag_created(
                                as_of_date=as_of_date,
                                tag_definition=tag_definition,
                                tag_value=tag_value
                            )
                    
                    except Exception as e:
                        error_msg = (
                            f"计算 tag 失败: tag_name={tag_definition.tag_name}, "
                            f"entity_id={self.entity['id']}, as_of_date={as_of_date}, error={e}"
                        )
                        logger.error(error_msg, exc_info=True)
                        errors.append(error_msg)
                        
                        # 调用错误处理钩子
                        should_continue = self.on_calculate_error(
                            as_of_date=as_of_date,
                            error=e,
                            tag_definition=tag_definition
                        )
                        
                        if not should_continue:
                            # 如果钩子返回 False，停止处理该 tag
                            break
                
                # 调用每个日期计算完成钩子
                self.on_as_of_date_calculate_complete(as_of_date)
                
                processed_dates += 1
                
            except Exception as e:
                error_msg = (
                    f"处理日期失败: entity_id={self.entity['id']}, "
                    f"as_of_date={as_of_date}, error={e}"
                )
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
        
        # 保存所有 tag values（批量保存）
        self._tag_values_to_save = tag_values_to_save
        
        return {
            "entity_id": self.entity['id'],
            "entity_type": self.entity['type'],
            "scenario_name": self.scenario['name'],
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
        批量保存 tag values（使用批量写入队列，解决并发写入问题）
        
        Args:
            tag_values: Tag value 列表
        """
        if not tag_values:
            return
        
        try:
            # 使用 save_batch，内部会调用 model.batch_save_tag_values() → model.upsert_many() → queue_write()
            # 已经自动支持批量写入队列，无需额外修改
            self.tag_data_service.save_batch(tag_values)
            logger.debug(
                f"批量保存 tag values 成功: entity_id={self.entity['id']}, "
                f"count={len(tag_values)}"
            )
            
            # 注意：在多进程场景下，每个子进程有自己的 DatabaseManager 实例
            # 但批量写入队列是进程级别的，所以每个进程的写入会进入各自的队列
            # 这里不需要等待，因为 tag_manager 会在所有 jobs 完成后统一等待
        except Exception as e:
            logger.error(
                f"批量保存 tag values 失败: entity_id={self.entity['id']}, "
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
        as_of_date: str,
        historical_data: Dict[str, Any],
        tag_definition: TagModel
    ) -> Optional[Dict[str, Any]]:
        """
        计算 tag（用户必须实现）
        
        Args:
            as_of_date: 当前业务日期（YYYYMMDD格式）
            historical_data: 历史数据字典，结构根据 settings 中的配置保持一致：
                - key 统一使用 data_id（例如 "stock.kline" / "macro.gdp"）
                - value 为对应 data_id 的历史记录列表
            tag_definition: Tag定义对象（TagModel），包含：
                - id: Tag定义ID
                - tag_name: Tag名称
                - display_name: 显示名称
                - description: Tag描述（重要，用于理解tag的意义）
                - 其他元信息
        
        注意：
        - entity信息可通过 self.entity['id'] 和 self.entity['type'] 访问
        - 配置信息可通过 self.config['core'] 和 self.config['performance'] 访问
        - 临时状态可通过 self.tracker 存储和访问
        
        Returns:
            Dict[str, Any] 或 None:
                - 如果返回None，不创建tag
                - 如果返回字典，格式：
                    {
                        "value": str | dict | list,  # Tag值（必填），支持字符串或 JSON 格式（dict/list）
                        "start_date": str,  # 可选，起始日期（YYYYMMDD）
                        "end_date": str,  # 可选，结束日期（YYYYMMDD）
                    }
                
                注意：
                - value 可以是字符串或 JSON 格式（dict/list）
                - 推荐使用 JSON 格式存储结构化数据，例如：
                  {"momentum": 0.1234, "year_month": "202501"}
                - 系统会自动将 dict/list 转换为 JSON 字符串存储到数据库
                - 读取时会自动解析 JSON 字符串为 Python dict/list
        """
        pass
    
    def on_tag_created(
        self,
        as_of_date: str,
        tag_definition: TagModel,
        tag_value: Dict[str, Any]
    ):
        """
        Tag 创建后的钩子
        
        在 calculate_tag 返回结果并创建 tag value 后调用。
        用户可以在这里进行自定义处理，如记录日志、更新 tracker 等。
        
        Args:
            as_of_date: 业务日期（YYYYMMDD格式）
            tag_definition: Tag定义对象（TagModel），包含完整的tag信息
            tag_value: 创建的 tag value 字典，包含：
                - entity_id: 实体ID
                - entity_type: 实体类型
                - tag_definition_id: Tag定义ID
                - as_of_date: 业务日期
                - json_value: Tag值（JSON 格式）
                - start_date: 起始日期（可选）
                - end_date: 结束日期（可选）
        
        注意：
        - tag名称可通过 tag_definition.tag_name 获取
        - tag描述可通过 tag_definition.description 获取
        """
        pass
    
    def on_as_of_date_calculate_complete(self, as_of_date: str):
        """
        每个日期计算完成后的钩子
        
        在处理完一个日期的所有 tags 后调用。
        用户可以在这里进行自定义处理，如更新 tracker、记录进度等。
        
        Args:
            as_of_date: 业务日期（YYYYMMDD格式）
        
        注意：
        - 如果需要历史数据，可以在 calculate_tag 中处理
        - 如果需要统计该日期创建的 tag 数量，可以通过 self.tracker 维护
        """
        pass
    
    def on_calculate_error(
        self,
        as_of_date: str,
        error: Exception,
        tag_definition: TagModel
    ) -> bool:
        """
        计算错误钩子
        
        在 calculate_tag 抛出异常时调用。
        用户可以在这里进行错误处理，如记录日志、发送通知等。
        
        Args:
            as_of_date: 业务日期（YYYYMMDD格式）
            error: 异常对象
            tag_definition: Tag定义对象（TagModel），包含完整的tag信息
        
        注意：
        - tag名称可通过 tag_definition.tag_name 获取
        - entity信息可通过 self.entity 访问
        
        Returns:
            bool: 是否继续处理（True=继续，False=停止）
        """
        return True
    
    def on_after_execute_tagging(self, result: Dict[str, Any]):
        """
        执行标签计算后的钩子
        
        在所有日期处理完成后、批量保存结果后调用。
        用户可以在这里进行清理工作，如释放资源、记录统计信息等。
        
        Args:
            result: 执行结果统计信息字典，包含：
                - entity_id: 实体ID
                - entity_type: 实体类型
                - scenario_name: Scenario名称
                - total_dates: 总日期数
                - processed_dates: 已处理日期数
                - total_tags_created: 创建的tag总数
                - errors: 错误列表
                - success: 是否成功
        
        注意：
        - entity信息也可通过 self.entity 访问
        - scenario信息也可通过 self.scenario 访问
        """
        pass