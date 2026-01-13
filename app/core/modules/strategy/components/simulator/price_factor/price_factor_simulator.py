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
from typing import Dict, Any, List, Optional
from collections import defaultdict
import logging
import json
from datetime import datetime

from .helpers import DateTimeEncoder
from app.core.modules.strategy.managers.version_manager import VersionManager
from app.core.modules.strategy.managers.data_loader import DataLoader
from app.core.modules.strategy.managers.result_path_manager import ResultPathManager
from app.core.modules.strategy.components.simulator.base.simulator_hooks_dispatcher import (
    SimulatorHooksDispatcher,
)
from .result_presenter import ResultPresenter
from .result_aggregator import ResultAggregator
from .investment_builder import InvestmentBuilder
from .stock_summary_builder import StockSummaryBuilder


logger = logging.getLogger(__name__)


@dataclass
class PriceFactorSimulatorConfig:
    """
    PriceFactorSimulator 的基础配置

    这些配置中的大部分会从 userspace 策略的 settings 中派生，
    当前类只是一个集中承载体，方便在主进程与 Worker 之间传递。
    """

    # SOT 版本号；"latest" 表示使用最新的 SOT 版本目录
    # 支持格式：
    #   - "latest": 使用最新的 SOT 版本
    #   - "1_20260112_161317": 使用指定版本号
    #   - "test/latest": 使用最新的测试版本（test/ 目录）
    #   - "sot/latest": 使用最新的 SOT 版本（sot/ 目录，默认）
    sot_version: str = "latest"

    # 是否使用采样配置（默认 True，使用 sampling 配置过滤股票）
    use_sampling: bool = True

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
        from app.core.modules.strategy.models.strategy_settings import StrategySettings

        # 为避免触发所有策略的全局校验，这里不通过 StrategyManager，
        # 而是直接按模块路径加载指定策略的 settings.py
        import importlib

        settings_module_path = f"app.userspace.strategies.{strategy_name}.settings"
        try:
            settings_module = importlib.import_module(settings_module_path)
        except ModuleNotFoundError as e:
            raise ValueError(
                f"[PriceFactorSimulator] 无法加载策略 settings: {settings_module_path}"
            ) from e

        raw_settings = getattr(settings_module, "settings", None)
        if not isinstance(raw_settings, dict):
            raise ValueError(
                f"[PriceFactorSimulator] 策略 {strategy_name} 的 settings.py 中缺少 'settings' 字典"
            )

        base_settings = StrategySettings.from_dict(raw_settings)
        simulator_config = self._build_config_from_settings(base_settings)

        # 2. 解析 SOT 版本目录（依赖的枚举版本）
        sot_version_dir, sot_root = VersionManager.resolve_sot_version(
            strategy_name, simulator_config.sot_version
        )
        logger.info(
            f"[PriceFactorSimulator] 使用 SOT 版本: strategy={strategy_name}, "
            f"sot_version={sot_version_dir.name}"
        )

        # 3. 创建模拟器版本目录（使用统一的版本管理）
        sim_version_dir, sim_version_id = VersionManager.create_price_factor_version(
            strategy_name
        )
        logger.info(
            f"[PriceFactorSimulator] 模拟器版本: {sim_version_dir.name} (version_id={sim_version_id})"
        )

        # 4. 创建 DataLoader 实例
        data_loader = DataLoader(strategy_name=strategy_name, cache_enabled=True)

        # 5. 扫描 SOT 目录下的机会/目标文件，按股票分组
        stock_files = self._scan_sot_files(sot_version_dir)
        if not stock_files:
            logger.warning(
                f"[PriceFactorSimulator] 在 SOT 目录中未找到任何机会文件: {sot_version_dir}"
            )
            return {}

        # 5. 根据 use_sampling 配置过滤股票列表
        from app.core.modules.data_manager import DataManager
        from app.core.modules.strategy.helper.stock_sampling_helper import (
            StockSamplingHelper,
        )

        data_mgr = DataManager(is_verbose=False)
        all_stocks_info = data_mgr.service.stock.list.load(filtered=True)
        stock_info_map = {s.get("id"): s for s in all_stocks_info}

        # 如果启用采样，使用 sampling 配置过滤股票
        if simulator_config.use_sampling:
            sampling_cfg = base_settings.sampling or {}
            sampling_strategy = sampling_cfg.get("strategy", "continuous")
            sampling_amount = int(sampling_cfg.get("sampling_amount", 20))

            # 获取采样后的股票列表
            sampled_stock_ids = StockSamplingHelper.get_stock_list(
                all_stocks=all_stocks_info,
                sampling_amount=sampling_amount,
                sampling_config=sampling_cfg,
            )
            sampled_stock_set = set(sampled_stock_ids)

            # 过滤 stock_files，只保留采样后的股票
            filtered_stock_files = {
                stock_id: paths
                for stock_id, paths in stock_files.items()
                if stock_id in sampled_stock_set
            }

            logger.info(
                f"[PriceFactorSimulator] 采样模式: "
                f"strategy={sampling_strategy}, amount={sampling_amount}, "
                f"原始={len(stock_files)} 只股票, 采样后={len(filtered_stock_files)} 只股票"
            )
            stock_files = filtered_stock_files
        else:
            logger.info(
                f"[PriceFactorSimulator] 全量模式: {len(stock_files)} 只股票"
            )

        # 6. 构建 job 列表（每只股票一个作业）
        jobs: List[Dict[str, Any]] = []
        for stock_id, paths in stock_files.items():
            jobs.append(
                {
                    "stock_id": stock_id,
                    "strategy_name": strategy_name,
                    "stock_info": stock_info_map.get(stock_id, {"id": stock_id}),
                    "sim_version_dir": str(sim_version_dir),
                    "opportunities_path": str(paths["opportunities"]),
                    "targets_path": str(paths["targets"]),
                    "config": simulator_config.__dict__,
                }
            )

        # 7. 使用多进程 Worker 执行（沿用 OpportunityEnumerator 的用法）
        from app.core.infra.worker.multi_process.process_worker import (
            ProcessWorker,
            ExecutionMode as ProcessExecutionMode,
        )
        from app.core.infra.worker.multi_process.process_worker import (  # type: ignore
            JobStatus,
        )
        from app.core.modules.strategy.components.simulator.price_factor import (
            PriceFactorSimulatorWorker,
        )

        # 解析 max_workers（支持 'auto'）
        resolved_workers = ProcessWorker.resolve_max_workers(
            simulator_config.max_workers, module_name="PriceFactorSimulator"
        )

        worker_pool = ProcessWorker(
            max_workers=resolved_workers,
            execution_mode=ProcessExecutionMode.QUEUE,
            job_executor=PriceFactorSimulatorWorker.execute_job,
            is_verbose=self.is_verbose,
        )

        # 构建 ProcessWorker 格式的 jobs
        process_jobs = [{"id": job["stock_id"], "payload": job} for job in jobs]

        logger.info(
            f"[PriceFactorSimulator] 开始模拟: strategy={strategy_name}, "
            f"stocks={len(process_jobs)}, workers={resolved_workers}"
        )

        # 执行作业（Worker 会在子进程中独立保存每个股票的 JSON）
        worker_pool.run_jobs(process_jobs)

        # 打印进度统计
        stats = worker_pool.stats
        logger.info(
            f"[PriceFactorSimulator] 执行完成: "
            f"成功={stats.get('completed_jobs', 0)}, "
            f"失败={stats.get('failed_jobs', 0)}, "
            f"耗时={stats.get('total_duration', 0):.2f}秒"
        )

        # 获取结果（用于生成 session summary）
        job_results = worker_pool.get_results()
        results: List[Dict[str, Any]] = []
        for jr in job_results:
            if jr.status == JobStatus.COMPLETED:
                results.append(jr.result or {})
            else:
                logger.warning(
                    f"[PriceFactorSimulator] 任务失败: job_id={jr.job_id}, error={jr.error}"
                )

        # 8. 汇总结果并生成 session summary
        stock_summaries: List[Dict[str, Any]] = []
        for r in results:
            if r.get("success", False):
                stock_summaries.append(r)
        
        if not stock_summaries:
            logger.warning("[PriceFactorSimulator] 没有成功的结果，无法生成 session summary")
            return {}
        
        session_summary = ResultAggregator.aggregate_results(stock_summaries)
        
        # 在 session_summary 中添加 SOT 版本依赖信息
        session_summary["sot_version"] = {
            "version_dir": sot_version_dir.name,
            "sot_root": str(sot_version_dir.parent.name),
        }
        session_summary["sim_version"] = {
            "version_id": sim_version_id,
            "version_dir": sim_version_dir.name,
        }

        # 9. 保存结果和 metadata（主进程负责）
        try:
            self._save_results(
                strategy_name=strategy_name,
                sim_version_dir=sim_version_dir,
                sim_version_id=sim_version_id,
                sot_version_dir=sot_version_dir,
                session_summary=session_summary,
                settings_snapshot=base_settings.to_dict(),
            )
        except Exception as e:
            logger.error(f"[PriceFactorSimulator] 保存结果失败: {e}")

        # 10. 展示结果
        ResultPresenter.present_results(session_summary, strategy_name)

        # 11. 同时返回内存结构
        return session_summary

    # ------------------------------------------------------------------ #
    # 配置与 SOT 解析
    # ------------------------------------------------------------------ #
    def _build_config_from_settings(self, settings) -> PriceFactorSimulatorConfig:
        """
        从通用 StrategySettings 中提取 PriceFactorSimulator 所需配置。

        配置优先级：
        - max_workers: simulator.max_workers > enumerator.max_workers > performance.max_workers > "auto"
        - use_sampling: simulator.use_sampling（默认 True）
        - sot_version: simulator.sot_version（默认 "latest"）
        """
        settings_dict = settings.to_dict()
        simulator_cfg = settings_dict.get("simulator", {}) or {}
        enumerator_cfg = settings_dict.get("enumerator", {}) or {}
        performance_cfg = settings_dict.get("performance", {}) or {}

        # SOT 版本号（枚举版本依赖）
        sot_version = simulator_cfg.get("sot_version", "latest")

        # 是否使用采样（默认 True）
        use_sampling = simulator_cfg.get("use_sampling", True)
        if not isinstance(use_sampling, bool):
            use_sampling = True  # 如果不是 bool，默认 True

        # 时间窗口
        start_date = simulator_cfg.get("start_date", "") or ""
        end_date = simulator_cfg.get("end_date", "") or ""

        # 交易成本
        fees_cfg = simulator_cfg.get("fees", {}) or {}
        commission_rate = float(fees_cfg.get("commission_rate", 0.0) or 0.0)
        min_commission = float(fees_cfg.get("min_commission", 0.0) or 0.0)
        stamp_duty_rate = float(fees_cfg.get("stamp_duty_rate", 0.0) or 0.0)
        transfer_fee_rate = float(fees_cfg.get("transfer_fee_rate", 0.0) or 0.0)

        # max_workers：只从 simulator 配置读取，如果没有则使用 "auto"
        max_workers = simulator_cfg.get("max_workers", "auto")

        return PriceFactorSimulatorConfig(
            sot_version=sot_version,
            use_sampling=use_sampling,
            start_date=start_date,
            end_date=end_date,
            commission_rate=commission_rate,
            min_commission=min_commission,
            stamp_duty_rate=stamp_duty_rate,
            transfer_fee_rate=transfer_fee_rate,
            max_workers=max_workers,
        )


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
    # 结果保存
    # ------------------------------------------------------------------ #
    def _save_results(
        self,
        strategy_name: str,
        sim_version_dir: Path,
        sim_version_id: int,
        sot_version_dir: Path,
        session_summary: Dict[str, Any],
        settings_snapshot: Dict[str, Any],
    ) -> None:
        """
        保存模拟器结果和 metadata（主进程负责）。

        注意：每个股票的 JSON 文件由 Worker 在子进程中独立保存。
        """
        # 使用统一的 ResultPathManager 管理结果目录和文件名
        path_mgr = ResultPathManager(sim_version_dir=sim_version_dir)

        # 写入会话级 summary
        session_path = path_mgr.session_summary_path()
        with session_path.open("w", encoding="utf-8") as f:
            json.dump(session_summary, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
        
        # 写入 metadata.json（包含依赖的 SOT 版本信息）
        now = datetime.now()
        metadata = {
            "strategy_name": strategy_name,
            "sim_version_id": sim_version_id,
            "sim_version_dir": sim_version_dir.name,
            "created_at": now.isoformat(),
            "sot_version": {
                "version_dir": sot_version_dir.name,
                "sot_root": str(sot_version_dir.parent),
            },
            "session_summary": session_summary,
            "settings_snapshot": settings_snapshot,
        }
        
        metadata_path = path_mgr.metadata_path()
        with metadata_path.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
        
        logger.info(f"[PriceFactorSimulator] 结果已保存: {sim_version_dir}")
        logger.info(f"[PriceFactorSimulator] - Session summary: {session_path}")
        logger.info(f"[PriceFactorSimulator] - Metadata: {metadata_path}")


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
        self.stock_info: Dict[str, Any] = job_payload.get("stock_info", {"id": self.stock_id})
        self.opportunities_path = Path(job_payload["opportunities_path"])
        self.targets_path = Path(job_payload["targets_path"])
        self.sim_version_dir = Path(job_payload["sim_version_dir"])
        self.config_dict: Dict[str, Any] = job_payload.get("config", {})
        # 钩子分发器（按策略名加载用户 StrategyWorker）
        self.hooks_dispatcher = SimulatorHooksDispatcher(self.strategy_name)

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
        """
        单股模拟主入口（当前实现为“1 股级机会回放”的基础版本）：
        - 从 opportunities CSV 读取该股所有机会
        - 按 trigger_date 排序
        - 只在“未持仓”时接纳新机会（已持有且未结束时出现的新机会将被跳过）
        - 每个被接纳的机会视作买入 1 股并持有至 exit_date，基于 ROI 计算 PnL
        """
        try:
            logger.info(f"[PriceFactorSimulatorWorker] 开始处理: {self.stock_id}")
            stock_summary = self._simulate_one_share_per_opportunity()

            # 在子进程中直接保存该股票的 JSON 文件
            self._save_stock_json(stock_summary)

            investment_count = stock_summary["summary"].get("total_investments", 0)
            logger.info(
                f"[PriceFactorSimulatorWorker] 完成: {self.stock_id}, "
                f"investments={investment_count}"
            )

            return {
                "success": True,
                "stock_id": self.stock_id,
                "stock": stock_summary["stock"],
                "investments": stock_summary["investments"],
                "summary": stock_summary["summary"],
            }
        except Exception as e:
            logger.error(
                f"[PriceFactorSimulatorWorker] 处理股票失败: stock={self.stock_id}, error={e}"
            )
            return {
                "success": False,
                "stock_id": self.stock_id,
                "stock": self.stock_info,
                "investments": [],
                "summary": {},
                "error": str(e),
            }

    # ------------------------------------------------------------------ #
    # 内部：基于 opportunities + targets 的 1 股级回放
    # ------------------------------------------------------------------ #
    def _simulate_one_share_per_opportunity(
        self,
    ) -> Dict[str, Any]:
        """
        基于 opportunities / targets 做"1 股级机会回放"：

        - 使用 targets 表中预先计算好的 weighted_profit 字段来还原整体 PnL
        - 同一只股票在任意时刻只能有一笔持仓
        - 没有资金约束：只要不与当前持仓重叠，就视为可以买 1 股
        """
        cfg = self.config_dict or {}
        start_date: str = cfg.get("start_date") or ""
        end_date: str = cfg.get("end_date") or ""

        # 1. 创建 DataLoader 并加载 opportunities 和 targets
        from app.core.modules.strategy.managers.data_loader import DataLoader
        data_loader = DataLoader(strategy_name=self.strategy_name, cache_enabled=False)
        
        # 从路径中提取 SOT 版本目录和股票 ID
        sot_version_dir = self.opportunities_path.parent
        stock_id = self.stock_id
        
        opportunities, targets_map = data_loader.load_opportunities_and_targets(
            sot_version_dir,
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date,
        )

        if not opportunities:
            stock_summary = {
                "stock": self.stock_info,
                "investments": [],
                "summary": StockSummaryBuilder._empty_summary(),
            }
            # 允许用户在“空结果”场景也做一次 after_process_stock 钩子
            modified = self.hooks_dispatcher.call_hook(
                "on_price_factor_after_process_stock",
                self.stock_id,
                stock_summary,
                cfg,
            )
            return modified or stock_summary

        # 2. 调用“单股处理前”钩子
        self.hooks_dispatcher.call_hook(
            "on_price_factor_before_process_stock",
            self.stock_id,
            opportunities,
            cfg,
        )
        
        # 3. 按 trigger_date 排序
        opportunities.sort(
            key=lambda r: (r.get("trigger_date") or "", r.get("opportunity_id") or "")
        )
        
        # 4. 模拟：同一时刻只持有一个机会（1 股），并构造 investments 列表
        investments: List[Dict[str, Any]] = []
        holding: bool = False
        current_exit_date: Optional[str] = None

        for row in opportunities:
            # 钩子：允许用户修改机会原始行
            modified_row = self.hooks_dispatcher.call_hook(
                "on_price_factor_opportunity_trigger",
                row,
                cfg,
            ) or row
            
            trigger_date = modified_row.get("trigger_date") or ""
            exit_date = modified_row.get("exit_date") or ""
            opp_id = str(modified_row.get("opportunity_id") or "").strip()

            # 若当前仍有持仓，且新机会的触发日早于当前持仓结束，则跳过
            if holding and current_exit_date is not None and trigger_date <= current_exit_date:
                continue
            
            # 接纳该机会：视为买入 1 股并持有至 exit_date
            holding = True
            current_exit_date = exit_date
            
            # 取出并通过钩子处理所有 target 行
            raw_targets = targets_map.get(opp_id) or []
            processed_targets: List[Dict[str, Any]] = []
            for t in raw_targets:
                modified_t = self.hooks_dispatcher.call_hook(
                    "on_price_factor_target_hit",
                    t,
                    modified_row,
                    cfg,
                ) or t
                processed_targets.append(modified_t)
            
            # 使用 InvestmentBuilder 构建 investment 记录
            investment = InvestmentBuilder.build_investment(modified_row, processed_targets)
            investments.append(investment)

            # 更新持仓状态
            holding = False
            current_exit_date = exit_date

        # 5. 构建 summary
        summary = StockSummaryBuilder.build_summary(investments)
        stock_summary = {
            "stock": self.stock_info,
            "investments": investments,
            "summary": summary,
        }
        
        # 6. 单股处理后钩子，允许用户调整结果
        modified_summary = self.hooks_dispatcher.call_hook(
            "on_price_factor_after_process_stock",
            self.stock_id,
            stock_summary,
            cfg,
        )
        
        return modified_summary or stock_summary

    # ------------------------------------------------------------------ #
    # 结果保存（Worker 独立保存）
    # ------------------------------------------------------------------ #
    def _save_stock_json(self, stock_summary: Dict[str, Any]) -> None:
        """
        在子进程中保存单个股票的 JSON 文件。
        
        目录结构：
            app/userspace/strategies/{strategy}/results/simulations/price_factor/{sim_version}/{stock_id}.json
        """
        # 使用 ResultPathManager 统一管理结果目录与文件名
        from app.core.modules.strategy.managers.result_path_manager import ResultPathManager

        path_mgr = ResultPathManager(sim_version_dir=self.sim_version_dir)
        stock_path = path_mgr.stock_json_path(self.stock_id)
        with stock_path.open("w", encoding="utf-8") as f:
            json.dump(stock_summary, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
        
        logger.debug(f"[PriceFactorSimulatorWorker] 已保存: {stock_path}")

