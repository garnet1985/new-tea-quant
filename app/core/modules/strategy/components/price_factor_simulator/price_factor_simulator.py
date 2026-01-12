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
from datetime import datetime

from .helpers import parse_yyyymmdd, to_ratio, to_percent, get_annual_return
from app.core.utils.icon.icon_service import IconService

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """自定义 JSON 编码器，处理 datetime 对象和其他不可序列化的类型"""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, (int, float)):
            # 处理 numpy 类型（如果存在）
            return float(obj) if isinstance(obj, float) else int(obj)
        elif hasattr(obj, '__dict__'):
            # 处理其他对象，尝试转换为字典
            return obj.__dict__
        return super().default(obj)


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
        sot_root, sot_version_dir = self._resolve_sot_version_dir(strategy_name, simulator_config.sot_version)
        logger.info(
            f"[PriceFactorSimulator] 使用 SOT 版本: strategy={strategy_name}, "
            f"sot_version={sot_version_dir.name}"
        )

        # 3. 创建模拟器版本目录（使用自己的版本管理）
        sim_version_dir, sim_version_id = self._create_simulation_version_dir(strategy_name)
        logger.info(
            f"[PriceFactorSimulator] 模拟器版本: {sim_version_dir.name} (version_id={sim_version_id})"
        )

        # 4. 扫描 SOT 目录下的机会/目标文件，按股票分组
        stock_files = self._scan_sot_files(sot_version_dir)
        if not stock_files:
            logger.warning(f"[PriceFactorSimulator] 在 SOT 目录中未找到任何机会文件: {sot_version_dir}")
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
        from app.core.infra.worker.multi_process.process_worker import JobStatus  # type: ignore
        from app.core.modules.strategy.components.price_factor_simulator import (
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
        
        session_summary = self._aggregate_results(stock_summaries)
        
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
        self._present_results(session_summary, strategy_name)

        # 11. 同时返回内存结构
        return session_summary

    # ------------------------------------------------------------------ #
    # 结果展示
    # ------------------------------------------------------------------ #
    def _present_results(self, session_summary: Dict[str, Any], strategy_name: str) -> None:
        """
        展示 PriceFactorSimulator 的结果（类似 legacy 的展示方式）
        
        Args:
            session_summary: 会话汇总结果
            strategy_name: 策略名称
        """
        if not session_summary:
            logger.warning("[PriceFactorSimulator] 没有结果可展示")
            return

        print("\n" + "="*60)
        print(f"📊 {strategy_name} 策略价格因子回测结果")
        print("="*60)

        win_rate = session_summary.get('win_rate', 0)
        annual_return = session_summary.get('annual_return', 0)
        annual_return_in_trading_days = session_summary.get('annual_return_in_trading_days', 0)
        avg_roi = session_summary.get('avg_roi', 0) * 100.0  # 转换为百分比

        # 胜率
        if win_rate >= 50:
            win_rate_dot = IconService.get('green_dot')
        else:
            win_rate_dot = IconService.get('red_dot')
        print(f"{win_rate_dot} 胜率: {win_rate:.1f}%")

        # 平均 ROI
        if avg_roi >= 5:
            avg_roi_dot = IconService.get('green_dot')
        else:
            avg_roi_dot = IconService.get('red_dot')
        print(f"{avg_roi_dot} 平均每笔投资回报率(ROI): {avg_roi:.2f}%")

        # 年化收益率
        if annual_return >= 0.15:
            annual_return_dot = IconService.get('green_dot')
        else:
            annual_return_dot = IconService.get('red_dot')

        if annual_return_in_trading_days >= 0.1:
            annual_return_in_trading_days_dot = IconService.get('green_dot')
        else:
            annual_return_in_trading_days_dot = IconService.get('red_dot')

        print(f"折算后平均每笔投资年化收益率: ")
        print(f" - {annual_return_dot} 按自然日: {annual_return * 100:.2f}%")
        print(f" - {annual_return_in_trading_days_dot} 按交易日: {annual_return_in_trading_days * 100:.2f}%")

        # 其他统计信息
        print(f"{IconService.get('clock')} 平均投资时长: {session_summary.get('avg_duration_in_days', 0):.1f} 自然日")
        print(f"{IconService.get('bar_chart')} 总投资次数: {session_summary.get('total_investments', 0)}")
        print(f"{IconService.get('success')} 成功次数: {session_summary.get('total_win_investments', 0)}")
        print(f"{IconService.get('error')} 失败次数: {session_summary.get('total_loss_investments', 0)}")
        print(f"{IconService.get('ongoing')} 未完成次数: {session_summary.get('total_open_investments', 0)}")
        
        # 总盈利
        total_profit = session_summary.get('total_profit', 0.0)
        if total_profit >= 0:
            profit_icon = IconService.get('green_dot')
        else:
            profit_icon = IconService.get('red_dot')
        print(f"{profit_icon} 总盈利: {total_profit:.2f}")
        
        # 产生机会的股票数
        stocks_with_opportunities = session_summary.get('stocks_have_opportunities', 0)
        print(f"{IconService.get('money')} 产生机会的股票数: {stocks_with_opportunities}")
        
        print("")

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

        # max_workers 优先级：simulator > enumerator > performance > "auto"
        # TODO: max workers should not fetch from other different components, they work differently
        max_workers = (
            simulator_cfg.get("max_workers")
            or enumerator_cfg.get("max_workers")
            or performance_cfg.get("max_workers")
            or "auto"
        )

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

    def _create_simulation_version_dir(self, strategy_name: str) -> Tuple[Path, int]:
        """
        创建模拟器版本目录（使用自己的版本管理，类似枚举器）。
        
        目录结构：
            app/userspace/strategies/{strategy}/results/simulations/price_factor/
                meta.json  # 版本管理元信息
                {version_id}_{YYYYMMDD_HHMMSS}/  # 模拟器版本目录
        
        Returns:
            (version_dir, version_id): 版本目录路径和版本ID
        """
        root_dir = (
            Path("app")
            / "userspace"
            / "strategies"
            / strategy_name
            / "results"
            / "simulations"
            / "price_factor"
        )
        root_dir.mkdir(parents=True, exist_ok=True)

        # 读取或创建 meta.json
        meta_path = root_dir / "meta.json"
        if meta_path.exists():
            try:
                with meta_path.open("r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception:
                meta = {}
        else:
            meta = {}

        next_version_id = int(meta.get("next_version_id", 1))
        now = datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        version_dir_name = f"{next_version_id}_{timestamp_str}"
        version_dir = root_dir / version_dir_name
        version_dir.mkdir(parents=True, exist_ok=True)

        # 立刻更新 meta.json（版本管理），不依赖后续流程是否成功
        new_meta = {
            "next_version_id": next_version_id + 1,
            "last_updated": now.isoformat(),
            "strategy_name": strategy_name,
        }
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(new_meta, f, indent=2, ensure_ascii=False)

        return version_dir, next_version_id

    def _resolve_sot_version_dir(self, strategy_name: str, sot_version: str) -> Tuple[Path, Path]:
        """
        解析枚举版本目录：
        
        支持的格式：
        - "latest": 使用最新的 SOT 版本（sot/ 目录）
        - "test/latest": 使用最新的测试版本（test/ 目录）
        - "sot/latest": 使用最新的 SOT 版本（sot/ 目录）
        - "1_20260112_161317": 使用指定版本号（默认在 sot/ 目录查找）
        - "test/1_20260112_161317": 使用指定测试版本号（test/ 目录）
        - "sot/1_20260112_161317": 使用指定 SOT 版本号（sot/ 目录）
        """
        base_root = (
            Path("app")
            / "userspace"
            / "strategies"
            / strategy_name
            / "results"
            / "opportunity_enums"
        )

        # 解析目录类型和版本号
        if "/" in sot_version:
            # 格式：test/latest 或 sot/latest 或 test/1_xxx 或 sot/1_xxx
            parts = sot_version.split("/", 1)
            sub_dir_name = parts[0]  # test 或 sot
            version_str = parts[1]  # latest 或具体版本号
        else:
            # 格式：latest 或 1_xxx（默认使用 sot 目录）
            sub_dir_name = "sot"
            version_str = sot_version

        root = base_root / sub_dir_name
        if not root.exists():
            raise FileNotFoundError(
                f"[PriceFactorSimulator] 枚举目录不存在: {root} (sot_version={sot_version})"
            )

        if version_str == "latest":
            # 查找最新的版本目录
            candidates = [p for p in root.iterdir() if p.is_dir() and "_" in p.name]
            if not candidates:
                raise FileNotFoundError(
                    f"[PriceFactorSimulator] {sub_dir_name} 目录下没有任何版本: {root}"
                )
            # 版本名形如: {version_id}_{YYYYMMDD_HHMMSS}，直接按 name 排序即可
            version_dir = sorted(candidates, key=lambda p: p.name)[-1]
            logger.info(
                f"[PriceFactorSimulator] 使用最新版本: {sub_dir_name}/{version_dir.name}"
            )
            return root, version_dir

        # 使用指定版本号
        version_dir = root / version_str
        if not version_dir.exists() or not version_dir.is_dir():
            raise FileNotFoundError(
                f"[PriceFactorSimulator] 指定版本目录不存在: {version_dir} (sot_version={sot_version})"
            )
        logger.info(
            f"[PriceFactorSimulator] 使用指定版本: {sub_dir_name}/{version_str}"
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
    def _aggregate_results(self, stock_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        将各 Worker 的结果聚合为一个策略级 summary。

        复用 legacy 的 summarize_session_by_default_way 思路：
        - 按单股 summary 的 avg_roi 和 avg_duration 做加权
        - 得到会话级 avg_roi / avg_duration，再推导 annual_return 系列
        """
        if not stock_summaries:
            return {}

        total_investments = 0
        total_win = 0
        total_loss = 0
        total_open = 0
        total_profit = 0.0
        total_roi = 0.0
        total_duration_days = 0.0

        stocks_with_opportunities = len(stock_summaries)

        for stock_summary in stock_summaries:
            summary = stock_summary.get("summary", {})
            investment_count = summary.get("total_investments", 0)

            if investment_count > 0:
                total_investments += investment_count
                total_win += summary.get("total_win", 0)
                total_loss += summary.get("total_loss", 0)
                total_open += summary.get("total_open", 0)
                total_profit += summary.get("total_profit", 0.0)

                stock_avg_roi = summary.get("avg_roi", 0.0)
                total_roi += stock_avg_roi * investment_count
                total_duration_days += summary.get("avg_duration_in_days", 0.0) * investment_count

        # 计算整体平均值
        avg_roi = to_ratio(total_roi, total_investments, decimals=4)
        avg_duration_days = to_ratio(total_duration_days, total_investments)

        annual_return_raw = get_annual_return(avg_roi, avg_duration_days)
        annual_return = (
            float(annual_return_raw.real)
            if isinstance(annual_return_raw, complex)
            else float(annual_return_raw)
            if isinstance(annual_return_raw, (int, float))
            else 0.0
        )
        annual_return_in_trading_days_raw = get_annual_return(
            avg_roi, avg_duration_days, is_trading_days=True
        )
        annual_return_in_trading_days = (
            float(annual_return_in_trading_days_raw.real)
            if isinstance(annual_return_in_trading_days_raw, complex)
            else float(annual_return_in_trading_days_raw)
            if isinstance(annual_return_in_trading_days_raw, (int, float))
            else 0.0
        )

        win_rate = to_percent(total_win, total_investments)

        session_summary: Dict[str, Any] = {
            "win_rate": win_rate,
            "avg_roi": avg_roi,
            "annual_return": annual_return,
            "annual_return_in_trading_days": annual_return_in_trading_days,
            "avg_duration_in_days": avg_duration_days,
            "total_investments": total_investments,
            "total_open_investments": total_open,
            "total_win_investments": total_win,
            "total_loss_investments": total_loss,
            "total_profit": round(total_profit, 2),
            "stocks_have_opportunities": stocks_with_opportunities,
        }

        return session_summary

    # ------------------------------------------------------------------ #
    # 结果落盘
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
        # 写入会话级 summary
        session_path = sim_version_dir / "0_session_summary.json"
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
        
        metadata_path = sim_version_dir / "metadata.json"
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
        基于 opportunities / targets 做“1 股级机会回放”：

        - 使用 targets 表中预先计算好的 weighted_profit 字段来还原整体 PnL
          （sum(weighted_profit) 即视为持有 1 股的总盈利）
        - 若某机会没有 targets 记录，则回退为: pnl = trigger_price * roi
        - 同一只股票在任意时刻只能有一笔持仓：
          - 若已有持仓未结束，新机会的 trigger_date 落在持仓区间内，则跳过该机会
        - 没有资金约束：只要不与当前持仓重叠，就视为可以买 1 股
        """
        opp_path = self.opportunities_path
        if not opp_path.exists():
            logger.warning(
                f"[PriceFactorSimulatorWorker] opportunities 文件不存在: {opp_path}"
            )
            return {
                "stock": self.stock_info,
                "investments": [],
                "summary": {
                    "total_investments": 0,
                    "total_win": 0,
                    "total_loss": 0,
                    "total_open": 0,
                    "profitable": 0,
                    "minor_profitable": 0,
                    "unprofitable": 0,
                    "minor_unprofitable": 0,
                    "win_rate": 0.0,
                    "total_profit": 0.0,
                    "avg_profit": 0.0,
                    "avg_duration_in_days": 0.0,
                    "avg_roi": 0.0,
                    "annual_return": 0.0,
                    "annual_return_in_trading_days": 0.0,
                },
            }

        cfg = self.config_dict or {}
        start_date: str = cfg.get("start_date") or ""
        end_date: str = cfg.get("end_date") or ""

        # 1. 读取 targets，按 opportunity_id 分组
        targets_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        if self.targets_path.exists():
            with self.targets_path.open("r", encoding="utf-8") as f_t:
                t_reader = csv.DictReader(f_t)
                for row in t_reader:
                    opp_id = str(row.get("opportunity_id") or "").strip()
                    if not opp_id:
                        continue
                    # 规范化数值字段
                    try:
                        row["weighted_profit"] = float(row.get("weighted_profit") or 0.0)
                    except ValueError:
                        row["weighted_profit"] = 0.0
                    targets_map[opp_id].append(row)

        # 2. 读取所有机会
        opportunities: List[Dict[str, Any]] = []
        with opp_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trigger_date = row.get("trigger_date") or ""
                exit_date = row.get("exit_date") or ""

                # 时间窗口过滤（基于字符串比较，YYYYMMDD 形式）
                if start_date and trigger_date < start_date:
                    continue
                if end_date and trigger_date > end_date:
                    continue

                opportunities.append(row)

        total_count = len(opportunities)
        if total_count == 0:
            return {
                "stock": self.stock_info,
                "investments": [],
                "summary": {
                    "total_investments": 0,
                    "total_win": 0,
                    "total_loss": 0,
                    "total_open": 0,
                    "profitable": 0,
                    "minor_profitable": 0,
                    "unprofitable": 0,
                    "minor_unprofitable": 0,
                    "win_rate": 0.0,
                    "total_profit": 0.0,
                    "avg_profit": 0.0,
                    "avg_duration_in_days": 0.0,
                    "avg_roi": 0.0,
                    "annual_return": 0.0,
                    "annual_return_in_trading_days": 0.0,
                },
            }

        # 3. 按 trigger_date 排序
        opportunities.sort(key=lambda r: (r.get("trigger_date") or "", r.get("opportunity_id") or ""))

        # 4. 模拟：同一时刻只持有一个机会（1 股），并构造 investments 列表
        investments: List[Dict[str, Any]] = []

        total_investments = 0
        total_win = 0
        total_loss = 0
        total_open = 0

        total_profit = 0.0
        total_duration = 0.0
        total_roi = 0.0

        profitable_count = 0
        minor_profitable_count = 0
        unprofitable_count = 0
        minor_unprofitable_count = 0

        holding: bool = False
        current_exit_date: Optional[str] = None

        for row in opportunities:
            trigger_date = row.get("trigger_date") or ""
            exit_date = row.get("exit_date") or ""
            opp_id = str(row.get("opportunity_id") or "").strip()

            # 若当前仍有持仓，且新机会的触发日早于当前持仓结束，则跳过
            if holding and current_exit_date is not None and trigger_date <= current_exit_date:
                continue

            # 接纳该机会：视为买入 1 股并持有至 exit_date
            holding = True
            current_exit_date = exit_date

            # 解析基础字段
            try:
                trigger_price = float(row.get("trigger_price") or 0.0)
            except ValueError:
                trigger_price = 0.0
            try:
                roi = float(row.get("roi") or 0.0)
            except ValueError:
                roi = 0.0

            # 4.1 计算该机会的整体 PnL（1 股）：
            t_list = targets_map.get(opp_id) or []
            if t_list:
                pnl = sum(t.get("weighted_profit", 0.0) for t in t_list)
            else:
                # 回退：使用整体 ROI 估算
                pnl = trigger_price * roi

            # 4.2 计算持续天数（自然日）
            start_dt = parse_yyyymmdd(trigger_date)
            end_dt = parse_yyyymmdd(exit_date)
            if start_dt and end_dt:
                duration_in_days = max((end_dt - start_dt).days, 1)
            else:
                duration_in_days = 1

            # 4.3 构造 tracking（暂时使用 start/end_date 作为 min/max 日期近似）
            try:
                max_price = float(row.get("max_price") or 0.0)
            except ValueError:
                max_price = 0.0
            try:
                min_price = float(row.get("min_price") or 0.0)
            except ValueError:
                min_price = 0.0

            if trigger_price > 0:
                max_ratio = (max_price - trigger_price) / trigger_price if max_price > 0 else 0.0
                min_ratio = (min_price - trigger_price) / trigger_price if min_price > 0 else 0.0
            else:
                max_ratio = 0.0
                min_ratio = 0.0

            tracking = {
                "max_close_reached": {
                    "price": max_price if max_price > 0 else trigger_price,
                    "date": exit_date,
                    "ratio": max_ratio,
                },
                "min_close_reached": {
                    "price": min_price if min_price > 0 else trigger_price,
                    "date": trigger_date,
                    "ratio": min_ratio,
                },
            }

            # 4.4 构造 completed_targets
            completed_targets: List[Dict[str, Any]] = []
            for t in t_list:
                sell_price = float(t.get("price") or 0.0)
                profit = float(t.get("profit") or 0.0)
                weighted_profit = float(t.get("weighted_profit") or 0.0)
                t_roi = float(t.get("roi") or 0.0)
                sell_ratio = float(t.get("sell_ratio") or 0.0)
                sell_date = t.get("date") or ""
                reason = (t.get("reason") or "").lower()

                if "win" in reason:
                    target_type = "take_profit"
                    name = reason
                elif "loss" in reason:
                    target_type = "stop_loss"
                    name = reason
                elif "expiration" in reason:
                    target_type = "expired"
                    name = "expiration"
                else:
                    target_type = "unknown"
                    name = reason or "unknown"

                completed_targets.append(
                    {
                        "name": name,
                        "target_type": target_type,
                        "sell_price": sell_price,
                        "sell_date": sell_date,
                        "sell_ratio": sell_ratio,
                        "profit": profit,
                        "weighted_profit": weighted_profit,
                        "profit_ratio": t_roi,
                        "target_price": trigger_price,
                        "extra_fields": {},
                    }
                )

            # 4.5 result 分类
            status = (row.get("status") or "").lower()
            if status in ("win", "loss", "open"):
                result = status
            else:
                if pnl > 0:
                    result = "win"
                elif pnl < 0:
                    result = "loss"
                else:
                    result = "open"

            # 4.6 构造 investment 记录
            overall_annual_return = get_annual_return(roi, duration_in_days)
            investment = {
                "result": result,
                "start_date": trigger_date,
                "end_date": exit_date,
                "purchase_price": trigger_price,
                "duration_in_days": duration_in_days,
                "overall_profit": pnl,
                "roi": roi,
                "overall_annual_return": overall_annual_return,
                "tracking": tracking,
                "completed_targets": completed_targets,
            }

            investments.append(investment)

            # 4.7 累计 summary 所需数据
            total_investments += 1
            total_profit += pnl
            total_duration += duration_in_days
            total_roi += roi

            if result == "win":
                total_win += 1
            elif result == "loss":
                total_loss += 1
            elif result == "open":
                total_open += 1

            if roi >= 0.2:
                profitable_count += 1
            elif 0 <= roi < 0.2:
                minor_profitable_count += 1
            elif roi < 0 and roi > -0.2:
                minor_unprofitable_count += 1
            else:
                unprofitable_count += 1

            holding = False
            current_exit_date = exit_date

        # 5. 计算单股 summary（复用 legacy 逻辑）
        avg_profit = to_ratio(total_profit, total_investments)
        avg_duration_in_days = to_ratio(total_duration, total_investments)
        avg_roi = to_ratio(total_roi, total_investments, decimals=4)

        annual_return_raw = get_annual_return(avg_roi, avg_duration_in_days)
        annual_return = float(annual_return_raw.real) if isinstance(annual_return_raw, complex) else float(annual_return_raw) if isinstance(annual_return_raw, (int, float)) else 0.0
        annual_return_in_trading_days_raw = get_annual_return(
            avg_roi, avg_duration_in_days, is_trading_days=True
        )
        annual_return_in_trading_days = float(annual_return_in_trading_days_raw.real) if isinstance(annual_return_in_trading_days_raw, complex) else float(annual_return_in_trading_days_raw) if isinstance(annual_return_in_trading_days_raw, (int, float)) else 0.0

        win_rate = to_ratio(
            profitable_count + minor_profitable_count, total_investments, 3
        )

        summary = {
            "total_investments": total_investments,
            "total_win": total_win,
            "total_loss": total_loss,
            "total_open": total_open,
            "profitable": profitable_count,
            "minor_profitable": minor_profitable_count,
            "unprofitable": unprofitable_count,
            "minor_unprofitable": minor_unprofitable_count,
            "win_rate": round(win_rate, 1),
            "total_profit": round(total_profit, 2),
            "avg_profit": round(avg_profit, 2),
            "avg_duration_in_days": round(avg_duration_in_days, 1),
            "avg_roi": round(avg_roi, 4),
            "annual_return": round(annual_return, 2),
            "annual_return_in_trading_days": round(annual_return_in_trading_days, 2),
        }

        return {
            "stock": self.stock_info,
            "investments": investments,
            "summary": summary,
        }

    # ------------------------------------------------------------------ #
    # 结果保存（Worker 独立保存）
    # ------------------------------------------------------------------ #
    def _save_stock_json(self, stock_summary: Dict[str, Any]) -> None:
        """
        在子进程中保存单个股票的 JSON 文件。
        
        目录结构：
            app/userspace/strategies/{strategy}/results/simulations/price_factor/{sim_version}/{stock_id}.json
        """
        # 使用传入的 sim_version_dir（模拟器版本目录）
        root = Path(self.sim_version_dir)
        root.mkdir(parents=True, exist_ok=True)

        stock_path = root / f"{self.stock_id}.json"
        with stock_path.open("w", encoding="utf-8") as f:
            json.dump(stock_summary, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
        
        logger.debug(f"[PriceFactorSimulatorWorker] 已保存: {stock_path}")

