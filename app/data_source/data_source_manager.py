"""
DataSource Manager - 数据源管理器

负责加载和管理 DataSource、Handler、Schema，执行数据获取
"""
import json
import importlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger
from app.data_manager import DataManager
from app.labeler import LabelerService


class DataSourceManager:
    """
    数据源管理器
    
    职责：
    - 加载 Schema 定义
    - 加载 Handler 映射配置
    - 动态加载 Handler 类
    - 执行 Handler 获取数据
    """
    
    def __init__(self, is_verbose: bool = False):
        """
        初始化数据源管理器
        
        Args:
            is_verbose: 是否输出详细日志
        """
        # 统一使用 DataManager 单例作为数据访问入口
        self.data_manager = DataManager(is_verbose=False)
        self.is_verbose = is_verbose
        self._schemas: Dict[str, Any] = {}
        self._handlers: Dict[str, Any] = {}
        self._mapping: Dict[str, Any] = {}
        
        # 加载配置
        self._load_schemas()
        self._load_mapping()
        self._load_handlers()
    
    def _load_schemas(self):
        """加载 Schema 定义"""
        try:
            from app.data_source.defaults.schemas import DEFAULT_SCHEMAS
            self._schemas = DEFAULT_SCHEMAS.copy()
            logger.debug(f"✅ 加载了 {len(self._schemas)} 个 Schema")
        except Exception as e:
            logger.error(f"❌ 加载 Schema 失败: {e}")
            self._schemas = {}
    
    def _load_mapping(self):
        """加载 Handler 映射配置（先加载 defaults，再加载 custom 覆盖）"""
        self._mapping = {}
        
        # 1. 加载 defaults/mapping.json
        try:
            defaults_path = Path(__file__).parent / "defaults" / "mapping.json"
            if defaults_path.exists():
                with open(defaults_path, 'r', encoding='utf-8') as f:
                    defaults_mapping = json.load(f)
                    self._mapping.update(defaults_mapping.get("data_sources", {}))
                logger.debug(f"✅ 加载了 defaults/mapping.json")
        except Exception as e:
            logger.warning(f"⚠️ 加载 defaults/mapping.json 失败: {e}")
        
        # 2. 加载 custom/mapping.json（覆盖 defaults）
        try:
            custom_path = Path(__file__).parent / "custom" / "mapping.json"
            if custom_path.exists():
                with open(custom_path, 'r', encoding='utf-8') as f:
                    custom_mapping = json.load(f)
                    # 只更新已存在的或新增的 data_source
                    for ds_name, ds_config in custom_mapping.get("data_sources", {}).items():
                        if ds_config.get("is_enabled", True):
                            self._mapping[ds_name] = ds_config
                logger.debug(f"✅ 加载了 custom/mapping.json")
        except Exception as e:
            logger.debug(f"custom/mapping.json 不存在或加载失败（这是正常的）: {e}")
    
    def _load_handler(self, ds_name: str, handler_path: str):
        """
        动态加载 Handler 类
        
        Args:
            ds_name: 数据源名称
            handler_path: Handler 类的完整路径（如 "defaults.handlers.stock_list_handler.TushareStockListHandler"）
        
        Returns:
            Handler 类
        """
        try:
            module_path, class_name = handler_path.rsplit('.', 1)
            module = importlib.import_module(f"app.data_source.{module_path}")
            handler_class = getattr(module, class_name)
            if self.is_verbose:
                logger.debug(f"✅ 成功加载 Handler 类: {ds_name} ({handler_path})")
            return handler_class
        except Exception as e:
            logger.error(f"❌ 加载 Handler 失败 {ds_name} ({handler_path}): {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _load_handlers(self):
        """加载所有启用的 Handler 实例"""
        for ds_name, ds_config in self._mapping.items():
            if not ds_config.get("is_enabled", True):
                continue
            
            handler_path = ds_config.get("handler")
            if not handler_path:
                logger.warning(f"⚠️ {ds_name} 没有配置 handler")
                continue
            
            # 获取 Schema
            schema = self._schemas.get(ds_name)
            if not schema:
                logger.warning(f"⚠️ {ds_name} 没有找到对应的 Schema")
                continue
            
            # 加载 Handler 类
            handler_class = self._load_handler(ds_name, handler_path)
            if not handler_class:
                continue
            
            # 创建 Handler 实例
            try:
                params = ds_config.get("params", {})
                handler_instance = handler_class(schema, params, self.data_manager)
                
                # 如果是 RollingHandler，需要设置 data_source 名称
                if hasattr(handler_instance, 'set_data_source_name'):
                    handler_instance.set_data_source_name(ds_name)
                else:
                    # 其他 handler 的 data_source 应该是类属性，确保一致
                    handler_instance.data_source = ds_name
                
                self._handlers[ds_name] = handler_instance
                if self.is_verbose:
                    logger.debug(f"✅ 成功加载 Handler: {ds_name}")
            except Exception as e:
                logger.error(f"❌ 创建 Handler 实例失败 {ds_name}: {e}")
                import traceback
                logger.error(traceback.format_exc())
    
    async def fetch(
        self, 
        ds_name: str, 
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        获取数据源数据
        
        执行指定数据源的 Handler，获取并标准化数据。
        
        注意：数据保存由 Handler 在生命周期钩子中自行决定（如 after_normalize）。
        如果需要保存数据，Handler 可以在钩子中调用 _save_to_data_manager() 方法。
        
        Args:
            ds_name: 数据源名称
            context: 执行上下文（可选）
        
        Returns:
            标准化后的数据
        """
        if ds_name not in self._handlers:
            raise ValueError(f"数据源 {ds_name} 未找到或未启用")
        
        handler = self._handlers[ds_name]
        context = context or {}
        
        logger.info(f"🔄 开始获取数据源: {ds_name}")
        
        # 执行 Handler 的 fetch_and_normalize
        result = await handler.fetch_and_normalize(context)
        
        logger.info(f"✅ 数据源 {ds_name} 获取完成")
        
        return result
    
    
    def list_data_sources(self) -> List[str]:
        """列出所有可用的数据源"""
        return list(self._handlers.keys())
    
    def get_handler_status(self) -> Dict[str, Any]:
        """
        获取所有数据源的加载状态（用于调试）
        
        Returns:
            Dict: {
                "mapping_count": int,  # mapping.json 中的数据源数量
                "enabled_count": int,    # 启用的数据源数量
                "schema_count": int,    # 有 schema 的数据源数量
                "loaded_handlers": List[str],  # 成功加载的 handler 列表
                "failed_handlers": Dict[str, str],  # 加载失败的 handler 及原因
            }
        """
        enabled_count = sum(1 for ds_config in self._mapping.values() 
                           if ds_config.get("is_enabled", True))
        schema_count = sum(1 for ds_name in self._mapping.keys() 
                          if ds_name in self._schemas)
        
        loaded_handlers = list(self._handlers.keys())
        failed_handlers = {}
        
        # 检查哪些数据源应该被加载但没有
        for ds_name, ds_config in self._mapping.items():
            if not ds_config.get("is_enabled", True):
                continue
            if ds_name not in self._handlers:
                reasons = []
                if not ds_config.get("handler"):
                    reasons.append("没有配置 handler")
                if ds_name not in self._schemas:
                    reasons.append("没有找到对应的 Schema")
                failed_handlers[ds_name] = "; ".join(reasons) if reasons else "未知原因"
        
        return {
            "mapping_count": len(self._mapping),
            "enabled_count": enabled_count,
            "schema_count": schema_count,
            "loaded_handlers": loaded_handlers,
            "failed_handlers": failed_handlers,
        }
    
    def get_schema(self, ds_name: str):
        """获取数据源的 Schema"""
        return self._schemas.get(ds_name)
    
    async def renew_kline_data(
        self,
        latest_completed_trading_date: str = None,
        stock_list: Optional[list] = None,
        test_mode: bool = False,
        dry_run: bool = False,
    ):
        """
        更新 K 线数据（包括 daily/weekly/monthly K 线 + daily_basic）
        
        Args:
            latest_completed_trading_date: 最新完成交易日（YYYYMMDD），为空时内部自动获取
            stock_list: 股票列表（可选，默认由 DataManager 自行加载）
            test_mode: 测试模式，只处理少量股票
            dry_run: 干运行模式，只跑任务不写入数据库
        
        行为：
        - 默认会：
          1.（非 dry_run）更新一次股票列表数据源 `stock_list`
          2. 从数据库读取股票列表（可选传入自定义列表）
          3. 使用 `kline` Handler 做增量更新
        - `dry_run=True` 时，只执行计算和任务调度，不向数据库写入任何 K 线记录
        """
        # 获取 / 回退最新交易日
        if not latest_completed_trading_date:
            latest_completed_trading_date = self.data_manager.get_latest_completed_trading_date()

        # 1. 更新股票列表（必须先更新，因为其他数据源依赖它）
        # 注意：dry_run 模式下也更新股票列表（因为需要最新的股票列表来计算需要更新的股票）
        if not dry_run:
            logger.info("📋 步骤 1/3: 更新股票列表...")
            await self.fetch("stock_list")  # Handler 会在 after_normalize 钩子中自动保存
        else:
            logger.info("📋 步骤 1/3: 跳过股票列表更新（dry_run 模式）...")

        # 测试模式：只处理前 10-20 个股票
        if test_mode:
            stock_list = stock_list[:20]
            logger.info(f"🧪 测试模式：只处理前 {len(stock_list)} 个股票")

        logger.info(f"📊 共 {len(stock_list)} 只股票需要更新K线数据")

        # 2. 更新K线数据（daily/weekly/monthly）
        logger.info("📋 步骤 2/3: 更新K线数据...")
        if dry_run:
            logger.info("🧪 干运行模式：只计算和执行 task，不保存数据")

        try:
            # 构建 context（不再需要 term 参数，Handler 会处理所有周期）
            context: Dict[str, Any] = {
                "stock_list": stock_list,
                "dry_run": dry_run,  # 传递 dry_run 标志给 Handler
                "latest_completed_trading_date": latest_completed_trading_date,
            }

            # 调用 fetch，Handler 会自动处理所有周期的数据获取和保存
            result = await self.fetch("kline", context=context)

            data_count = len(result.get("data", []))
            if dry_run:
                if data_count > 0:
                    logger.info(f"🧪 K线数据干运行完成，共 {data_count} 条记录（未保存，包含所有周期）")
                else:
                    logger.info("🧪 K线数据干运行完成，无需更新（数据已是最新）")
            else:
                if data_count > 0:
                    logger.info(f"✅ K线数据更新完成，共 {data_count} 条记录（包含所有周期）")
                else:
                    logger.info("ℹ️  K线数据无需更新（数据已是最新）")
        except Exception as e:
            logger.error(f"❌ 更新 K线数据失败: {e}")
            import traceback

            traceback.print_exc()



    async def renew_adj_factor_data(
        self,
        latest_completed_trading_date: str = None,
        stock_list: Optional[list] = None,
        test_mode: bool = False,
        dry_run: bool = False,
    ):
        """
        更新复权因子事件数据（adj_factor_event）

        - 使用 `adj_factor_event` Handler 实现增量/首建更新
        - 依赖：
          - 已更新的 `stock_list` 基础表
          - 已具备一定覆盖率的 `stock_kline`（K 线）数据
        - 传入的 `stock_list` 用作“关注股票集合”，为空则让 Handler 自行决定覆盖范围
        """
        # 获取 / 回退最新交易日
        if not latest_completed_trading_date:
            latest_completed_trading_date = self.data_manager.get_latest_completed_trading_date()

        # 构建 context：只传递关心的股票 universe 和基准日期（如果上层已经算好）
        context: Dict[str, Any] = {
            "latest_completed_trading_date": latest_completed_trading_date,
            # 为兼容可能使用 latest_trading_date 命名的 Handler，这里同时提供别名
            "latest_trading_date": latest_completed_trading_date,
        }
        if stock_list:
            context["stock_list"] = stock_list

        if test_mode and stock_list:
            # 测试模式下，仅使用前 N 只股票作为预筛选集合，减少 API/IO
            max_test_stocks = 50
            truncated = stock_list[:max_test_stocks]
            context["stock_list"] = truncated
            logger.info(f"🧪 测试模式：复权因子事件仅处理前 {len(truncated)} 只股票")

        if dry_run:
            logger.info("🧪 干运行模式：仅执行 adj_factor_event Handler 逻辑，不写入数据库")
            context["dry_run"] = True

        try:
            result = await self.fetch("adj_factor_event", context=context)
            # result["data"] 一般为空（adj_factor_event 的保存逻辑在 after_all_tasks_execute 中完成）
            logger.info("✅ 复权因子事件数据更新完成（adj_factor_event）")
            return result
        except Exception as e:
            logger.error(f"❌ 更新复权因子事件数据失败: {e}")
            import traceback
            traceback.print_exc()
            return {"data": []}

    async def renew_corporate_finance_data(
        self,
        latest_completed_trading_date: str = None,
        stock_list: Optional[list] = None,
        test_mode: bool = False,
        dry_run: bool = False,
    ):
        """
        更新企业财务数据（corporate_finance）
        
        - 使用 `corporate_finance` Handler 实现增量更新
        - 依赖：
          - 已更新的 `stock_list` 基础表
        - 传入的 `stock_list` 用作"关注股票集合"，为空则让 Handler 自行决定覆盖范围
        """
        # 获取 / 回退最新交易日
        if not latest_completed_trading_date:
            latest_completed_trading_date = self.data_manager.get_latest_completed_trading_date()
        
        # 构建 context：只传递关心的股票 universe 和基准日期
        context: Dict[str, Any] = {
            "latest_completed_trading_date": latest_completed_trading_date,
        }
        if stock_list:
            context["stock_list"] = stock_list
        
        if test_mode and stock_list:
            # 测试模式下，仅使用前 N 只股票，减少 API/IO
            max_test_stocks = 50
            truncated = stock_list[:max_test_stocks]
            context["stock_list"] = truncated
            logger.info(f"🧪 测试模式：企业财务数据仅处理前 {len(truncated)} 只股票")
        
        if dry_run:
            logger.info("🧪 干运行模式：仅执行 corporate_finance Handler 逻辑，不写入数据库")
            context["dry_run"] = True
        
        try:
            result = await self.fetch("corporate_finance", context=context)
            logger.info("✅ 企业财务数据更新完成（corporate_finance）")
            return result
        except Exception as e:
            logger.error(f"❌ 更新企业财务数据失败: {e}")
            import traceback
            traceback.format_exc()
            return {"data": []}

    async def renew_gdp_data(
        self,
        latest_completed_trading_date: str = None,
        stock_list: Optional[list] = None,
        test_mode: bool = False,
        dry_run: bool = False,
    ):
        """
        更新 GDP 数据
        
        - 使用 `RollingHandler` 实现滚动刷新机制
        - 数据格式：季度数据（YYYYQ1/YYYYQ2/YYYYQ3/YYYYQ4）
        - Handler 会自动计算需要更新的日期范围（从数据库最新日期开始，或使用默认范围）
        - 不依赖 `latest_completed_trading_date` 和 `stock_list`（宏观数据）
        """
        # 构建 context：宏观数据不需要 latest_completed_trading_date
        context: Dict[str, Any] = {}
        
        if dry_run:
            logger.info("🧪 干运行模式：仅执行 GDP Handler 逻辑，不写入数据库")
            context["dry_run"] = True
        
        try:
            result = await self.fetch("gdp", context=context)
            logger.info("✅ GDP 数据更新完成")
            return result
        except Exception as e:
            logger.error(f"❌ 更新 GDP 数据失败: {e}")
            import traceback
            traceback.print_exc()
            return {"data": []}
    
    async def renew_shibor_data(
        self,
        latest_completed_trading_date: str = None,
        stock_list: Optional[list] = None,
        test_mode: bool = False,
        dry_run: bool = False,
    ):
        """
        更新 Shibor 数据
        
        - 使用 `RollingHandler` 实现滚动刷新机制
        - 数据格式：日期数据（YYYYMMDD）
        - Handler 会自动计算需要更新的日期范围（从数据库最新日期开始，或使用默认范围）
        - 不依赖 `latest_completed_trading_date` 和 `stock_list`（宏观数据）
        """
        # 构建 context：宏观数据不需要 latest_completed_trading_date
        context: Dict[str, Any] = {}
        
        if dry_run:
            logger.info("🧪 干运行模式：仅执行 Shibor Handler 逻辑，不写入数据库")
            context["dry_run"] = True
        
        try:
            result = await self.fetch("shibor", context=context)
            logger.info("✅ Shibor 数据更新完成")
            return result
        except Exception as e:
            logger.error(f"❌ 更新 Shibor 数据失败: {e}")
            import traceback
            traceback.print_exc()
            return {"data": []}
    
    async def renew_lpr_data(
        self,
        latest_completed_trading_date: str = None,
        stock_list: Optional[list] = None,
        test_mode: bool = False,
        dry_run: bool = False,
    ):
        """
        更新 LPR 数据
        
        - 使用 `RollingHandler` 实现滚动刷新机制
        - 数据格式：日期数据（YYYYMMDD）
        - Handler 会自动计算需要更新的日期范围（从数据库最新日期开始，或使用默认范围）
        - 不依赖 `latest_completed_trading_date` 和 `stock_list`（宏观数据）
        """
        # 构建 context：宏观数据不需要 latest_completed_trading_date
        context: Dict[str, Any] = {}
        
        if dry_run:
            logger.info("🧪 干运行模式：仅执行 LPR Handler 逻辑，不写入数据库")
            context["dry_run"] = True
        
        try:
            result = await self.fetch("lpr", context=context)
            logger.info("✅ LPR 数据更新完成")
            return result
        except Exception as e:
            logger.error(f"❌ 更新 LPR 数据失败: {e}")
            import traceback
            traceback.print_exc()
            return {"data": []}
    

    async def renew_price_indexes_data(
        self,
        latest_completed_trading_date: str = None,
        stock_list: Optional[list] = None,
        test_mode: bool = False,
        dry_run: bool = False,
    ):
        """
        更新价格指数数据（CPI/PPI/PMI/货币供应量）
        
        - 使用 `price_indexes` Handler 实现增量更新
        - 数据格式：月度数据（YYYYMM）
        - Handler 会自动计算需要更新的日期范围（从数据库最新日期开始，或使用默认范围）
        - 不依赖 `latest_completed_trading_date` 和 `stock_list`（宏观数据）
        """
        # 构建 context：price_indexes 是月度宏观数据，不需要 latest_completed_trading_date
        context: Dict[str, Any] = {}
        
        if dry_run:
            logger.info("🧪 干运行模式：仅执行 price_indexes Handler 逻辑，不写入数据库")
            context["dry_run"] = True
        
        try:
            result = await self.fetch("price_indexes", context=context)
            logger.info("✅ 价格指数数据更新完成（price_indexes）")
            return result
        except Exception as e:
            logger.error(f"❌ 更新价格指数数据失败: {e}")
            import traceback
            traceback.print_exc()
            return {"data": []}


    async def renew_industry_capital_flow_data(
        self,
        latest_completed_trading_date: str = None,
        stock_list: Optional[list] = None,
        test_mode: bool = False,
        dry_run: bool = False,
    ):
        """
        更新行业资本流动数据（industry_capital_flow）
        
        - 使用专门的 `IndustryCapitalFlowHandler`，保持与 legacy 行为一致（增量更新）
        - 数据格式：日度数据（YYYYMMDD）
        - Handler 会根据数据库最新日期或默认范围自动计算需要更新的日期区间
        - 不依赖 `latest_completed_trading_date` 和 `stock_list`
        """
        # 行业资金流向是宏观日度数据，这里不需要 latest_completed_trading_date / stock_list
        context: Dict[str, Any] = {}
        if dry_run:
            logger.info("🧪 干运行模式：仅执行 industry_capital_flow Handler 逻辑，不写入数据库")
            context["dry_run"] = True

        try:
            result = await self.fetch("industry_capital_flow", context=context)
            logger.info("✅ 行业资本流动数据更新完成（industry_capital_flow）")
            return result
        except Exception as e:
            logger.error(f"❌ 更新行业资本流动数据失败: {e}")
            import traceback
            traceback.print_exc()
            return {"data": []}


    async def renew_index_indicators_data(
        self,
        latest_completed_trading_date: str = None,
        stock_list: Optional[list] = None,
        test_mode: bool = False,
        dry_run: bool = False,
    ):
        """
        更新股票指数指标数据（stock_index_indicator）
        
        - 使用 `StockIndexIndicatorHandler` 获取指数 K 线数据
        - 支持 daily / weekly / monthly 三个周期
        - Handler 会根据数据库最新日期自动计算增量区间
        - 不依赖 `latest_completed_trading_date` 和 `stock_list`
        """
        # 指数指标是宏观/指数类数据，这里不需要 latest_completed_trading_date / stock_list
        context: Dict[str, Any] = {}
        if dry_run:
            logger.info("🧪 干运行模式：仅执行 stock_index_indicator Handler 逻辑，不写入数据库")
            context["dry_run"] = True

        try:
            result = await self.fetch("stock_index_indicator", context=context)
            logger.info("✅ 股票指数指标数据更新完成（stock_index_indicator）")
            return result
        except Exception as e:
            logger.error(f"❌ 更新股票指数指标数据失败: {e}")
            import traceback
            traceback.print_exc()
            return {"data": []}


    async def renew_data(
        self,
        latest_completed_trading_date: str = None,
        stock_list: Optional[list] = None,
        test_mode: bool = False,
        dry_run: bool = False
    ):
        """
        一站式更新：行情数据 + 标签数据。

        Args:
            latest_completed_trading_date: 最新交易日（可选，如果不提供则自动获取）
            stock_list: 股票列表（可选，如果不提供则从数据库读取）
            test_mode: 测试模式，如果为 True，只处理前 10-20 个股票
            dry_run: 干运行模式，如果为 True，只更新行情流程，不写入任何标签
        """
        stock_list = self.data_manager.load_stock_list(filtered=True)

        # 1. 先更新行情数据（目前主要是 K 线）
        # logger.info("🧪 renew step 1: 行情数据更新开始...")
        # await self.renew_kline_data(
        #     latest_completed_trading_date=latest_completed_trading_date,
        #     stock_list=stock_list,
        #     test_mode=test_mode,
        #     dry_run=dry_run
        # )

        # 2. 再更新标签数据（非 dry_run 模式才真正写入）
        # logger.info("🧪 renew step 2: 复权因子数据更新开始...")
        # await self.renew_adj_factor_data(
        #     latest_completed_trading_date=latest_completed_trading_date,
        #     stock_list=stock_list,
        #     test_mode=test_mode,
        #     dry_run=dry_run,
        # )

        # logger.info("🧪 renew step 3: 企业财务数据更新开始...")
        # await self.renew_corporate_finance_data(
        #     latest_completed_trading_date=latest_completed_trading_date,
        #     stock_list=stock_list,
        #     test_mode=test_mode,
        #     dry_run=dry_run,
        # )

        # logger.info("🧪 renew step 4: 价格指数数据更新开始...")
        # await self.renew_price_indexes_data(
        #     latest_completed_trading_date=latest_completed_trading_date,
        #     test_mode=test_mode,
        #     dry_run=dry_run,
        # )

        # logger.info("🧪 renew step 4: 宏观经济数据更新开始...")
        # await self.renew_gdp_data(
        #     latest_completed_trading_date=latest_completed_trading_date,
        #     test_mode=test_mode,
        #     dry_run=dry_run,
        # )
        # await self.renew_shibor_data(
        #     latest_completed_trading_date=latest_completed_trading_date,
        #     test_mode=test_mode,
        #     dry_run=dry_run,
        # )
        # await self.renew_lpr_data(
        #     latest_completed_trading_date=latest_completed_trading_date,
        #     test_mode=test_mode,
        #     dry_run=dry_run,
        # )

        logger.info("🧪 renew step 5: 股票指数指标数据更新开始...")
        await self.renew_index_indicators_data(
            latest_completed_trading_date=latest_completed_trading_date,
            test_mode=test_mode,
            dry_run=dry_run,
        )


        # logger.info("🧪 renew step 5: 股票指数指标数据更新开始...")
        # await self.renew_index_indicators_weight_data(
        #     latest_completed_trading_date=latest_completed_trading_date,
        #     test_mode=test_mode,
        #     dry_run=dry_run,
        # )