#!/usr/bin/env python3
"""
策略 ``capital_simulator`` 配置块（对应 ``settings_example`` 第 9) 节）。

持有整包 ``raw_settings``，便于 ``get_fees_config_with_priority`` 读取
``capital_simulator.fees`` / ``price_simulator.fees`` / 顶层 ``fees``。
``start_date`` / ``end_date`` 可省略，空表示使用枚举输出全时段。
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, Literal, Union

from .settings_base import SettingsBase, ValidationReport

logger = logging.getLogger(__name__)

_VALID_MODES = frozenset({"equal_capital", "equal_shares", "kelly", "custom"})


@dataclass
class AllocationConfig:
    """``capital_simulator.allocation`` 解析视图。"""

    mode: str = "equal_capital"
    max_portfolio_size: int = 10
    max_weight_per_stock: float = 0.3
    lot_size: int = 100
    lots_per_trade: int = 1
    kelly_fraction: float = 0.5


@dataclass
class OutputConfig:
    """``capital_simulator.output`` 解析视图。"""

    save_trades: bool = True
    save_equity_curve: bool = True


@dataclass
class StrategyCapitalSimulatorSettings(SettingsBase):
    """资金分配模拟器：``capital_simulator`` 子树 + 校验/默认值。"""

    raw_settings: Dict[str, Any]
    _missing_use_sampling_at_load: bool = field(default=False, repr=False)
    _capital_simulator_validated: bool = field(default=False, repr=False)

    @property
    def capital_simulator(self) -> Dict[str, Any]:
        block = self.raw_settings.get("capital_simulator")
        if not isinstance(block, dict):
            block = {}
            self.raw_settings["capital_simulator"] = block
        return block

    @classmethod
    def from_strategy_root(cls, root: Dict[str, Any]) -> StrategyCapitalSimulatorSettings:
        if not isinstance(root, dict):
            root = {}
        block = root.get("capital_simulator")
        missing_us = not isinstance(block, dict) or "use_sampling" not in block
        if not isinstance(block, dict):
            block = {}
            root["capital_simulator"] = block
        return cls(raw_settings=root, _missing_use_sampling_at_load=missing_us)

    @classmethod
    def from_base_settings(cls, base_settings: "StrategySettings") -> StrategyCapitalSimulatorSettings:
        return cls.from_strategy_root(base_settings.raw_settings)

    def apply_defaults(self) -> None:
        """与 ``settings_example`` 第 9 节默认一致。"""
        c = self.capital_simulator
        if "use_sampling" not in c:
            c["use_sampling"] = False
        if "base_version" not in c:
            c["base_version"] = "latest"
        if "initial_capital" not in c:
            c["initial_capital"] = 1_000_000
        if "start_date" not in c:
            c["start_date"] = ""
        if "end_date" not in c:
            c["end_date"] = ""

        alloc = c.get("allocation")
        if not isinstance(alloc, dict):
            alloc = {}
            c["allocation"] = alloc
        if "mode" not in alloc:
            alloc["mode"] = "equal_capital"
        if "max_portfolio_size" not in alloc:
            alloc["max_portfolio_size"] = 10
        if "max_weight_per_stock" not in alloc:
            alloc["max_weight_per_stock"] = 0.3
        if "lot_size" not in alloc:
            alloc["lot_size"] = 100
        if "lots_per_trade" not in alloc:
            alloc["lots_per_trade"] = 1
        if "kelly_fraction" not in alloc:
            alloc["kelly_fraction"] = 0.5

        out = c.get("output")
        if not isinstance(out, dict):
            out = {}
            c["output"] = out
        if "save_trades" not in out:
            out["save_trades"] = True
        if "save_equity_curve" not in out:
            out["save_equity_curve"] = True

    def validate(self) -> ValidationReport:
        result = SettingsBase.new_validation()
        self.apply_defaults()

        alloc = self._parse_allocation()
        try:
            ic = float(self.capital_simulator.get("initial_capital", 1_000_000))
        except (TypeError, ValueError):
            ic = 0.0
        self.capital_simulator["initial_capital"] = max(ic, 0.0)

        if self.capital_simulator["initial_capital"] < 1000:
            SettingsBase.add_critical(
                result,
                "capital_simulator.initial_capital",
                (
                    f"initial_capital ({self.capital_simulator['initial_capital']}) 必须 >= 1000 元，"
                    "否则无法购买任何股票"
                ),
                suggested_fix='在 capital_simulator 中将 "initial_capital" 设为至少 1000',
            )

        if alloc.mode not in _VALID_MODES:
            SettingsBase.add_critical(
                result,
                "capital_simulator.allocation.mode",
                f"allocation.mode ({alloc.mode!r}) 必须是: {sorted(_VALID_MODES)}",
                suggested_fix='将 "mode" 设为 equal_capital / equal_shares / kelly / custom 之一',
            )

        if alloc.max_portfolio_size <= 0:
            SettingsBase.add_critical(
                result,
                "capital_simulator.allocation.max_portfolio_size",
                f"max_portfolio_size ({alloc.max_portfolio_size}) 必须 > 0",
                suggested_fix='将 "max_portfolio_size" 设为大于 0 的整数',
            )

        bv = str(self.capital_simulator.get("base_version") or "latest")
        if bv != "latest":
            SettingsBase.add_warning(
                result,
                "capital_simulator.base_version",
                f"指定枚举依赖版本 {bv!r}，将在运行时解析；不存在时将回退 latest",
                suggested_fix="若目录不存在，请先跑枚举或改用 latest",
            )

        fees_config = self.get_fees_config_with_priority()
        if not fees_config or all(
            fees_config.get(key, 0.0) == 0.0
            for key in ("commission_rate", "stamp_duty_rate", "transfer_fee_rate")
        ):
            SettingsBase.add_warning(
                result,
                "fees",
                "fees 配置缺失或主要费率为 0，可能忽略部分交易费用",
                suggested_fix="在顶层 fees、price_simulator.fees 或 capital_simulator.fees 中补充费率",
            )

        if self._missing_use_sampling_at_load:
            SettingsBase.add_warning(
                result,
                "capital_simulator.use_sampling",
                "use_sampling 未配置，已默认 False（读 output/ 全量枚举结果）",
                suggested_fix='需要读 test/ 时设置 "use_sampling": True',
            )

        self._validate_max_workers(result)
        self._validate_fees_block(result)

        SettingsBase.log_warnings(result, logger)
        self._capital_simulator_validated = True
        return result

    def _validate_max_workers(self, result: ValidationReport) -> None:
        mw = self.capital_simulator.get("max_workers", "auto")
        if mw == "auto" or mw is None:
            self.capital_simulator["max_workers"] = "auto"
            return
        try:
            self.capital_simulator["max_workers"] = max(int(mw), 1)
        except (TypeError, ValueError):
            SettingsBase.add_critical(
                result,
                "capital_simulator.max_workers",
                'capital_simulator.max_workers 须为 "auto" 或正整数',
                suggested_fix='设为 "auto" 或例如 4',
            )

    def _validate_fees_block(self, result: ValidationReport) -> None:
        fees = self.capital_simulator.get("fees")
        if fees is None:
            return
        if not isinstance(fees, dict):
            SettingsBase.add_critical(
                result,
                "capital_simulator.fees",
                "fees 必须为对象（dict）",
                suggested_fix="删除 fees 或改为与顶层 fees 相同结构",
            )

    def _parse_allocation(self) -> AllocationConfig:
        a = self.capital_simulator.get("allocation") or {}
        if not isinstance(a, dict):
            a = {}
            self.capital_simulator["allocation"] = a
        try:
            mps = max(int(a.get("max_portfolio_size", 10)), 1)
        except (TypeError, ValueError):
            mps = 10
        try:
            mw = max(min(float(a.get("max_weight_per_stock", 0.3)), 1.0), 0.0)
        except (TypeError, ValueError):
            mw = 0.3
        try:
            lot = max(int(a.get("lot_size", 100)), 1)
        except (TypeError, ValueError):
            lot = 100
        try:
            lots = max(int(a.get("lots_per_trade", 1)), 1)
        except (TypeError, ValueError):
            lots = 1
        try:
            kf = max(min(float(a.get("kelly_fraction", 0.5)), 1.0), 0.0)
        except (TypeError, ValueError):
            kf = 0.5
        mode = str(a.get("mode", "equal_capital") or "equal_capital")
        return AllocationConfig(
            mode=mode,
            max_portfolio_size=mps,
            max_weight_per_stock=mw,
            lot_size=lot,
            lots_per_trade=lots,
            kelly_fraction=kf,
        )

    def _parse_output(self) -> OutputConfig:
        o = self.capital_simulator.get("output") or {}
        if not isinstance(o, dict):
            o = {}
            self.capital_simulator["output"] = o
        return OutputConfig(
            save_trades=bool(o.get("save_trades", True)),
            save_equity_curve=bool(o.get("save_equity_curve", True)),
        )

    def get_fees_config_with_priority(self) -> Dict[str, Any]:
        """capital_simulator.fees > price_simulator.fees > 顶层 fees。"""
        capital_config = self.raw_settings.get("capital_simulator", {}) or {}
        simulator_config = self.raw_settings.get("price_simulator", {}) or {}
        top_level_fees = self.raw_settings.get("fees", {}) or {}
        if not isinstance(top_level_fees, dict):
            top_level_fees = {}
        return (
            (capital_config.get("fees") if isinstance(capital_config.get("fees"), dict) else None)
            or (simulator_config.get("fees") if isinstance(simulator_config.get("fees"), dict) else None)
            or top_level_fees
            or {}
        )

    def to_dict(self) -> Dict[str, Any]:
        return self.deep_copy_dict(dict(self.capital_simulator))

    @property
    def use_sampling(self) -> bool:
        return bool(self.capital_simulator.get("use_sampling", False))

    @property
    def base_version(self) -> str:
        return str(self.capital_simulator.get("base_version", "latest") or "latest")

    @property
    def initial_capital(self) -> float:
        try:
            return float(self.capital_simulator.get("initial_capital", 1_000_000))
        except (TypeError, ValueError):
            return 1_000_000.0

    @property
    def start_date(self) -> str:
        return str(self.capital_simulator.get("start_date", "") or "")

    @property
    def end_date(self) -> str:
        return str(self.capital_simulator.get("end_date", "") or "")

    @property
    def max_workers(self) -> Union[Literal["auto"], int]:
        mw = self.capital_simulator.get("max_workers", "auto")
        if mw == "auto" or mw is None:
            return "auto"
        try:
            return max(int(mw), 1)
        except (TypeError, ValueError):
            return "auto"

    @property
    def allocation(self) -> AllocationConfig:
        return self._parse_allocation()

    @property
    def output(self) -> OutputConfig:
        return self._parse_output()


CapitalAllocationSettings = StrategyCapitalSimulatorSettings
