#!/usr/bin/env python3
"""
策略 ``price_simulator`` 配置块（对应 ``settings_example`` 第 8) 节）。

与 ``PriceFactorSimulator`` 使用的字段对齐：``use_sampling``、``base_version``、
``max_workers``、``start_date`` / ``end_date``（可省略，空字符串表示使用输出版本全时段）、可选 ``fees``。

兼容旧键名 ``output_version``（若存在且未写 ``base_version``，校验时会归并到 ``base_version``）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, Literal, Union

from .settings_base import SettingsBase, ValidationReport

logger = logging.getLogger(__name__)


@dataclass
class StrategyPriceSimulatorSettings(SettingsBase):
    """整包 ``raw_settings`` 引用 + ``price_simulator`` 子树访问与校验。"""

    raw_settings: Dict[str, Any]
    _missing_use_sampling_at_load: bool = field(default=False, repr=False)
    _price_simulator_validated: bool = field(default=False, repr=False)

    @property
    def price_simulator(self) -> Dict[str, Any]:
        block = self.raw_settings.get("price_simulator")
        if not isinstance(block, dict):
            block = {}
            self.raw_settings["price_simulator"] = block
        return block

    @classmethod
    def from_strategy_root(cls, root: Dict[str, Any]) -> StrategyPriceSimulatorSettings:
        if not isinstance(root, dict):
            root = {}
        block = root.get("price_simulator")
        missing_us = not isinstance(block, dict) or "use_sampling" not in block
        if not isinstance(block, dict):
            block = {}
            root["price_simulator"] = block
        return cls(raw_settings=root, _missing_use_sampling_at_load=missing_us)

    @classmethod
    def from_base_settings(cls, base_settings: "StrategySettings") -> StrategyPriceSimulatorSettings:
        return cls.from_strategy_root(base_settings.raw_settings)

    def apply_defaults(self) -> None:
        """与 ``settings_example`` 及 ``PriceFactorSimulator`` 读取逻辑对齐。"""
        ps = self.price_simulator
        if "use_sampling" not in ps:
            ps["use_sampling"] = False
        if "base_version" not in ps and "output_version" in ps:
            ps["base_version"] = ps.get("output_version") or "latest"
        if "base_version" not in ps:
            ps["base_version"] = "latest"
        if "max_workers" not in ps:
            ps["max_workers"] = "auto"
        if "start_date" not in ps:
            ps["start_date"] = ""
        if "end_date" not in ps:
            ps["end_date"] = ""

    def validate(self) -> ValidationReport:
        result = SettingsBase.new_validation()
        self.apply_defaults()

        bv = str(self.price_simulator.get("base_version") or "latest")
        if bv != "latest":
            SettingsBase.add_warning(
                result,
                "price_simulator.base_version",
                f"指定枚举依赖版本 {bv!r}，将在运行时解析；不存在时将回退 latest",
                suggested_fix="若目录不存在，请先跑枚举或改用 latest",
            )

        if self._missing_use_sampling_at_load:
            SettingsBase.add_warning(
                result,
                "price_simulator.use_sampling",
                "use_sampling 未配置，已默认 False（读 output/ 全量枚举结果）",
                suggested_fix='需要读 test/ 时设置 "use_sampling": True',
            )

        self._validate_max_workers(result)
        self._validate_fees_if_present(result)

        SettingsBase.log_warnings(result, logger)
        self._price_simulator_validated = True
        return result

    def _validate_max_workers(self, result: ValidationReport) -> None:
        ps = self.price_simulator
        mw = ps.get("max_workers", "auto")
        if mw == "auto" or mw is None:
            ps["max_workers"] = "auto"
            return
        try:
            ps["max_workers"] = max(int(mw), 1)
        except (TypeError, ValueError):
            SettingsBase.add_critical(
                result,
                "price_simulator.max_workers",
                'price_simulator.max_workers 须为 "auto" 或正整数',
                suggested_fix='设为 "auto" 或例如 4',
            )

    def _validate_fees_if_present(self, result: ValidationReport) -> None:
        fees = self.price_simulator.get("fees")
        if fees is None:
            return
        if not isinstance(fees, dict):
            SettingsBase.add_critical(
                result,
                "price_simulator.fees",
                "fees 必须为对象（dict）",
                suggested_fix="删除 fees 或改为与顶层 fees 相同的对象结构",
            )
            return
        required = (
            "commission_rate",
            "min_commission",
            "stamp_duty_rate",
            "transfer_fee_rate",
        )
        for k in required:
            if k not in fees:
                SettingsBase.add_warning(
                    result,
                    f"price_simulator.fees.{k}",
                    f"模拟器 fees 缺少 {k}，将回退到顶层 fees 或内置默认",
                    suggested_fix=f'在 price_simulator.fees 中补充 "{k}"',
                )

    def to_dict(self) -> Dict[str, Any]:
        return self.deep_copy_dict(dict(self.price_simulator))

    @property
    def use_sampling(self) -> bool:
        return bool(self.price_simulator.get("use_sampling", False))

    @property
    def base_version(self) -> str:
        ps = self.price_simulator
        return str(ps.get("base_version") or ps.get("output_version") or "latest") or "latest"

    @property
    def start_date(self) -> str:
        return str(self.price_simulator.get("start_date", "") or "")

    @property
    def end_date(self) -> str:
        return str(self.price_simulator.get("end_date", "") or "")

    @property
    def max_workers(self) -> Union[Literal["auto"], int]:
        mw = self.price_simulator.get("max_workers", "auto")
        if mw == "auto" or mw is None:
            return "auto"
        try:
            return max(int(mw), 1)
        except (TypeError, ValueError):
            return "auto"

    @property
    def fees(self) -> Dict[str, Any]:
        f = self.price_simulator.get("fees")
        return f if isinstance(f, dict) else {}

    def get_default_date_range(self) -> tuple[str, str]:
        """默认回测窗口（需 DataManager）；与历史行为一致。"""
        from core.modules.data_manager import DataManager
        from core.utils.date.date_utils import DateUtils

        data_mgr = DataManager(is_verbose=False)
        start_date = DateUtils.DEFAULT_START_DATE
        try:
            end_date = data_mgr.service.calendar.get_latest_completed_trading_date()
        except Exception as exc:
            logger.warning("无法获取最新交易日: %s", exc)
            end_date = ""
        return start_date, end_date


# 旧文件名/类名兼容
StrategyPriceFactorSimulationSettings = StrategyPriceSimulatorSettings
