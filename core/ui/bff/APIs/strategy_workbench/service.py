"""Strategy workbench service logic."""

from pprint import pformat

from core.infra.project_context.config_manager import ConfigManager
from core.infra.project_context.path_manager import PathManager
from core.ui.bff.shared.file_ops import atomic_write_text, backup_file
from core.ui.bff.shared.response import error, ok


class StrategyWorkbenchService:
    """策略工作台业务服务（不包含 route 绑定）。"""

    def get_strategies(self):
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
            return ok({"strategies": strategies})
        except Exception as e:
            return error(f"获取策略列表失败: {str(e)}", 500)

    def get_strategy_settings_options_allocation_modes(self):
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
            return ok({"options": options, "profiles": profiles})
        except Exception as e:
            return error(f"获取资金分配选项失败: {str(e)}", 500)

    def get_strategy_settings_options_sampling_strategies(self):
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
            return ok({"options": options, "profiles": profiles})
        except Exception as e:
            return error(f"获取采样策略选项失败: {str(e)}", 500)

    def _runtime_to_api_settings(self, runtime_settings):
        if not isinstance(runtime_settings, dict):
            return {}
        api_settings = dict(runtime_settings)
        meta_from_runtime = {
            "name": runtime_settings.get("name", ""),
            "description": runtime_settings.get("description", ""),
            "is_enabled": bool(runtime_settings.get("is_enabled", False)),
        }
        existing_meta = runtime_settings.get("meta")
        if isinstance(existing_meta, dict):
            meta_from_runtime.update({
                "name": existing_meta.get("name", meta_from_runtime["name"]),
                "description": existing_meta.get("description", meta_from_runtime["description"]),
                "is_enabled": bool(existing_meta.get("is_enabled", meta_from_runtime["is_enabled"])),
            })
        api_settings["meta"] = meta_from_runtime
        return api_settings

    def _api_to_runtime_settings(self, api_settings):
        if not isinstance(api_settings, dict):
            return {}
        runtime = dict(api_settings)
        meta = runtime.get("meta")
        if isinstance(meta, dict):
            runtime["name"] = meta.get("name", runtime.get("name", ""))
            runtime["description"] = meta.get("description", runtime.get("description", ""))
            runtime["is_enabled"] = bool(meta.get("is_enabled", runtime.get("is_enabled", False)))
        return runtime

    def get_strategy_settings(self, strategy_name: str):
        try:
            strategy_dir = PathManager.strategy(strategy_name)
            settings_file = PathManager.strategy_settings(strategy_name)
            if not strategy_dir.exists() or not strategy_dir.is_dir():
                return error(f"策略不存在: {strategy_name}", 404)
            if not settings_file.exists():
                return error(f"策略缺少 settings.py: {strategy_name}", 404)

            runtime_settings = ConfigManager.load_python(settings_file, var_name="settings")
            if not isinstance(runtime_settings, dict):
                return error(f"策略 settings 无效: {strategy_name}", 500)

            return ok({
                "strategy_name": strategy_name,
                "settings": self._runtime_to_api_settings(runtime_settings),
            })
        except Exception as e:
            return error(f"读取策略 settings 失败: {str(e)}", 500)

    def save_strategy_settings(self, strategy_name: str, payload: dict):
        try:
            if not isinstance(payload, dict):
                return error("请求体必须为对象", 400)
            settings = payload.get("settings")
            if not isinstance(settings, dict):
                return error("请求体缺少 settings 或类型错误", 400)

            strategy_dir = PathManager.strategy(strategy_name)
            settings_file = PathManager.strategy_settings(strategy_name)
            if not strategy_dir.exists() or not strategy_dir.is_dir() or not settings_file.exists():
                return error(f"策略不存在: {strategy_name}", 404)

            runtime_settings = self._api_to_runtime_settings(settings)
            runtime_settings["name"] = strategy_name

            from core.modules.strategy.data_classes.strategy_settings.strategy_settings import (
                StrategySettings,
            )
            validated = StrategySettings(raw_settings=dict(runtime_settings))
            report = validated.validate()
            if not report.is_usable():
                critical_errors = [
                    f"{item.get('field_path', 'unknown')}: {item.get('message', '')}"
                    for item in (report.errors or [])
                    if item.get("level") == "critical"
                ]
                detail = "；".join(critical_errors) if critical_errors else "settings 校验失败"
                return error(detail, 422)

            normalized_runtime_settings = validated.to_dict()
            normalized_runtime_settings["name"] = strategy_name
            formatted = pformat(normalized_runtime_settings, width=100, sort_dicts=False)
            output_text = (
                "# Auto-generated by Strategy Workbench BFF API.\n"
                "# Manual edits are allowed, but next save may reformat this file.\n\n"
                f"settings = {formatted}\n"
            )

            backup_file(settings_file)
            atomic_write_text(settings_file, output_text)

            return ok({
                "strategy_name": strategy_name,
                "saved": True,
            })
        except Exception as e:
            return error(f"保存策略 settings 失败: {str(e)}", 500)
