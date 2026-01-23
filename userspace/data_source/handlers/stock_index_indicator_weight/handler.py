"""
股指成分股权重 Handler

从 Tushare 获取指数成分股权重数据。

业务逻辑：
1. 调用 Tushare index_weight API
2. 为每个指数生成一个 ApiJob
3. 指数成分股不常变化，至少1个月才更新
"""
from typing import List, Dict, Any
from loguru import logger

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper
from core.utils.date.date_utils import DateUtils


class StockIndexIndicatorWeightHandler(BaseHandler):
    """
    股指成分股权重 Handler
    
    特点：
    - 为每个指数生成一个 ApiJob
    - 单API，简单mapping
    - 指数成分股不常变化，至少1个月才更新
    
    配置（在 config.json 中）：
    - renew_mode: "incremental"
    - date_format: "day"
    - index_list: [...] (指数列表)
    - apis: {...} (包含 index_weight API 配置)
    """
    
    def __init__(self, data_source_name: str, schema, config, providers: Dict[str, BaseProvider]):
        super().__init__(data_source_name, schema, config, providers)
        # 从 config 获取指数列表
        if hasattr(config, "get"):
            self.index_list = config.get("index_list", [])
        elif hasattr(config, "index_list"):
            self.index_list = config.index_list
        else:
            self.index_list = []
    
    def on_before_fetch(self, context: Dict[str, Any], apis: List[ApiJob]) -> List[ApiJob]:
        """
        抓取前阶段钩子：为每个指数创建 ApiJob
        
        Args:
            context: 执行上下文
            apis: 原始 ApiJob 列表（从 config 构建）
            
        Returns:
            List[ApiJob]: 处理后的 ApiJob 列表（每个指数一个 ApiJob）
        """
        # 从 context 获取日期范围
        end_date = context.get("end_date")
        if not end_date:
            # 获取最新交易日
            latest_trading_date = context.get("latest_completed_trading_date")
            if not latest_trading_date:
                data_manager = context.get("data_manager")
                if data_manager:
                    try:
                        latest_trading_date = data_manager.service.calendar.get_latest_completed_trading_date()
                    except Exception as e:
                        logger.warning(f"获取最新交易日失败: {e}")
                        latest_trading_date = DateUtils.get_current_date_str()
                else:
                    latest_trading_date = DateUtils.get_current_date_str()
            
            # 实际结束日期是前一个交易日
            end_date = DateUtils.get_date_before_days(latest_trading_date, 1)
            context["end_date"] = end_date
        
        # 从数据库查询每个指数的最新日期
        index_latest_dates = {}  # {index_id: latest_date}
        data_manager = context.get("data_manager")
        if data_manager:
            try:
                index_latest_dates = data_manager.index.load_latest_weights()
            except Exception as e:
                logger.warning(f"查询数据库失败: {e}")
        
        context["index_latest_dates"] = index_latest_dates
        
        # 为每个指数创建 ApiJob
        expanded_apis = []
        base_api = apis[0] if apis else None  # 假设只有一个 base API
        
        if not base_api:
            logger.warning("未找到 base API，无法创建指数 ApiJobs")
            return apis
        
        for index_info in self.index_list:
            index_id = index_info['id']
            index_name = index_info.get('name', index_id)
            
            # 计算开始日期
            latest_date = index_latest_dates.get(index_id)
            
            if latest_date:
                # 有历史记录，检查是否需要更新（至少1个月才更新）
                time_gap_days = DateUtils.get_duration_in_days(latest_date, end_date)
                if time_gap_days < 30:  # 至少30天才更新
                    continue
                
                start_date = DateUtils.get_date_after_days(latest_date, 1)
            else:
                # 无历史记录，使用默认起始日期
                from core.infra.project_context import ConfigManager
                start_date = ConfigManager.get_default_start_date()
            
            # 如果开始日期大于结束日期，跳过
            if start_date > end_date:
                continue
            
            # 复制 base_api 并修改参数
            new_api = ApiJob(
                api_name=base_api.api_name,
                provider_name=base_api.provider_name,
                method=base_api.method,
                params={
                    **base_api.params,
                    "index_code": index_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
                api_params=base_api.api_params,
                depends_on=base_api.depends_on,
                rate_limit=base_api.rate_limit,
                job_id=f"{index_id}_weight",
            )
            expanded_apis.append(new_api)
        
        logger.info(f"✅ 为 {len(expanded_apis)} 个指数生成了成分股权重数据获取任务")
        
        return expanded_apis
    
    def on_after_fetch(self, context: Dict[str, Any], fetched_data: Dict[str, Any], apis: List[ApiJob]) -> Dict[str, Any]:
        """
        抓取后阶段钩子：从 job_id 提取 index_id，添加到记录中
        
        Args:
            context: 执行上下文
            fetched_data: 抓取的数据，格式为 {job_id: result}
            apis: 执行的 ApiJob 列表
            
        Returns:
            Dict[str, Any]: 转换后的数据，格式为 {api_name: records_list}
        """
        config = context.get("config")
        apis_conf = config.get_apis() if hasattr(config, "get_apis") else config.get("apis") if config else {}
        
        all_records = []
        for job_id, result in fetched_data.items():
            if not job_id.endswith("_weight"):
                logger.warning(f"⚠️ job_id 格式异常: {job_id}，跳过")
                continue
            
            index_id = job_id.replace("_weight", "")
            
            # 转换为记录列表
            records = DataSourceHandlerHelper.result_to_records(result)
            if not records:
                continue
            
            # 为每条记录添加 index_id
            for record in records:
                record['id'] = index_id
                all_records.append(record)
        
        if all_records and apis_conf:
            # 所有记录使用相同的 field_mapping，所以可以合并到一个 API name 下
            first_api_name = list(apis_conf.keys())[0]
            return {first_api_name: all_records}
        return {}
    
    def on_after_mapping(self, context: Dict[str, Any], mapped_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        字段映射后的钩子：标准化日期格式（YYYY-MM-DD -> YYYYMMDD）
        
        Args:
            context: 执行上下文
            mapped_records: 已应用 field_mapping 的记录列表
            
        Returns:
            List[Dict[str, Any]]: 处理后的记录列表
        """
        if not mapped_records:
            return mapped_records
        
        formatted = []
        for record in mapped_records:
            date_value = record.get('date')
            if date_value:
                date_str = str(date_value)
                # 统一日期格式为 YYYYMMDD
                date_ymd = date_str.replace('-', '') if '-' in date_str else date_str
                record['date'] = date_ymd
            else:
                logger.warning("记录缺少 date 字段，跳过该记录")
                continue
            
            # 确保 weight 是 float 类型
            weight = record.get('weight')
            if weight is not None:
                try:
                    record['weight'] = float(weight)
                except (ValueError, TypeError):
                    logger.warning(f"weight 字段无法转换为 float: {weight}，使用默认值 0.0")
                    record['weight'] = 0.0
            
            formatted.append(record)
        
        logger.info(f"✅ 股指成分股权重数据处理完成，共 {len(formatted)} 条记录")
        return formatted
    
    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化后处理：保存股指成分股权重数据到数据库
        
        Args:
            context: 执行上下文
            normalized_data: 标准化后的数据
            
        Returns:
            Dict[str, Any]: 返回标准化后的数据
        """
        data_manager = context.get("data_manager")
        if not data_manager:
            logger.warning("DataManager 未初始化，无法保存股指成分股权重数据")
            return normalized_data
        
        # 检查是否是 dry_run 模式
        dry_run = context.get('dry_run', False)
        if dry_run:
            logger.info("🧪 干运行模式：跳过股指成分股权重数据保存")
            return normalized_data
        
        # 验证数据格式
        data_list = normalized_data.get("data") if isinstance(normalized_data, dict) else None
        if not data_list:
            logger.debug("股指成分股权重数据为空，无需保存")
            return normalized_data
        
        try:
            from core.infra.db.helpers.db_helpers import DBHelper
            data_list = DBHelper.clean_nan_in_list(data_list, default=0.0)
            
            # 使用 service 保存数据
            count = data_manager.index.save_weight(data_list)
            logger.info(f"✅ 股指成分股权重数据保存完成，共 {count} 条记录")
        except Exception as e:
            logger.error(f"❌ 保存股指成分股权重数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
        
        return normalized_data
