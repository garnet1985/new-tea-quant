"""BFF API 统一入口。"""

from flask import jsonify
from pathlib import Path

from .APIs.stock_api import StockApi
from .APIs.investment_api import InvestmentApi
from .setup_runtime import SetupRuntimeManager
from core.infra.project_context.path_manager import PathManager
from core.modules.data_manager import DataManager
from setup.meta_loader import load_setup_step_meta


class BFFApi:
    """BFF API 统一入口类"""
    
    def __init__(self):
        """初始化 BFF API。"""
        # DataManager 改为惰性初始化，避免 /api/health 在 setup 前强依赖数据库。
        self._data_mgr = None
        
        # 初始化业务API（惰性创建）
        self._stock_api = None
        self._investment_api = None
        self._setup_runtime = SetupRuntimeManager()

    @property
    def data_mgr(self):
        """DataManager（延迟初始化）"""
        if self._data_mgr is None:
            self._data_mgr = DataManager(is_verbose=False)
        return self._data_mgr
    
    @property
    def stock_api(self):
        """股票API（延迟初始化）"""
        if self._stock_api is None:
            self._stock_api = StockApi(data_mgr=self.data_mgr)
        return self._stock_api
    
    @property
    def investment_api(self):
        """投资API（延迟初始化）"""
        if self._investment_api is None:
            # InvestmentApi 依赖 DataManager；这里与 stock_api 共享同一实例。
            self._investment_api = InvestmentApi(data_mgr=self.data_mgr)
        return self._investment_api
    
    # ==================== 健康检查 ====================
    
    def health_check(self):
        """健康检查"""
        return jsonify({
            "success": True,
            "message": "BFF API 运行正常",
            "timestamp": "当前时间"
        })

    def get_setup_definition(self):
        """获取 setup 步骤定义（来自 setup/*/meta.json）"""
        steps = load_setup_step_meta(ui_only=True)
        userspace_abs_path = str(PathManager.userspace().resolve())
        userspace_exists = Path(userspace_abs_path).exists()
        for step in steps:
            if step.get("id") == "init_userspace":
                step["name"] = "初始化 userspace"
                schema = step.get("inputSchema") or step.get("requiredUserInputs") or []
                filtered_schema = []
                for field in schema:
                    if field.get("key") == "userspaceTargetPath":
                        field["label"] = "userspace 路径"
                        field["defaultValue"] = userspace_abs_path
                        field["helperText"] = "默认使用该绝对路径；勾选后可改成你自己的路径。"
                        field["editableByCheckbox"] = True
                        field["editableLabel"] = "我想自定义 userspace 路径"
                        filtered_schema.append(field)
                        continue
                    if field.get("key") == "userspaceConflictPolicy":
                        # 前端默认隐藏该字段；仅当目标路径已存在时显示（默认路径是否显示由该标记决定）。
                        field["showByDefault"] = bool(userspace_exists)
                        filtered_schema.append(field)
                        continue
                    filtered_schema.append(field)
                step["inputSchema"] = filtered_schema
            elif step.get("id") == "import_data":
                step["name"] = "导入初始化数据"
        return jsonify({
            "status": "ok",
            "message": {
                "steps": steps
            }
        })

    def get_setup_status(self):
        return jsonify({"status": "ok", "message": self._setup_runtime.get_status()})

    def start_setup(self):
        return jsonify(self._setup_runtime.start())

    def submit_setup_step(self, step_id: str, inputs: dict):
        return jsonify(self._setup_runtime.submit(step_id, inputs or {}))

    def retry_setup(self):
        return jsonify(self._setup_runtime.retry())

    def reset_setup(self):
        return jsonify(self._setup_runtime.reset())

    def precheck_db_connection(self, inputs: dict):
        return jsonify(self._setup_runtime.precheck_db_connection(inputs or {}))

    def precheck_userspace_path(self, inputs: dict):
        return jsonify(self._setup_runtime.precheck_userspace_path(inputs or {}))

    def get_import_data_progress(self):
        return jsonify(self._setup_runtime.get_import_data_progress())
    
    # ==================== 股票相关 API ====================
    
    def get_stock_kline(self, stock_id: str, term: str = 'daily'):
        """获取股票K线数据"""
        return self.stock_api.get_stock_kline(stock_id, term)
    
    def get_stock_scan(self, strategy: str, stock_id: str):
        """获取股票策略扫描结果"""
        return self.stock_api.get_stock_scan(strategy, stock_id)
    
    def get_stock_simulate(self, strategy: str, stock_id: str):
        """获取股票策略模拟结果"""
        return self.stock_api.get_stock_simulate(strategy, stock_id)

    def get_stock_hl_analysis(self, stock_id: str):
        """获取股票 HL 策略分析结果。"""
        return self.stock_api.get_stock_hl_analysis(stock_id)

    def get_stock_all_historic_lows(self, stock_id: str):
        """获取股票所有历史低点。"""
        return self.stock_api.get_stock_all_historic_lows(stock_id)
    
    # ==================== 投资相关 API ====================
    
    def get_all_closed_trades(self):
        """获取所有已关闭的交易"""
        return self.investment_api.get_all_closed_trades()

    def get_all_open_trades(self):
        """获取所有进行中的交易。"""
        return self.investment_api.get_all_open_trades()
    
    def get_open_positions(self):
        """获取当前持仓（兼容旧方法，转发到 open trades）。"""
        return self.investment_api.get_all_open_trades()
    
    def get_trades_by_stock(self, stock_id: str):
        """按股票获取交易记录"""
        return self.investment_api.get_trades_by_stock(stock_id)
    
    def get_investment_overview(self):
        """获取投资概览（当前 BFF 未提供专用聚合，先返回 open trades）。"""
        return self.investment_api.get_all_open_trades()

    def get_trade_detail(self, trade_id: int):
        """获取单笔交易详情。"""
        return self.investment_api.get_trade_detail(trade_id)

    def get_trade_operations(self, trade_id: int):
        """获取交易操作列表。"""
        return self.investment_api.get_trade_operations(trade_id)

    def create_trade(self, data: dict):
        """创建交易。"""
        return self.investment_api.create_trade(data)

    def create_operation(self, trade_id: int, data: dict):
        """创建交易操作。"""
        return self.investment_api.create_operation(trade_id, data)

    def get_strategies_list(self):
        """获取策略列表。"""
        return self.investment_api.get_strategies_list()

    def search_stocks(self, keyword: str):
        """搜索股票（自动完成）。"""
        return self.investment_api.search_stocks(keyword)

    def update_trade(self, trade_id: int, data: dict):
        """更新交易。"""
        return self.investment_api.update_trade(trade_id, data)

    def delete_trade(self, trade_id: int):
        """删除交易。"""
        return self.investment_api.delete_trade(trade_id)

    def update_operation(self, trade_id: int, operation_id: int, data: dict):
        """更新交易操作。"""
        return self.investment_api.update_operation(trade_id, operation_id, data)

    def delete_operation(self, trade_id: int, operation_id: int):
        """删除交易操作。"""
        return self.investment_api.delete_operation(trade_id, operation_id)


