"""BFF API 统一入口。"""

from flask import jsonify
from pathlib import Path

from .setup_runtime import SetupRuntimeManager
from core.infra.project_context.path_manager import PathManager
from setup.meta_loader import load_setup_step_meta


class BFFApi:
    """BFF API 统一入口类"""
    
    def __init__(self):
        """初始化 BFF API。"""
        self._setup_runtime = SetupRuntimeManager()
    
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

    # ==================== 策略工作台（v1） ====================

    def get_strategies(self):
        """
        获取已发现策略列表（策略工作台 list 页使用）。

        返回结构与前端 requestJson 约定一致：status=ok，列表挂在 message.strategies。
        """
        try:
            from core.modules.strategy.helpers.strategy_discovery_helper import StrategyDiscoveryHelper

            strategies = []
            discovered = StrategyDiscoveryHelper.discover_strategies()
            for _name, info in (discovered or {}).items():
                meta = getattr(info.settings, "meta", None)
                strategies.append({
                    "key": str(info.folder.name),
                    "name": str(getattr(meta, "name", info.name)),
                    "description": str(getattr(meta, "description", "") or ""),
                    "is_enabled": bool(getattr(meta, "is_enabled", False)),
                })

            strategies.sort(key=lambda x: x.get("key", ""))
            return jsonify({"status": "ok", "message": {"strategies": strategies}})
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": {"detail": f"获取策略列表失败: {str(e)}"},
            }), 500

    def get_strategy_settings_options_allocation_modes(self):
        """
        资金分配策略下拉选项（capital_simulator.allocation.mode）。
        ``value`` 必须与 ``StrategyCapitalAllocationSettings`` 校验集合一致。
        """
        try:
            from core.modules.strategy.data_classes.strategy_settings.capital_allocation_settings import (
                _VALID_MODES,
            )

            ordered = (
                ("equal_capital", "每个机会均等资金买入"),
                ("equal_shares", "每个机会均等股数买入"),
                ("kelly", "凯莉公式"),
                ("custom", "自定义"),
            )
            options = [{"value": v, "label": lbl} for v, lbl in ordered if v in _VALID_MODES]
            missing = _VALID_MODES - {o["value"] for o in options}
            if missing:
                for v in sorted(missing):
                    options.append({"value": v, "label": v})

            # 前端可根据 profile 控制字段显隐/校验提示，避免把 mode 规则写死在 FED。
            profiles = {
                "equal_capital": {
                    "configurable_fields": [
                        "allocation.max_portfolio_size",
                        "allocation.max_weight_per_stock",
                    ],
                    "required_fields": [],
                },
                "equal_shares": {
                    "configurable_fields": [
                        "allocation.max_portfolio_size",
                        "allocation.max_weight_per_stock",
                        "allocation.lot_size",
                        "allocation.lots_per_trade",
                    ],
                    "required_fields": ["allocation.lot_size", "allocation.lots_per_trade"],
                },
                "kelly": {
                    "configurable_fields": [
                        "allocation.max_portfolio_size",
                        "allocation.max_weight_per_stock",
                        "allocation.kelly_fraction",
                    ],
                    "required_fields": ["allocation.kelly_fraction"],
                },
                "custom": {
                    "configurable_fields": [
                        "allocation.max_portfolio_size",
                        "allocation.max_weight_per_stock",
                    ],
                    "required_fields": [],
                },
            }
            return jsonify({"status": "ok", "message": {"options": options, "profiles": profiles}})
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": {"detail": f"获取资金分配选项失败: {str(e)}"},
            }), 500

    def get_strategy_settings_options_sampling_strategies(self):
        """
        采样策略下拉选项（sampling.strategy）。
        ``value`` 必须与 ``StrategySamplingSettings.validate`` 所用 ``KNOWN_STRATEGIES`` 一致。
        """
        try:
            from core.modules.strategy.data_classes.strategy_settings.sampling_settings import (
                KNOWN_STRATEGIES,
            )

            ordered = (
                ("continuous", "连续采样（默认）"),
                ("uniform", "均匀采样"),
                ("stratified", "分层采样"),
                ("random", "随机采样"),
                ("pool", "指定股票池采样"),
                ("blacklist", "排除黑名单采样"),
            )
            options = [{"value": v, "label": lbl} for v, lbl in ordered if v in KNOWN_STRATEGIES]
            missing = KNOWN_STRATEGIES - {o["value"] for o in options}
            if missing:
                for v in sorted(missing):
                    options.append({"value": v, "label": v})

            profiles = {
                "continuous": {
                    "configurable_fields": ["sampling.sampling_amount", "sampling.continuous.start_idx"],
                    "required_fields": [],
                },
                "uniform": {
                    "configurable_fields": ["sampling.sampling_amount"],
                    "required_fields": [],
                },
                "stratified": {
                    "configurable_fields": ["sampling.sampling_amount", "sampling.stratified.seed"],
                    "required_fields": [],
                },
                "random": {
                    "configurable_fields": ["sampling.sampling_amount", "sampling.random.seed"],
                    "required_fields": [],
                },
                "pool": {
                    "configurable_fields": [
                        "sampling.sampling_amount",
                        "sampling.pool.stock_ids",
                        "sampling.pool.file",
                    ],
                    "required_fields": [],
                },
                "blacklist": {
                    "configurable_fields": [
                        "sampling.sampling_amount",
                        "sampling.blacklist.stock_ids",
                        "sampling.blacklist.file",
                    ],
                    "required_fields": [],
                },
            }
            return jsonify({"status": "ok", "message": {"options": options, "profiles": profiles}})
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": {"detail": f"获取采样策略选项失败: {str(e)}"},
            }), 500

