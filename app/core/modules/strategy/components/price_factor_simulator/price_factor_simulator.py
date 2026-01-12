#!/usr/bin/env python3
"""
PriceFactorSimulator

基于枚举器 SOT 结果的价格因子模拟器：
- 输入：opportunity_enumerator 的 SOT 版本（opportunities/targets CSV）
- 粒度：单股；每只股票独立模拟（适合多进程）
- 核心：在机会触发时以 1 股入场，按机会结果回放，统计价格因子/信号质量

注意：本模块专注于“因子/信号层”的效果评估，不引入资金约束与账户层面的资金管理。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import csv
import logging
import json
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class PriceFactorSimulatorConfig:
    """
    PriceFactorSimulator 的基础配置

    这些配置中的大部分会从 userspace 策略的 settings 中派生，
    当前类只是一个集中承载体，方便在主进程与 Worker 之间传递。
    """

    # SOT 版本号；"latest" 表示使用最新的 SOT 版本目录
    sot_version: str = "latest"

    # 时间窗口（可选），为空表示使用 SOT 全量时间
    start_date: str = ""
    end_date: str = ""

    # 交易成本（预留字段，当前模拟可以先不扣费用或统一简单处理）
    commission_rate: float = 0.0
    min_commission: float = 0.0
    stamp_duty_rate: float = 0.0
    transfer_fee_rate: float = 0.0

    # 多进程 Worker 数量（沿用 ProcessWorker 的配置约定）
    max_workers: "str | int" = "auto"


class PriceFactorSimulator:
    """
    PriceFactorSimulator 主入口类（主进程）

    主要职责：
    - 解析策略 settings，构建 PriceFactorSimulatorConfig
    - 解析并选择 SOT 版本目录（support: 具体版本号 / latest）
    - 扫描 SOT 目录下的 opportunities/targets CSV
    - 构建每只股票的模拟作业（job_payload）
    - 使用 ProcessWorker 分发到 PriceFactorSimulatorWorker 多进程执行
    - 汇总所有股票的模拟结果，输出整体 summary
    """

    def __init__(self, is_verbose: bool = False) -> None:
        self.is_verbose = is_verbose

    # ------------------------------------------------------------------ #
    # 公共入口
    # ------------------------------------------------------------------ #
    def run(self, strategy_name: str) -> Dict[str, Any]:
        """
        运行 PriceFactorSimulator

        Args:
            strategy_name: 策略名称（对应 userspace/strategies/{strategy_name}）

        Returns:
            summary: 一个轻量级结果摘要（后续可扩展）
        """
        # 1. 加载策略 settings，并从中抽取 price-factor simulator 的配置
        from app.core.modules.strategy.strategy_manager import StrategyManager
        from app.core.modules.strategy.models.strategy_settings import StrategySettings

        strategy_manager = StrategyManager()
        strategy_info = strategy_manager.strategy_cache.get(strategy_name)
        if not strategy_info:
            raise ValueError(f"[PriceFactorSimulator] 策略不存在: {strategy_name}")

        base_settings = StrategySettings.from_dict(strategy_info["settings"])
        simulator_config = self._build_config_from_settings(base_settings)

        # 2. 解析 SOT 版本目录
        sot_root, version_dir = self._resolve_sot_version_dir(strategy_name, simulator_config.sot_version)
        logger.info(
            f"[PriceFactorSimulator] 使用 SOT 版本: strategy={strategy_name}, "
            f"sot_version={version_dir.name}"
        )

        # 3. 扫描 SOT 目录下的机会/目标文件，按股票分组
        stock_files = self._scan_sot_files(version_dir)
        if not stock_files:
            logger.warning(f"[PriceFactorSimulator] 在 SOT 目录中未找到任何机会文件: {version_dir}")
            return {}

        # 4. 构建 job 列表（每只股票一个作业）
        jobs: List[Dict[str, Any]] = []
        for stock_id, paths in stock_files.items():
            jobs.append(
                {
                    "stock_id": stock_id,
                    "strategy_name": strategy_name,
                    "sot_version_dir": str(version_dir),
                    "opportunities_path": str(paths["opportunities"]),
                    "targets_path": str(paths["targets"]),
                    "config": simulator_config.__dict__,
                }
            )

        # 5. 使用多进程 Worker 执行
        from app.core.infra.worker.multi_process.process_worker import ProcessWorker, ExecutionMode

        max_workers = simulator_config.max_workers
        worker_pool = ProcessWorker(
            max_workers=max_workers,
            execution_mode=ExecutionMode.PROCESS,
            is_verbose=self.is_verbose,
        )

        from app.core.modules.strategy.components.price_factor_simulator import PriceFactorSimulatorWorker

        results: List[Dict[str, Any]] = worker_pool.run(
            jobs=jobs,
            job_executor=PriceFactorSimulatorWorker.execute_job,
        )

        # 6. 汇总结果（先实现一个简单的汇总，后续可以扩展）
        summary = self._aggregate_results(results)

        # 7. 输出到 simulations 目录（当前只返回内存结构，后续可以补写 JSON 落盘）
        return summary

    # ------------------------------------------------------------------ #
    # 配置与 SOT 解析
    # ------------------------------------------------------------------ #
    def _build_config_from_settings(self, settings: "StrategySettings") -> PriceFactorSimulatorConfig:
        """
        从通用 StrategySettings 中提取 PriceFactorSimulator 所需配置。

        当前实现只做最小提取和默认值处理，后续可以根据文档进一步丰富。
        """
        settings_dict = settings.to_dict()
        simulator_cfg = settings_dict.get("simulator", {}) or {}

        sot_version = simulator_cfg.get("sot_version", "latest")
        start_date = simulator_cfg.get("start_date", "") or ""
        end_date = simulator_cfg.get("end_date", "") or ""

        fees_cfg = simulator_cfg.get("fees", {}) or {}
        commission_rate = float(fees_cfg.get("commission_rate", 0.0) or 0.0)
        min_commission = float(fees_cfg.get("min_commission", 0.0) or 0.0)
        stamp_duty_rate = float(fees_cfg.get("stamp_duty_rate", 0.0) or 0.0)
        transfer_fee_rate = float(fees_cfg.get("transfer_fee_rate", 0.0) or 0.0)

        performance_cfg = settings_dict.get("performance", {}) or {}
        max_workers = performance_cfg.get("max_workers", "auto")

        return PriceFactorSimulatorConfig(
            sot_version=sot_version,
            start_date=start_date,
            end_date=end_date,
            commission_rate=commission_rate,
            min_commission=min_commission,
            stamp_duty_rate=stamp_duty_rate,
            transfer_fee_rate=transfer_fee_rate,
            max_workers=max_workers,
        )

    def _resolve_sot_version_dir(self, strategy_name: str, sot_version: str) -> Tuple[Path, Path]:
        """
        解析 SOT 版本目录：
        - 若 sot_version == "latest": 选择 `sot/` 下版本号最大的目录
        - 否则: 直接使用给定版本号
        """
        root = (
            Path("app")
            / "userspace"
            / "strategies"
            / strategy_name
            / "results"
            / "opportunity_enums"
            / "sot"
        )
        if not root.exists():
            raise FileNotFoundError(f"[PriceFactorSimulator] SOT 根目录不存在: {root}")

        if sot_version == "latest":
            candidates = [p for p in root.iterdir() if p.is_dir() and "_" in p.name]
            if not candidates:
                raise FileNotFoundError(f"[PriceFactorSimulator] SOT 目录下没有任何版本: {root}")
            # 版本名形如: {version_id}_{YYYYMMDD_HHMMSS}，直接按 name 排序即可
            version_dir = sorted(candidates, key=lambda p: p.name)[-1]
            return root, version_dir

        version_dir = root / sot_version
        if not version_dir.exists() or not version_dir.is_dir():
            raise FileNotFoundError(
                f"[PriceFactorSimulator] 指定 SOT 版本目录不存在: {version_dir}"
            )
        return root, version_dir

    def _scan_sot_files(self, version_dir: Path) -> Dict[str, Dict[str, Path]]:
        """
        扫描指定 SOT 版本目录下的 opportunities/targets 文件，按股票进行分组。

        约定文件名格式：
            {stock_id}_opportunities.csv
            {stock_id}_targets.csv
        """
        stock_files: Dict[str, Dict[str, Path]] = defaultdict(dict)

        for entry in version_dir.iterdir():
            if not entry.is_file():
                continue
            name = entry.name
            if name.endswith("_opportunities.csv"):
                stock_id = name[: -len("_opportunities.csv")]
                stock_files[stock_id]["opportunities"] = entry
            elif name.endswith("_targets.csv"):
                stock_id = name[: -len("_targets.csv")]
                stock_files[stock_id]["targets"] = entry

        # 只保留同时存在 opportunities 和 targets 的股票
        filtered: Dict[str, Dict[str, Path]] = {}
        for stock_id, paths in stock_files.items():
            if "opportunities" in paths and "targets" in paths:
                filtered[stock_id] = paths

        return filtered

    # ------------------------------------------------------------------ #
    # 结果汇总（初版）
    # ------------------------------------------------------------------ #
    def _aggregate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        将各 Worker 的结果聚合为一个 summary。

        当前实现只做一个非常轻量的统计：
        - 总股票数
        - 总参与机会数
        - 按股票的机会数量
        后续可以根据 PriceFactorSimulator 设计文档进一步丰富。
        """
        if not results:
            return {}

        stock_summaries: Dict[str, Dict[str, Any]] = {}
        total_opportunities = 0

        for r in results:
            if not r.get("success", False):
                logger.warning(
                    f"[PriceFactorSimulator] Worker 处理失败: stock={r.get('stock_id')}, "
                    f"error={r.get('error')}"
                )
                continue

            stock_id = r.get("stock_id")
            opp_count = int(r.get("opportunity_count", 0))
            total_opportunities += opp_count
            stock_summaries[stock_id] = {
                "stock_id": stock_id,
                "opportunity_count": opp_count,
            }

        summary: Dict[str, Any] = {
            "summary": {
                "total_stocks": len(stock_summaries),
                "total_opportunity_count": total_opportunities,
            },
            "per_stock": stock_summaries,
        }
        return summary


class PriceFactorSimulatorWorker:
    """
    PriceFactorSimulator 的 Worker（子进程）

    当前版本实现了一个“按股统计机会数量”的最小 MVP：
    - 解析该股的 opportunities CSV
    - 返回 opportunity 总数

    后续可以逐步根据 PriceFactorSimulator 设计文档，将完整的
    1 股级机会回放逻辑（trigger/target/T+1/钩子等）填充进来。
    """

    def __init__(self, job_payload: Dict[str, Any]) -> None:
        self.job_payload = job_payload
        self.stock_id: str = job_payload["stock_id"]
        self.strategy_name: str = job_payload["strategy_name"]
        self.opportunities_path = Path(job_payload["opportunities_path"])
        self.targets_path = Path(job_payload["targets_path"])
        self.config_dict: Dict[str, Any] = job_payload.get("config", {})

    # ------------------------------------------------------------------ #
    # 静态入口（供 ProcessWorker 使用）
    # ------------------------------------------------------------------ #
    @staticmethod
    def execute_job(job_payload: Dict[str, Any]) -> Dict[str, Any]:
        worker = PriceFactorSimulatorWorker(job_payload)
        return worker.run()

    # ------------------------------------------------------------------ #
    # 主执行逻辑（当前为最小实现）
    # ------------------------------------------------------------------ #
    def run(self) -> Dict[str, Any]:
        try:
            # 目前只做一个简单统计：该股有多少条机会记录
            opportunity_count = self._count_opportunities()

            return {
                "success": True,
                "stock_id": self.stock_id,
                "opportunity_count": opportunity_count,
            }
        except Exception as e:
            logger.error(f"[PriceFactorSimulatorWorker] 处理股票失败: stock={self.stock_id}, error={e}")
            return {
                "success": False,
                "stock_id": self.stock_id,
                "opportunity_count": 0,
                "error": str(e),
            }

    def _count_opportunities(self) -> int:
        """
        读取 opportunities CSV，统计机会数量。

        这是 PriceFactorSimulator 的最小 MVP，
        后续会在这里扩展为完整的事件回放逻辑。
        """
        path = self.opportunities_path
        if not path.exists():
            logger.warning(f"[PriceFactorSimulatorWorker] opportunities 文件不存在: {path}")
            return 0

        count = 0
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for _ in reader:
                count += 1
        return count

