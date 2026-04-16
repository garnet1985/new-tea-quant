#!/usr/bin/env python3
"""
PriceFactorSimulator

基于枚举器输出结果的价格因子模拟器：
- 输入：opportunity_enumerator 的输出版本（opportunities/targets CSV）
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
import time
from datetime import datetime

from .helpers import DateTimeEncoder
from core.modules.strategy.managers.version_manager import VersionManager
from core.modules.strategy.managers.data_loader import DataLoader
from core.modules.strategy.managers.result_path_manager import ResultPathManager
from core.modules.strategy.components.simulator.base.simulator_hooks_dispatcher import (
    SimulatorHooksDispatcher,
)
from core.modules.strategy.components.opportunity_enumerator.performance_profiler import (
    AggregateProfiler,
    PerformanceMetrics,
    PerformanceProfiler,
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

    说明：
    - 采样的语义统一下沉到枚举器层（opportunity_enumerator），
      本层不再根据 use_sampling 做二次抽样，只是读取指定的枚举输出版本。
    - base_version 用于指定版本号；use_sampling 决定读取 test/ 或 output/。
    """

    # base_version：依赖的枚举版本号（如 "latest" / "1"）
    # 实际从 test 还是 output 读取，由 use_sampling 决定。
    base_version: str = "latest"
    # 是否使用采样枚举结果（True: test/*；False: output/*）
    use_sampling: bool = True

    # 时间窗口（可选），为空表示使用输出版本全量时间
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
    - 解析并选择枚举器输出版本目录（support: 具体版本号 / latest）
    - 扫描输出版本目录下的 opportunities/targets CSV
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
        from core.modules.strategy.models.strategy_settings import StrategySettings

        # 为避免触发所有策略的全局校验，这里不通过 StrategyManager，
        # 而是直接按模块路径加载指定策略的 settings.py
        import importlib

        settings_module_path = f"userspace.strategies.{strategy_name}.settings"
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

        # 2. 解析枚举器输出版本目录（依赖的枚举版本）
        base_version = getattr(simulator_config, "base_version", "latest")
        use_sampling = bool(getattr(simulator_config, "use_sampling", True))
        logger.info(
            "[PriceFactorSimulator] 版本选择规则: use_sampling=%s -> source=%s, "
            "base_version=%s, missing_version=>latest, empty_source=>auto_enumerate",
            use_sampling,
            "test" if use_sampling else "output",
            base_version,
        )
        output_version_dir, output_root = self._resolve_or_build_enum_version(
            strategy_name=strategy_name,
            base_settings=base_settings,
            use_sampling=use_sampling,
            base_version=base_version,
        )
        logger.info(
            f"[PriceFactorSimulator] 使用枚举器输出版本: strategy={strategy_name}, "
            f"output_version={output_version_dir.name}, "
            f"source={output_root.name}"
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

        # 5. 扫描输出版本目录下的机会/目标文件，按股票分组
        stock_files = self._scan_output_files(output_version_dir)
        if not stock_files:
            logger.warning(
                f"[PriceFactorSimulator] 在输出版本目录中未找到任何机会文件: {output_version_dir}"
            )
            return {}

        # 5. 根据枚举输出决定股票集合：
        # - 如果枚举是全量（output/*），这里就全量跑这些股票；
        # - 如果枚举是采样版本（test/*），这里就只跑采样产出的那部分股票。
        from core.modules.data_manager import DataManager

        data_mgr = DataManager(is_verbose=False)
        all_stocks_info = data_mgr.service.stock.list.load(filtered=True)
        stock_info_map = {s.get("id"): s for s in all_stocks_info}

        logger.info(
            f"[PriceFactorSimulator] 使用枚举输出股票集合: {len(stock_files)} 只 "
            f"(由枚举器输出版本 {output_version_dir.name} 决定)"
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
        from core.infra.worker.multi_process.process_worker import (
            ProcessWorker,
            ExecutionMode as ProcessExecutionMode,
        )
        from core.infra.worker.multi_process.process_worker import (  # type: ignore
            JobStatus,
        )
        from core.modules.strategy.components.simulator.price_factor import (
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

        # 记录开始时间
        start_time = time.time()
        # 初始化性能聚合器
        aggregate_profiler = AggregateProfiler()
        
        logger.info(
            f"🚀 [PriceFactorSimulator] 开始模拟: strategy={strategy_name}, "
            f"stocks={len(process_jobs)}, workers={resolved_workers}"
        )

        # 执行作业（Worker 会在子进程中独立保存每个股票的 JSON）
        worker_pool.run_jobs(process_jobs)

        # 计算总时长
        total_elapsed = time.time() - start_time
        if total_elapsed < 60:
            total_time_str = f"{total_elapsed:.1f}秒"
        elif total_elapsed < 3600:
            total_time_str = f"{total_elapsed/60:.1f}分钟"
        else:
            hours = int(total_elapsed // 3600)
            minutes = int((total_elapsed % 3600) // 60)
            total_time_str = f"{hours}小时{minutes}分钟"
        
        # 打印进度统计
        stats = worker_pool.stats
        logger.info(
            f"✅ [PriceFactorSimulator] 执行完成: "
            f"成功={stats.get('completed_jobs', 0)}, "
            f"失败={stats.get('failed_jobs', 0)}, "
            f"总耗时={total_time_str}"
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
                # 聚合性能指标（如果 Worker 返回了 performance_metrics）
                perf_data = r.get("performance_metrics")
                stock_id = r.get("stock_id")
                if perf_data and stock_id:
                    metrics = PerformanceMetrics()
                    time_data = perf_data.get("time", {}) or {}
                    io_data = perf_data.get("io", {}) or {}
                    data_stats = perf_data.get("data", {}) or {}
                    mem_stats = perf_data.get("memory", {}) or {}

                    metrics.time_load_data = time_data.get("load_data", 0.0)
                    metrics.time_calculate_indicators = time_data.get("calculate_indicators", 0.0)
                    metrics.time_enumerate = time_data.get("enumerate", 0.0)
                    metrics.time_serialize = time_data.get("serialize", 0.0)
                    metrics.time_save_csv = time_data.get("save_csv", 0.0)
                    metrics.time_total = time_data.get("total", 0.0)

                    metrics.db_queries = io_data.get("db_queries", 0)
                    metrics.db_query_time = io_data.get("db_query_time", 0.0)
                    metrics.file_writes = io_data.get("file_writes", 0)
                    metrics.file_write_time = io_data.get("file_write_time", 0.0)
                    # file_write_size_mb 在 to_dict 中是 MB，这里按字节还原时允许为空
                    file_size_mb = io_data.get("file_write_size_mb", 0.0)
                    try:
                        metrics.file_write_size = int(file_size_mb * 1024 * 1024)
                    except Exception:
                        metrics.file_write_size = 0

                    metrics.kline_count = data_stats.get("kline_count", 0)
                    metrics.opportunity_count = data_stats.get("opportunity_count", 0)
                    metrics.target_count = data_stats.get("target_count", 0)

                    metrics.memory_peak = mem_stats.get("peak_mb", 0.0)
                    metrics.memory_start = mem_stats.get("start_mb", 0.0)
                    metrics.memory_end = mem_stats.get("end_mb", 0.0)

                    aggregate_profiler.add_stock_metrics(str(stock_id), metrics)
        
        if not stock_summaries:
            logger.warning("[PriceFactorSimulator] 没有成功的结果，无法生成 session summary")
            return {}
        
        session_summary = ResultAggregator.aggregate_results(stock_summaries)
        
        # 在 session_summary 中添加枚举器输出版本依赖信息
        session_summary["output_version"] = {
            "version_dir": output_version_dir.name,
            "output_root": str(output_version_dir.parent.name),
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
                output_version_dir=output_version_dir,
                session_summary=session_summary,
                settings_snapshot=base_settings.to_dict(),
            )
        except Exception as e:
            logger.error(f"[PriceFactorSimulator] 保存结果失败: {e}")

        # 10. 展示结果
        ResultPresenter.present_results(session_summary, strategy_name)

        # 11. 保存性能报告（如果有性能数据）
        try:
            perf_summary = aggregate_profiler.get_summary()
            if perf_summary:
                perf_file = sim_version_dir / "0_performance_report.json"
                with perf_file.open("w", encoding="utf-8") as f:
                    json.dump(perf_summary, f, indent=2, ensure_ascii=False)
                logger.info(f"[PriceFactorSimulator] 性能报告已保存: {perf_file}")
        except Exception as exc:
            logger.warning(
                "[PriceFactorSimulator] 保存性能报告失败（不影响主流程）: %s", exc
            )

        # 12. 运行 Analyzer（如果启用）
        try:
            from core.modules.strategy.components.analyzer import Analyzer

            Analyzer.run_for_simulator(
                strategy_name=strategy_name,
                sim_type="price_factor",
                sim_version_dir=sim_version_dir,
                raw_settings=base_settings.to_dict(),
            )
        except Exception as exc:
            logger.warning(
                "[PriceFactorSimulator] Analyzer 执行失败（不影响主流程）: %s", exc
            )

        # 13. 同时返回内存结构
        return session_summary

    # ------------------------------------------------------------------ #
    # 配置与输出版本解析
    # ------------------------------------------------------------------ #
    def _build_config_from_settings(self, settings) -> PriceFactorSimulatorConfig:
        """
        从通用 StrategySettings 中提取 PriceFactorSimulator 所需配置。

        配置优先级：
        - max_workers: price_simulator.max_workers > enumerator.max_workers > performance.max_workers > "auto"
        - base_version: price_simulator.base_version（默认 "latest"）
        """
        settings_dict = settings.to_dict()
        simulator_cfg = settings_dict.get("price_simulator", {}) or {}
        enumerator_cfg = settings_dict.get("enumerator", {}) or {}
        performance_cfg = settings_dict.get("performance", {}) or {}

        # base_version（枚举器输出版本依赖）
        base_version = simulator_cfg.get("base_version") or "latest"
        use_sampling = bool(simulator_cfg.get("use_sampling", True))

        # 时间窗口
        start_date = simulator_cfg.get("start_date", "") or ""
        end_date = simulator_cfg.get("end_date", "") or ""

        # 交易成本
        fees_cfg = simulator_cfg.get("fees", {}) or {}
        commission_rate = float(fees_cfg.get("commission_rate", 0.0) or 0.0)
        min_commission = float(fees_cfg.get("min_commission", 0.0) or 0.0)
        stamp_duty_rate = float(fees_cfg.get("stamp_duty_rate", 0.0) or 0.0)
        transfer_fee_rate = float(fees_cfg.get("transfer_fee_rate", 0.0) or 0.0)

        # max_workers：只从 price_simulator 配置读取，如果没有则使用 "auto"
        max_workers = simulator_cfg.get("max_workers", "auto")

        return PriceFactorSimulatorConfig(
            base_version=base_version,
            use_sampling=use_sampling,
            start_date=start_date,
            end_date=end_date,
            commission_rate=commission_rate,
            min_commission=min_commission,
            stamp_duty_rate=stamp_duty_rate,
            transfer_fee_rate=transfer_fee_rate,
            max_workers=max_workers,
        )

    def _resolve_or_build_enum_version(
        self,
        strategy_name: str,
        base_settings,
        use_sampling: bool,
        base_version: str,
    ) -> tuple[Path, Path]:
        """
        解析当前模拟依赖的枚举版本。

        规则：
        - use_sampling=True: 从 test/ 读取
        - use_sampling=False: 从 output/ 读取
        - base_version 为空或找不到 -> 回退同目录 latest
        - 如果该目录没有任何版本 -> 按对应模式先触发一次枚举，再取 latest
        """
        sub_dir = "test" if use_sampling else "output"
        raw_version = (base_version or "latest").strip()
        if "/" in raw_version:
            raw_version = raw_version.split("/", 1)[1].strip() or "latest"

        version_spec = f"{sub_dir}/{raw_version}"
        try:
            version_dir, root = VersionManager.resolve_output_version(
                strategy_name, version_spec
            )
            return version_dir, root
        except FileNotFoundError:
            if raw_version != "latest":
                logger.warning(
                    "[PriceFactorSimulator] 指定版本不存在: %s，回退到 %s/latest",
                    version_spec,
                    sub_dir,
                )
                try:
                    return VersionManager.resolve_output_version(
                        strategy_name, f"{sub_dir}/latest"
                    )
                except FileNotFoundError:
                    pass

        logger.info(
            "[PriceFactorSimulator] %s 目录无可用版本，先自动触发一次枚举",
            sub_dir,
        )
        self._run_enumerator_for_mode(
            strategy_name=strategy_name,
            base_settings=base_settings,
            use_sampling=use_sampling,
        )
        return VersionManager.resolve_output_version(strategy_name, f"{sub_dir}/latest")

    def _run_enumerator_for_mode(
        self,
        strategy_name: str,
        base_settings,
        use_sampling: bool,
    ) -> None:
        """按模式触发一次枚举：sampling=True 触发 test，False 触发 output。"""
        from core.modules.data_manager import DataManager
        from core.modules.strategy.components.opportunity_enumerator import OpportunityEnumerator
        from core.modules.strategy.helpers.stock_sampling_helper import StockSamplingHelper
        from core.utils.date.date_utils import DateUtils

        data_mgr = DataManager(is_verbose=False)
        all_stocks = data_mgr.service.stock.list.load(filtered=True)
        if use_sampling:
            stock_list = StockSamplingHelper.get_stock_list(
                all_stocks=all_stocks,
                sampling_amount=base_settings.sampling_amount or len(all_stocks),
                sampling_config=base_settings.sampling_config or {},
                strategy_name=strategy_name,
            )
        else:
            stock_list = [s["id"] for s in all_stocks]
        end_date = data_mgr.service.calendar.get_latest_completed_trading_date()
        start_date = DateUtils.DEFAULT_START_DATE

        logger.info(
            "[PriceFactorSimulator] 自动触发枚举开始: mode=%s, stocks=%d, period=%s~%s",
            "test" if use_sampling else "output",
            len(stock_list),
            start_date,
            end_date,
        )
        OpportunityEnumerator.enumerate(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            stock_list=stock_list,
            max_workers="auto",
        )
        logger.info("[PriceFactorSimulator] 自动触发枚举完成")


    def _scan_output_files(self, version_dir: Path) -> Dict[str, Dict[str, Path]]:
        """
        扫描指定输出版本目录下的 opportunities/targets 文件，按股票进行分组。

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
        output_version_dir: Path,
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
        
        # 写入 metadata.json（包含依赖的枚举器输出版本信息）
        now = datetime.now()
        metadata = {
            "strategy_name": strategy_name,
            "sim_version_id": sim_version_id,
            "sim_version_dir": sim_version_dir.name,
            "created_at": now.isoformat(),
            "output_version": {
                "version_dir": output_version_dir.name,
                "output_root": str(output_version_dir.parent.name),
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
        # 性能分析器（单股级）
        self.profiler = PerformanceProfiler(self.stock_id)

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
        # 记录总耗时
        self.profiler.start_timer("total")
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

            # 填充总耗时并最终生成性能指标
            self.profiler.metrics.time_total = self.profiler.end_timer("total")
            metrics = self.profiler.finalize()

            return {
                "success": True,
                "stock_id": self.stock_id,
                "stock": stock_summary["stock"],
                "investments": stock_summary["investments"],
                "summary": stock_summary["summary"],
                "performance_metrics": metrics.to_dict(),
            }
        except Exception as e:
            logger.error(
                f"[PriceFactorSimulatorWorker] 处理股票失败: stock={self.stock_id}, error={e}"
            )
            # 异常场景也尽量返回性能指标，便于观察
            try:
                self.profiler.metrics.time_total = self.profiler.end_timer("total")
                metrics = self.profiler.finalize()
                perf_dict = metrics.to_dict()
            except Exception:
                perf_dict = {}
            return {
                "success": False,
                "stock_id": self.stock_id,
                "stock": self.stock_info,
                "investments": [],
                "summary": {},
                "error": str(e),
                "performance_metrics": perf_dict,
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

        # 1. 创建 DataLoader 并加载 opportunities 和 targets（行式 dict）
        self.profiler.start_timer("load_data")
        from core.modules.strategy.managers.data_loader import DataLoader
        data_loader = DataLoader(strategy_name=self.strategy_name, cache_enabled=False)

        opportunities_rows, targets_rows, targets_index = data_loader.load_rows_for_stock(
            opportunities_path=self.opportunities_path,
            targets_path=self.targets_path,
            start_date=start_date,
            end_date=end_date,
        )
        # 记录加载耗时与数据规模
        load_elapsed = self.profiler.end_timer("load_data")
        self.profiler.metrics.time_load_data = load_elapsed
        self.profiler.metrics.kline_count = 0  # 价格模拟阶段不直接处理 K 线
        self.profiler.metrics.opportunity_count = len(opportunities_rows)
        self.profiler.metrics.target_count = len(targets_rows)

        if not opportunities_rows:
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

        # 2. 调用“单股处理前”钩子（传入机会行列表）
        self.hooks_dispatcher.call_hook(
            "on_price_factor_before_process_stock",
            self.stock_id,
            opportunities_rows,
            cfg,
        )
        
        # 3. 按 trigger_date 排序
        self.profiler.start_timer("enumerate")
        order = sorted(
            range(len(opportunities_rows)),
            key=lambda i: (
                opportunities_rows[i].get("trigger_date") or "",
                str(opportunities_rows[i].get("opportunity_id") or ""),
            ),
        )
        
        # 4. 模拟：同一时刻只持有一个机会（1 股），并构造 investments 列表
        investments: List[Dict[str, Any]] = []
        # 使用 holding_until 记录当前持仓的结束日期（含）；为 None 表示当前无持仓
        holding_until: Optional[str] = None

        for idx in order:
            row = opportunities_rows[idx]
            # 钩子：允许用户修改机会原始行
            modified_row = self.hooks_dispatcher.call_hook(
                "on_price_factor_opportunity_trigger",
                row,
                cfg,
            ) or row
            
            trigger_date = modified_row.get("trigger_date") or ""
            # 优先使用枚举输出中的 sell_date 作为退出日；如无则回退到 exit_date 或当日
            sell_date = modified_row.get("sell_date") or ""
            exit_date = sell_date or modified_row.get("exit_date") or trigger_date
            opp_id = str(modified_row.get("opportunity_id") or "").strip()

            # 若当前仍有持仓，且新机会的触发日早于或等于当前持仓结束日，则跳过
            # 这样保证同一只股票在任意时刻至多只有一笔持仓
            if holding_until is not None and trigger_date <= holding_until:
                continue
            
            # 接纳该机会：视为买入 1 股并持有至 exit_date（若无 exit_date，则视为当日平仓）
            holding_until = exit_date or trigger_date
            
            # 取出并通过钩子处理所有 target 行
            raw_target_indices = targets_index.get(opp_id) or []
            processed_targets: List[Dict[str, Any]] = []
            for t_idx in raw_target_indices:
                if t_idx < 0 or t_idx >= len(targets_rows):
                    continue
                t_row = targets_rows[t_idx]
                modified_t = self.hooks_dispatcher.call_hook(
                    "on_price_factor_target_hit",
                    t_row,
                    modified_row,
                    cfg,
                ) or t_row
                processed_targets.append(dict(modified_t))  # type: ignore[arg-type]
            
            # 使用 InvestmentBuilder 构建 investment 记录
            investment = InvestmentBuilder.build_investment(
                dict(modified_row),  # type: ignore[arg-type]
                processed_targets,
            )
            investments.append(investment)

        # 结束枚举计时
        enum_elapsed = self.profiler.end_timer("enumerate")
        self.profiler.metrics.time_enumerate = enum_elapsed

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
        在子进程中保存单个股票的结果。

        - 保留 JSON 版本（结构化、供内部工具使用）
        - 额外导出投资列表为 CSV，便于人工查看与 Excel 加载

        目录结构：
            userspace/strategies/{strategy}/results/simulations/price_factor/{sim_version}/{stock_id}.json
            userspace/strategies/{strategy}/results/simulations/price_factor/{sim_version}/{stock_id}.csv
        """
        # 使用 ResultPathManager 统一管理结果目录与文件名
        from core.modules.strategy.managers.result_path_manager import ResultPathManager
        from core.utils.io.csv_io import write_dicts_to_csv

        path_mgr = ResultPathManager(sim_version_dir=self.sim_version_dir)
        stock_path = path_mgr.stock_json_path(self.stock_id)

        # 1) 保存 JSON（完整结构）
        self.profiler.start_timer("save_csv")
        before = stock_path.stat().st_size if stock_path.exists() else 0
        with stock_path.open("w", encoding="utf-8") as f:
            json.dump(stock_summary, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
        after = stock_path.stat().st_size if stock_path.exists() else 0
        elapsed = self.profiler.end_timer("save_csv")

        size_bytes = max(0, after - before)
        self.profiler.metrics.time_save_csv += elapsed
        try:
            self.profiler.record_file_write(size_bytes=size_bytes, duration=elapsed)
        except TypeError:
            self.profiler.record_file_write(size_bytes, elapsed)

        # 2) 额外导出 investments 为 CSV（扁平化主要字段）
        investments = stock_summary.get("investments") or []
        if investments:
            csv_path = stock_path.with_suffix(".csv")
            # 选择一组常用字段，保证列顺序稳定，其余字段按名称追加
            preferred = [
                "stock_id",
                "result",
                "start_date",
                "end_date",
                "purchase_price",
                "duration_in_days",
                "overall_profit",
                "roi",
                "overall_annual_return",
            ]
            # 确保每条记录都有 stock_id 字段
            normalized_investments = []
            for inv in investments:
                if inv.get("stock_id") is None:
                    inv = dict(inv)
                    inv["stock_id"] = self.stock_id
                normalized_investments.append(inv)

            write_dicts_to_csv(csv_path, normalized_investments, preferred_order=preferred)

        logger.debug(f"[PriceFactorSimulatorWorker] 已保存: {stock_path}")

