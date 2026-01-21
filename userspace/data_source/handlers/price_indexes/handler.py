"""
价格指数 Handler - 合并 CPI、PPI、PMI、货币供应量数据

从 Tushare 获取 CPI、PPI、PMI、货币供应量数据，合并到 price_indexes 表中。

业务逻辑：
1. 调用四个 API：get_cpi, get_ppi, get_pmi, get_money_supply
2. 按月份合并数据
3. 保存到 price_indexes 表
"""
from typing import List, Dict, Any
from loguru import logger
import pandas as pd

from core.modules.data_source.base_data_source_handler import BaseDataSourceHandler
from core.modules.data_source.data_classes import DataSourceTask
from core.utils.date.date_utils import DateUtils


class PriceIndexesHandler(BaseDataSourceHandler):
    """
    价格指数 Handler - 合并 CPI、PPI、PMI、货币供应量数据
    
    特点：
    - 需要多个 API 调用（Tushare get_cpi + get_ppi + get_pmi + get_money_supply）
    - 增量更新（incremental）
    - 按月份合并数据
    - 滚动刷新机制：每次运行都刷新最近 N 个月的数据（确保数据一致性）
    """
    
    # 类属性（必须定义）
    data_source = "price_indexes"
    description = "获取价格指数数据（CPI/PPI/PMI，合并）"
    dependencies = []  # 不依赖其他数据源
    
    # 可选类属性
    requires_date_range = True  # 需要日期范围参数
    
    # 注意：不再需要自定义 before_fetch
    # 基类会根据 renew_mode="rolling" 自动处理日期范围计算
    
    async def fetch(self, context: Dict[str, Any] = None) -> List[DataSourceTask]:
        """
        生成获取价格指数数据的 Tasks
        
        逻辑：
        1. 从 context 获取日期范围
        2. 为每个 API 创建一个 ApiJob：
           - Tushare get_cpi API
           - Tushare get_ppi API
           - Tushare get_pmi API
           - Tushare get_money_supply API
        3. 合并成一个 Task
        """
        if context is None:
            context = {}
        
        start_date = context.get("start_date")
        end_date = context.get("end_date")
        
        # 调试：如果找不到日期范围，记录 context 的内容
        if not start_date or not end_date:
            logger.error(f"❌ PriceIndexesHandler 需要 start_date 和 end_date 参数")
            logger.error(f"   context 内容: {context}")
            logger.error(f"   context keys: {list(context.keys())}")
            logger.error(f"   start_date: {start_date}, end_date: {end_date}")
            raise ValueError("PriceIndexesHandler 需要 start_date 和 end_date 参数")
        
        logger.info(f"✅ 为价格指数数据生成任务: {start_date} 至 {end_date}")
        
        # 创建 4 个 ApiJob（从缓存的 API Job 实例创建，只修改 params）
        # 1. CPI API
        cpi_job = self.get_api_job_with_params(
            name="cpi_data",
            params={
                "start_date": start_date,
                "end_date": end_date,
            },
            job_id="cpi_data"
        )
        
        # 2. PPI API
        ppi_job = self.get_api_job_with_params(
            name="ppi_data",
            params={
                "start_date": start_date,
                "end_date": end_date,
            },
            job_id="ppi_data"
        )
        
        # 3. PMI API
        pmi_job = self.get_api_job_with_params(
            name="pmi_data",
            params={
                "start_date": start_date,
                "end_date": end_date,
            },
            job_id="pmi_data"
        )
        
        # 4. Money Supply API
        money_supply_job = self.get_api_job_with_params(
            name="money_supply_data",
            params={
                "start_date": start_date,
                "end_date": end_date,
            },
            job_id="money_supply_data"
        )
        
        # 创建一个 Task（包含 4 个 ApiJob）
        task = DataSourceTask(
            task_id="price_indexes_data",
            api_jobs=[cpi_job, ppi_job, pmi_job, money_supply_job],
            description=f"获取价格指数数据（CPI/PPI/PMI/货币供应量）: {start_date} 至 {end_date}",
        )
        
        return [task]
    
    async def normalize(self, task_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        标准化数据
        
        从 4 个 API 的结果中合并数据：
        1. 从 Tushare get_cpi 获取 CPI 数据
        2. 从 Tushare get_ppi 获取 PPI 数据
        3. 从 Tushare get_pmi 获取 PMI 数据
        4. 从 Tushare get_money_supply 获取货币供应量数据
        5. 按月份合并数据
        """
        formatted = []
        
        # task_results 的结构：{task_id: {job_id: result}}
        task_result = task_results.get("price_indexes_data", {})
        
        if not task_result:
            logger.warning("价格指数数据任务结果为空")
            return {"data": []}
        
        # 获取 4 个 API 的结果
        cpi_df = task_result.get("cpi_data")
        ppi_df = task_result.get("ppi_data")
        pmi_df = task_result.get("pmi_data")
        money_supply_df = task_result.get("money_supply_data")
        
        # 构建月份到数据的映射
        data_by_month = {}
        
        # 处理 CPI 数据
        if cpi_df is not None and not cpi_df.empty:
            for _, row in cpi_df.iterrows():
                month = str(row.get('month', ''))
                if not month:
                    continue
                
                # 统一月份格式为 YYYYMM
                month_ym = self._normalize_month(month)
                if not month_ym:
                    continue
                
                if month_ym not in data_by_month:
                    data_by_month[month_ym] = {'date': month_ym}
                
                data_by_month[month_ym]['cpi'] = float(row.get('nt_val', 0))
                data_by_month[month_ym]['cpi_yoy'] = float(row.get('nt_yoy', 0))
                data_by_month[month_ym]['cpi_mom'] = float(row.get('nt_mom', 0))
        
        # 处理 PPI 数据
        if ppi_df is not None and not ppi_df.empty:
            for _, row in ppi_df.iterrows():
                month = str(row.get('month', ''))
                if not month:
                    continue
                
                # 统一月份格式为 YYYYMM
                month_ym = self._normalize_month(month)
                if not month_ym:
                    continue
                
                if month_ym not in data_by_month:
                    data_by_month[month_ym] = {'date': month_ym}
                
                data_by_month[month_ym]['ppi'] = float(row.get('ppi_accu', 0))
                data_by_month[month_ym]['ppi_yoy'] = float(row.get('ppi_yoy', 0))
                data_by_month[month_ym]['ppi_mom'] = float(row.get('ppi_mom', 0))
        
        # 处理 PMI 数据
        if pmi_df is not None and not pmi_df.empty:
            for _, row in pmi_df.iterrows():
                month = str(row.get('MONTH', ''))
                if not month:
                    continue
                
                # 统一月份格式为 YYYYMM
                month_ym = self._normalize_month(month)
                if not month_ym:
                    continue
                
                if month_ym not in data_by_month:
                    data_by_month[month_ym] = {'date': month_ym}
                
                data_by_month[month_ym]['pmi'] = float(row.get('PMI010000', 0))
                data_by_month[month_ym]['pmi_l_scale'] = float(row.get('PMI010100', 0))
                data_by_month[month_ym]['pmi_m_scale'] = float(row.get('PMI010200', 0))
                data_by_month[month_ym]['pmi_s_scale'] = float(row.get('PMI010300', 0))
        
        # 处理货币供应量数据
        if money_supply_df is not None and not money_supply_df.empty:
            for _, row in money_supply_df.iterrows():
                month = str(row.get('month', ''))
                if not month:
                    continue
                
                # 统一月份格式为 YYYYMM
                month_ym = self._normalize_month(month)
                if not month_ym:
                    continue
                
                if month_ym not in data_by_month:
                    data_by_month[month_ym] = {'date': month_ym}
                
                data_by_month[month_ym]['m0'] = float(row.get('m0', 0))
                data_by_month[month_ym]['m0_yoy'] = float(row.get('m0_yoy', 0))
                data_by_month[month_ym]['m0_mom'] = float(row.get('m0_mom', 0))
                data_by_month[month_ym]['m1'] = float(row.get('m1', 0))
                data_by_month[month_ym]['m1_yoy'] = float(row.get('m1_yoy', 0))
                data_by_month[month_ym]['m1_mom'] = float(row.get('m1_mom', 0))
                data_by_month[month_ym]['m2'] = float(row.get('m2', 0))
                data_by_month[month_ym]['m2_yoy'] = float(row.get('m2_yoy', 0))
                data_by_month[month_ym]['m2_mom'] = float(row.get('m2_mom', 0))
        
        # 转换为列表，按日期排序
        for month_ym in sorted(data_by_month.keys()):
            record = data_by_month[month_ym]
            # 确保所有必需字段都有默认值
            record.setdefault('cpi', 0.0)
            record.setdefault('cpi_yoy', 0.0)
            record.setdefault('cpi_mom', 0.0)
            record.setdefault('ppi', 0.0)
            record.setdefault('ppi_yoy', 0.0)
            record.setdefault('ppi_mom', 0.0)
            record.setdefault('pmi', 0.0)
            record.setdefault('pmi_l_scale', 0.0)
            record.setdefault('pmi_m_scale', 0.0)
            record.setdefault('pmi_s_scale', 0.0)
            record.setdefault('m0', 0.0)
            record.setdefault('m0_yoy', 0.0)
            record.setdefault('m0_mom', 0.0)
            record.setdefault('m1', 0.0)
            record.setdefault('m1_yoy', 0.0)
            record.setdefault('m1_mom', 0.0)
            record.setdefault('m2', 0.0)
            record.setdefault('m2_yoy', 0.0)
            record.setdefault('m2_mom', 0.0)
            
            formatted.append(record)
        
        logger.info(f"✅ 价格指数数据处理完成，共 {len(formatted)} 条记录（合并 CPI/PPI/PMI/货币供应量）")
        
        return {
            "data": formatted
        }
    
    def _normalize_month(self, month: str) -> str:
        """
        标准化月份格式为 YYYYMM
        
        Args:
            month: 月份字符串，可能是 YYYYMM、YYYY-MM、YYYYMMDD 等格式
        
        Returns:
            str: YYYYMM 格式的月份字符串，如果无法解析返回空字符串
        """
        if not month:
            return ""
        
        # 移除所有非数字字符
        month_clean = ''.join(c for c in month if c.isdigit())
        
        if len(month_clean) == 6:
            # YYYYMM 格式
            return month_clean
        elif len(month_clean) == 8:
            # YYYYMMDD 格式，取前 6 位
            return month_clean[:6]
        elif len(month_clean) == 4:
            # YYYY 格式，需要补充月份（这种情况不应该出现，但为了容错）
            logger.warning(f"月份格式异常: {month}，无法解析")
            return ""
        else:
            logger.warning(f"月份格式异常: {month}，无法解析")
            return ""
    
    async def after_normalize(self, normalized_data: Dict[str, Any], context: Dict[str, Any] = None):
        """
        标准化后处理：保存数据到数据库
        
        Args:
            normalized_data: 标准化后的数据（包含 'data' 键）
            context: 执行上下文，可能包含 dry_run 标志
        """
        context = context or {}
        
        # 检查是否是 dry_run 模式
        dry_run = context.get('dry_run', False)
        if dry_run:
            logger.info("🧪 干运行模式：跳过价格指数数据保存")
            return
        
        if not self.data_manager:
            logger.warning("DataManager 未初始化，无法保存价格指数数据")
            return
        
        # 验证数据格式
        data_list = self._validate_data_for_save(normalized_data)
        if not data_list:
            logger.debug("价格指数数据为空，无需保存")
            return
        
        try:
            # 清理 NaN 值
            from core.infra.db.helpers.db_helpers import DBHelper
            data_list = DBHelper.clean_nan_in_list(data_list, default=0.0)
            
            # 保存数据（通过 service 访问）
            count = self.data_manager.macro.save_price_indexes_data(data_list)
            logger.info(f"✅ 价格指数数据保存完成，共 {count} 条记录")
        except Exception as e:
            logger.error(f"❌ 保存价格指数数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())


