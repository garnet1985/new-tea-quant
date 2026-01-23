"""
股指指标 Handler

从 Tushare 获取指数 K 线数据（日线/周线/月线）
为每个指数和周期创建 ApiJob，全部获取后一起 normalize 并入库
"""
from typing import List, Dict, Any
from loguru import logger

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper


class StockIndexIndicatorHandler(BaseHandler):
    """
    股指指标 Handler
    
    为每个指数和周期创建 ApiJob，全部获取后一起 normalize 并入库
    
    配置（在 config.json 中）：
    - renew_mode: "incremental"
    - date_format: "day"
    - index_list: [...] (指数列表)
    - apis: {...} (包含 daily_kline, weekly_kline, monthly_kline API 配置)
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
        抓取前阶段钩子：为每个指数和周期创建 ApiJob
        
        使用基类的统一日期范围，不需要为每个周期计算不同的结束日期
        
        Args:
            context: 执行上下文
            apis: 原始 ApiJob 列表（从 config 构建，包含 daily_kline, weekly_kline, monthly_kline）
            
        Returns:
            List[ApiJob]: 处理后的 ApiJob 列表（每个指数和周期一个 ApiJob）
        """
        # 构建 API name 到 base_api 的映射
        api_map = {api.api_name: api for api in apis}
        
        # 周期到 API name 的映射
        term_to_api = {
            "daily": "daily_kline",
            "weekly": "weekly_kline",
            "monthly": "monthly_kline"
        }
        
        expanded_apis = []
        
        # 为每个指数和周期创建 ApiJob
        # 日期范围由基类统一计算并注入，这里只需要设置 ts_code
        for index_info in self.index_list:
            index_id = index_info['id']
            
            for term, api_name in term_to_api.items():
                base_api = api_map.get(api_name)
                if not base_api:
                    continue
                
                # 创建 ApiJob，日期范围由基类统一注入
                new_api = ApiJob(
                    api_name=base_api.api_name,
                    provider_name=base_api.provider_name,
                    method=base_api.method,
                    params={
                        **base_api.params,
                        "ts_code": index_id,
                    },
                    api_params=base_api.api_params,
                    depends_on=base_api.depends_on,
                    rate_limit=base_api.rate_limit,
                    job_id=f"{index_id}_{term}",
                )
                expanded_apis.append(new_api)
        
        logger.info(f"✅ 为 {len(expanded_apis)} 个指数和周期生成了指数K线数据获取任务")
        
        return expanded_apis
    
    def on_after_fetch(self, context: Dict[str, Any], fetched_data: Dict[str, Any], apis: List[ApiJob]) -> Dict[str, Any]:
        """
        抓取完成后的预处理钩子：合并所有 records，添加 id 和 term 字段
        
        Args:
            context: 执行上下文
            fetched_data: {job_id: result} 格式的数据
            apis: ApiJob 列表
            
        Returns:
            Dict[str, Any]: {api_name: records_list} 格式的数据（records 中已包含 id 和 term 字段，但未应用 field_mapping）
        """
        config = context.get("config")
        if hasattr(config, "get_apis"):
            apis_conf = config.get_apis()
        else:
            apis_conf = config.get("apis") if config else {}
        
        # 合并所有 records，添加 id 和 term 字段（不应用 field_mapping，让基类处理）
        all_records = []
        
        for job_id, result in fetched_data.items():
            # 解析 job_id 获取 index_id 和 term
            parts = job_id.rsplit('_', 1)
            if len(parts) != 2:
                logger.warning(f"⚠️ job_id 格式异常: {job_id}，跳过")
                continue
            
            index_id = parts[0]
            term = parts[1]
            
            # 转换为 records（原始 records，未应用 field_mapping）
            records = DataSourceHandlerHelper.result_to_records(result)
            if not records:
                continue
            
            # 为每条记录添加 id 和 term 字段（在 field_mapping 之前添加，这样 field_mapping 不会覆盖它们）
            for record in records:
                record['id'] = index_id
                record['term'] = term
                all_records.append(record)
        
        # 按 API name 分组（基类期望的格式）
        # 由于所有 records 已经添加了 id 和 term，可以按任意 API name 分组
        # 这里使用第一个 API name（基类会应用对应的 field_mapping）
        if all_records and apis_conf:
            first_api_name = list(apis_conf.keys())[0]
            return {first_api_name: all_records}
        
        return {}
    
    def on_after_mapping(self, context: Dict[str, Any], mapped_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        字段映射后的钩子：标准化日期格式
        
        Args:
            context: 执行上下文
            mapped_records: 已应用 field_mapping 的记录列表（已包含 id 和 term 字段）
            
        Returns:
            List[Dict[str, Any]]: 处理后的记录列表
        """
        if not mapped_records:
            return mapped_records
        
        formatted = []
        for record in mapped_records:
            # 标准化日期格式（date 字段）
            date_value = record.get('date')
            if date_value:
                # 统一日期格式为 YYYYMMDD
                date_str = str(date_value)
                date_ymd = date_str.replace('-', '') if '-' in date_str else date_str
                record['date'] = date_ymd
            else:
                # 如果缺少 date 字段，跳过该记录
                logger.warning("记录缺少 date 字段，跳过该记录")
                continue
            
            formatted.append(record)
        
        return formatted

    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化后处理：保存股指指标数据到数据库
        
        Args:
            context: 执行上下文
            normalized_data: 标准化后的数据
            
        Returns:
            Dict[str, Any]: 返回标准化后的数据
        """
        data_manager = context.get("data_manager")
        if not data_manager:
            logger.warning("DataManager 未初始化，无法保存股指指标数据")
            return normalized_data
        
        # 检查是否是 dry_run 模式
        dry_run = context.get('dry_run', False)
        if dry_run:
            logger.info("🧪 干运行模式：跳过股指指标数据保存")
            return normalized_data
        
        # 验证数据格式
        data_list = normalized_data.get("data") if isinstance(normalized_data, dict) else None
        if not data_list:
            logger.debug("股指指标数据为空，无需保存")
            return normalized_data
        
        try:
            # 清理 NaN 值
            from core.infra.db.helpers.db_helpers import DBHelper
            data_list = DBHelper.clean_nan_in_list(data_list, default=0.0)
            
            # 使用 service 保存数据
            count = data_manager.index.save_indicator(data_list)
            logger.info(f"✅ 股指指标数据保存完成，共 {count} 条记录")
        except Exception as e:
            logger.error(f"❌ 保存股指指标数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
        
        return normalized_data

