#!/usr/bin/env python3
"""
Opportunity Enumerator - 机会枚举器

职责：
- 枚举指定策略的所有投资机会（完整枚举，不跳过）
- CSV 双表存储（opportunities + targets）
- 多进程并行
- 每次都重新计算（保证最新）
"""

from typing import List, Dict, Any, Union
import json
from pathlib import Path
from datetime import datetime
import logging

from app.core.modules.strategy.components.opportunity_enumerator.enumerator_settings import (
    OpportunityEnumeratorSettings,
)
from app.core.modules.strategy.models.strategy_settings import StrategySettings

logger = logging.getLogger(__name__)


class OpportunityEnumerator:
    """机会枚举器（主进程）"""
    
    @staticmethod
    def enumerate(
        strategy_name: str,
        start_date: str,
        end_date: str,
        stock_list: List[str],
        max_workers: Union[str, int] = 'auto'
    ) -> List[Dict[str, Any]]:
        """
        枚举所有投资机会（完整枚举）
        
        Args:
            strategy_name: 策略名称
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            stock_list: 股票列表
            max_workers: 最大并行数
                - 'auto': 自动计算（推荐）
                - 数字: 手动指定（会做保护，最多 2 倍 CPU 核心数）
        
        Returns:
            所有 opportunities（字典列表）
        """
        # 解析 max_workers（仍复用 ProcessWorker 的辅助逻辑）
        from app.core.infra.worker.multi_process.process_worker import ProcessWorker
        max_workers = ProcessWorker.resolve_max_workers(
            max_workers=max_workers,
            module_name='OpportunityEnumerator'
        )
        
        logger.info(
            f"开始枚举: strategy={strategy_name}, "
            f"period={start_date}~{end_date}, "
            f"stocks={len(stock_list)}, "
            f"workers={max_workers}"
        )
        
        # 0. 初始化性能分析器（在开始时就创建，以准确统计总时间）
        from app.core.modules.strategy.components.opportunity_enumerator.performance_profiler import (
            AggregateProfiler,
            PerformanceMetrics
        )
        aggregate_profiler = AggregateProfiler()
        
        # 1. 加载策略配置（通用 StrategySettings 模型）
        base_settings = OpportunityEnumerator._load_strategy_settings(strategy_name)

        # 1.1 通过枚举器专用 Settings 视图进行校验与补全（组合，而非继承）
        enum_settings = OpportunityEnumeratorSettings.from_base(base_settings)
        validated_settings = enum_settings.to_dict()

        # 1.2 准备版本目录（一次枚举 = 一个版本）
        # 使用统一的 VersionManager 创建版本目录
        from app.core.modules.strategy.managers.version_manager import VersionManager
        output_dir, version_id = VersionManager.create_enumerator_version(
            strategy_name=strategy_name,
            use_sampling=enum_settings.use_sampling
        )
        # 记录版本目录信息，便于后续保存 metadata 和清理旧版本
        sub_dir = output_dir.parent            # test/ 或 pool/ 目录
        version_dir_name = output_dir.name     # 版本目录名（自增ID）
        use_sampling = enum_settings.use_sampling

        # 2. 构建作业（每只股票一个 job）
        # 重要：枚举器（Layer 0）始终做“全量枚举”，不再按照调用方传入的 start_date 截断历史。
        # start_date/end_date 只用于：
        #   - metadata 记录
        #   - 上层应用决定如何消费结果（例如只用某个时间窗口内的机会）
        # 实际加载的数据范围由 Worker 使用统一的 DEFAULT_START_DATE 决定。
        from app.core.utils.date.date_utils import DateUtils
        enum_start_date = DateUtils.DEFAULT_START_DATE

        # 为每个子进程分配 ID 起始值（避免进程间冲突）
        # 假设每个股票最多产生 10000 个机会（实际可能更少，但留有余量）
        id_block_size = 10000
        jobs = []
        for idx, stock_id in enumerate(stock_list):
            start_id = idx * id_block_size + 1  # 从 1 开始，每个股票分配 10000 个 ID
            jobs.append({
                'stock_id': stock_id,
                'strategy_name': strategy_name,
                # 传入“已校验 & 补全”的 settings 视图，供 Worker 使用
                'settings': validated_settings,
                # 对 Worker 而言，start_date 固定为 DEFAULT_START_DATE（全量历史）
                'start_date': enum_start_date,
                'end_date': end_date,
                # 让子进程知道自身应将 CSV 写到哪里
                'output_dir': str(output_dir),
                # ID 起始值（由主进程分配，避免进程间冲突）
                'opportunity_id_start': start_id,
            })
        
        # 3. 使用新的模块化架构进行批量调度
        from app.core.infra.worker import (
            # 新架构组件
            ProcessExecutor,
            MemoryAwareScheduler,
            ProcessExecutionMode,
        )
        
        # ⚠️ 说明：
        # 理论上，这里可以使用多进程（ProcessExecutor + ComputeOnlyOpportunityEnumeratorWorker）
        # 但由于每个 job 的 payload 都包含完整的 K 线列表，跨进程序列化开销非常大，
        # 在本机测试中，2000 支股票多进程版本反而比单进程慢很多（> 3 分钟）。
        #
        # 为了保证“先跑通、结果稳定”，这里暂时回退到单线程多线程执行器：
        # - DB 仍然只在主进程批量查询（DuckDB 文件锁安全）
        # - 子任务在同一进程内串行执行 compute-only worker，避免 pickle 大对象
        #
        # 后续如果要进一步提速，需要引入共享内存 / 批次级数据共享，避免序列化 klines。
        from app.core.infra.worker import MultiThreadExecutor, ThreadExecutionMode
        executor = MultiThreadExecutor(
            max_workers=1,
            execution_mode=ThreadExecutionMode.PARALLEL,
            job_executor=OpportunityEnumerator._execute_single_job_compute_only,
            is_verbose=False,
        )
        
        # 创建调度器（支持 "auto" 自动计算）
        scheduler = MemoryAwareScheduler(
            jobs=jobs,
            memory_budget_mb=enum_settings.memory_budget_mb,
            warmup_batch_size=enum_settings.warmup_batch_size,
            min_batch_size=enum_settings.min_batch_size,
            max_batch_size=enum_settings.max_batch_size,
            monitor_interval=enum_settings.monitor_interval,
            log=logger,
        )
        
        # 如果需要，打印一次 worker / scheduler 决策摘要
        if enum_settings.is_verbose:
            logger.info(
                "🧵 Worker 配置: executor=ProcessExecutor, max_workers=%d (原因: DuckDB 单进程文件锁限制，只在主进程读 DB，子进程纯计算)",
                max_workers,
            )
            try:
                memory_budget = getattr(getattr(scheduler, "monitor", None), "memory_budget_mb", None)
            except Exception:
                memory_budget = None
            logger.info(
                "🧠 Scheduler 配置: total_jobs=%d, memory_budget=%s, warmup_batch=%s, min_batch=%s, max_batch=%s",
                len(jobs),
                f"{memory_budget:.1f}MB" if isinstance(memory_budget, (int, float)) else str(memory_budget),
                scheduler.warmup_batch_size,
                scheduler.min_batch_size,
                scheduler.max_batch_size,
            )

        # 批量执行（带批量数据预加载优化）
        job_results = []
        finished_jobs = 0
        # 统计 batch 信息
        batch_count = 0
        total_batch_size = 0
        min_batch_size = None
        max_batch_size = 0
        
        # 初始化 DataManager（用于批量查询，仅主进程使用）
        from app.core.modules.data_manager import DataManager
        batch_data_mgr = DataManager(is_verbose=False)
        
        for batch in scheduler.iter_batches():
            # ============================================================
            # 批量数据预加载优化：一次性查询这一批所有股票的K线数据
            # ============================================================
            import time
            batch_start_time = time.time()
            
            batch_stock_ids = [job['stock_id'] for job in batch]
            batch_size = len(batch_stock_ids)
            batch_count += 1
            total_batch_size += batch_size
            if min_batch_size is None or batch_size < min_batch_size:
                min_batch_size = batch_size
            if batch_size > max_batch_size:
                max_batch_size = batch_size
            
            # 批量查询K线数据（一次查询所有股票）
            batch_klines_map = {}
            try:
                from app.core.utils.date.date_utils import DateUtils
                enum_start_date = DateUtils.DEFAULT_START_DATE
                
                # 从 settings 中提取 term 和 adjust
                data_config = validated_settings.get('data', {})
                base_price_source = data_config.get('base_price_source', 'stock_kline_daily')
                adjust_type = data_config.get('adjust_type', 'qfq')
                
                # 提取周期（daily/weekly/monthly）
                base_str = str(base_price_source).lower()
                if 'daily' in base_str:
                    term = 'daily'
                elif 'weekly' in base_str:
                    term = 'weekly'
                elif 'monthly' in base_str:
                    term = 'monthly'
                else:
                    term = 'daily'
                
                # 提取复权方式（qfq/hfq/none）
                adjust_str = str(adjust_type).lower()
                if adjust_str in ['qfq', 'hfq', 'none']:
                    adjust = adjust_str
                else:
                    adjust = 'qfq'
                
                batch_klines_map = batch_data_mgr.stock.kline.load_batch(
                    stock_ids=batch_stock_ids,
                    term=term,
                    start_date=enum_start_date,
                    end_date=end_date,
                    adjust=adjust,
                )
                
                batch_query_time = time.time() - batch_start_time
                total_kline_count = sum(len(klines) for klines in batch_klines_map.values())
                stocks_with_data = sum(1 for klines in batch_klines_map.values() if klines)
                
                # 总是记录批量查询信息（即使 is_verbose=False，因为这对性能分析很重要）
                logger.info(
                    "📦 Batch 数据预加载: stocks=%d, 有数据=%d, klines=%d, 耗时=%.2fs, avg=%.1fms/stock",
                    batch_size,
                    stocks_with_data,
                    total_kline_count,
                    batch_query_time,
                    batch_query_time / batch_size * 1000 if batch_size > 0 else 0.0,
                )
            except Exception as e:
                logger.warning(f"批量查询K线数据失败，回退到单股票查询: {e}", exc_info=True)
                batch_klines_map = {}
            
            # 构建 compute-only payload（不再访问 DB）
            process_jobs = []
            for job in batch:
                stock_id = job['stock_id']
                klines = batch_klines_map.get(stock_id, [])
                payload = {
                    'stock_id': stock_id,
                    'strategy_name': job['strategy_name'],
                    'settings': job['settings'],
                    'klines': klines,
                    'start_date': job['start_date'],
                    'end_date': job['end_date'],
                    'output_dir': job['output_dir'],
                }
                process_jobs.append({'id': stock_id, 'payload': payload})
            
            # 执行当前 batch（单进程、compute-only）
            thread_jobs = [{'id': job['id'], 'data': job['payload']} for job in process_jobs]
            batch_results = executor.run_jobs(thread_jobs)
            
            # 更新调度器状态
            finished_jobs += len(batch)
            scheduler.update_after_batch(
                batch_size=len(batch),
                batch_results=batch_results,
                finished_jobs=finished_jobs,
            )
            
            # 收集结果
            job_results.extend(batch_results)
            
            # 定期输出监控信息（使用简化的 Progress API）
            if scheduler.should_log_progress():
                progress = scheduler.get_progress()
                stats = scheduler.get_monitor_stats()
                logger.info(
                    "📊 枚举进度: %.1f%% (%d/%d), batch=%d, 内存=%.1f%%",
                    progress["progress_percent"],
                    progress["finished_jobs"],
                    progress["total_jobs"],
                    progress["current_batch_size"],
                    stats["memory"]["usage_percent"],
                )
            
            # 检查内存告警
            warning = scheduler.get_memory_warning()
            if warning:
                logger.warning(f"⚠️  {warning}")
            
            # 清理资源，协助 GC
            del batch, process_jobs, batch_results
            import gc
            gc.collect()
        
        # 关闭执行器
        executor.shutdown()
        
        # 打印 batch 统计信息
        if batch_count > 0:
            avg_batch_size = total_batch_size / batch_count
            logger.info(
                "📦 Batch 统计: total_stocks=%d, total_batches=%d, "
                "avg_batch_size=%.1f, min_batch_size=%s, max_batch_size=%d",
                len(jobs),
                batch_count,
                avg_batch_size,
                str(min_batch_size) if min_batch_size is not None else "N/A",
                max_batch_size,
            )
        
        # 4. 聚合结果和性能指标（AggregateProfiler 已在开始时创建）
        total_opportunities = 0
        success_count = 0
        failed_count = 0
        
        for job_result in job_results:
            if job_result.status.value == 'completed':
                result = job_result.result
                if result.get('success'):
                    success_count += 1
                    total_opportunities += int(result.get('opportunity_count', 0))
                    
                    # 聚合性能指标
                    perf_data = result.get('performance_metrics')
                    if perf_data:
                        metrics = PerformanceMetrics()
                        metrics.time_load_data = perf_data.get('time', {}).get('load_data', 0)
                        metrics.time_calculate_indicators = perf_data.get('time', {}).get('calculate_indicators', 0)
                        metrics.time_enumerate = perf_data.get('time', {}).get('enumerate', 0)
                        metrics.time_serialize = perf_data.get('time', {}).get('serialize', 0)
                        metrics.time_save_csv = perf_data.get('time', {}).get('save_csv', 0)
                        metrics.time_total = perf_data.get('time', {}).get('total', 0)
                        metrics.db_queries = perf_data.get('io', {}).get('db_queries', 0)
                        metrics.db_query_time = perf_data.get('io', {}).get('db_query_time', 0)
                        metrics.file_writes = perf_data.get('io', {}).get('file_writes', 0)
                        metrics.file_write_time = perf_data.get('io', {}).get('file_write_time', 0)
                        metrics.file_write_size = int(perf_data.get('io', {}).get('file_write_size_mb', 0) * 1024 * 1024)
                        metrics.kline_count = perf_data.get('data', {}).get('kline_count', 0)
                        metrics.opportunity_count = perf_data.get('data', {}).get('opportunity_count', 0)
                        metrics.target_count = perf_data.get('data', {}).get('target_count', 0)
                        metrics.memory_peak = perf_data.get('memory', {}).get('peak_mb', 0)
                        metrics.memory_start = perf_data.get('memory', {}).get('start_mb', 0)
                        metrics.memory_end = perf_data.get('memory', {}).get('end_mb', 0)
                        
                        aggregate_profiler.add_stock_metrics(result.get('stock_id'), metrics)
                else:
                    failed_count += 1
                    logger.warning(
                        f"枚举失败: stock={result.get('stock_id')}, "
                        f"error={result.get('error')}"
                    )
            else:
                failed_count += 1
                logger.warning(
                    f"任务失败: job_id={job_result.job_id}, "
                    f"error={job_result.error}"
                )
        
        logger.info(
            f"✅ 枚举完成: 成功={success_count}, 失败={failed_count}, "
            f"机会数={total_opportunities}"
        )
        
        # 打印性能报告
        if success_count > 0:
            aggregate_profiler.print_report()
            
            # 同时保存性能报告到文件（会话级，使用 0_ 前缀方便排序）
            performance_summary = aggregate_profiler.get_summary()
            performance_file = output_dir / "0_performance_report.json"
            with performance_file.open("w", encoding="utf-8") as f:
                json.dump(performance_summary, f, indent=2, ensure_ascii=False)
            logger.info(f"📊 性能报告已保存: {performance_file}")
        
        # 5. 保存 metadata（含 settings 快照、版本信息）
        # 注意：is_full_enumeration 标记在所有子进程完成后才设置，避免异常中断导致数据不全
        is_full_enumeration = not enum_settings.use_sampling  # False = 采样模式，True = 全量模式
        OpportunityEnumerator._save_results(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            output_dir=output_dir,
            version_id=version_id,
            version_dir_name=version_dir_name,
            opportunity_count=total_opportunities,
            settings_snapshot=validated_settings,
            is_full_enumeration=is_full_enumeration,
        )
        
        # 6. 清理旧版本（根据模式选择对应的清理配置）
        if use_sampling:
            # 测试模式：清理 test/ 目录
            OpportunityEnumerator._cleanup_old_versions(
                root_dir=sub_dir,
                max_keep_versions=enum_settings.max_test_versions,
                strategy_name=strategy_name,
                mode="test"
            )
        else:
            # 全量模式：清理 sot/ 目录
            OpportunityEnumerator._cleanup_old_versions(
                root_dir=sub_dir,
                max_keep_versions=enum_settings.max_sot_versions,
                strategy_name=strategy_name,
                mode="sot"
            )
        
        # 7. 返回结果（目前直接返回 summary，而不是全量 opportunities）
        return [{
            'strategy_name': strategy_name,
            'version_id': version_id,
            'version_dir': version_dir_name,
            'opportunity_count': total_opportunities,
            'success_stocks': success_count,
            'failed_stocks': failed_count,
        }]
    
    @staticmethod
    def _execute_single_job(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Worker 包装函数
        
        - 在多进程模式下作为子进程入口
        - 在多线程模式下作为线程执行函数
        """
        from app.core.modules.strategy.components.opportunity_enumerator.enumerator_worker import OpportunityEnumeratorWorker
        worker = OpportunityEnumeratorWorker(payload)
        return worker.run()

    @staticmethod
    def _execute_single_job_compute_only(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        compute-only Worker 包装函数（多进程纯计算）
        """
        from app.core.modules.strategy.components.opportunity_enumerator.enumerator_worker import (
            ComputeOnlyOpportunityEnumeratorWorker,
        )

        worker = ComputeOnlyOpportunityEnumeratorWorker(payload)
        return worker.run()
    
    @staticmethod
    def _load_strategy_settings(strategy_name: str) -> StrategySettings:
        """加载策略配置，并封装为通用 StrategySettings 模型"""
        import importlib
        
        module_path = f"app.userspace.strategies.{strategy_name}.settings"
        try:
            module = importlib.import_module(module_path)
            raw_settings = module.settings
            return StrategySettings.from_dict(raw_settings)
        except Exception as e:
            logger.error(f"加载策略配置失败: {strategy_name}, error={e}")
            raise
    
    @staticmethod
    def _save_results(
        strategy_name: str,
        start_date: str,
        end_date: str,
        output_dir: Path,
        version_id: int,
        version_dir_name: str,
        opportunity_count: int,
        settings_snapshot: Dict[str, Any],
        is_full_enumeration: bool = False
    ):
        """
        保存本次枚举运行的 metadata（不再在这里写 CSV，CSV 由子进程按股票各自写出）
        
        Args:
            is_full_enumeration: 是否为全量枚举
                - True: 全量股票枚举，可以作为上层应用的基础数据
                - False: 测试模式（采样枚举），不能作为上层应用的基础数据
                注意：此标记在所有子进程完成后才设置，避免异常中断导致数据不全
        """
        now = datetime.now()
        metadata = {
            'strategy_name': strategy_name,
            'start_date': start_date,
            'end_date': end_date,
            'opportunity_count': opportunity_count,
            'created_at': now.isoformat(),
            'version_id': version_id,
            'version_dir': version_dir_name,
            'settings_snapshot': settings_snapshot,
            'is_full_enumeration': is_full_enumeration  # 标记是否为全量枚举
        }
        
        # 会话级 metadata 也使用 0_ 前缀
        with open(output_dir / '0_metadata.json', 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        enum_mode = "全量枚举" if is_full_enumeration else "测试模式（采样）"
        logger.info(f"✅ 枚举 metadata 已保存: {output_dir} ({enum_mode})")
    
    @staticmethod
    def _cleanup_old_versions(
        root_dir: Path,
        max_keep_versions: int,
        strategy_name: str,
        mode: str = "test"
    ):
        """
        清理旧的枚举版本
        
        按照版本 ID 排序，保留最新的 max_keep_versions 个版本，删除最早的版本。
        
        Args:
            root_dir: 版本目录的根目录（test/ 或 sot/）
            max_keep_versions: 最多保留的版本数
            strategy_name: 策略名称（用于日志）
            mode: 模式名称（"test" 或 "sot"），用于日志
        """
        if max_keep_versions < 1:
            return  # 至少保留 1 个版本
        
        try:
            # 1. 扫描所有版本目录
            version_dirs = []
            for item in root_dir.iterdir():
                if item.is_dir() and item.name != "__pycache__" and item.name != "meta.json":
                    # 版本目录格式：{version_id}_{timestamp}
                    if "_" in item.name:
                        version_dirs.append(item)
            
            if not version_dirs:
                return
            
            # 2. 读取每个版本的 metadata.json，提取版本信息
            versions = []
            for version_dir in version_dirs:
                metadata_path = version_dir / "metadata.json"
                if not metadata_path.exists():
                    # 如果没有 metadata.json，尝试从目录名解析版本 ID
                    try:
                        version_id = int(version_dir.name.split("_")[0])
                        versions.append({
                            "version_id": version_id,
                            "created_at": "",
                            "version_dir": version_dir,
                            "version_dir_name": version_dir.name
                        })
                    except (ValueError, IndexError):
                        continue
                    continue
                
                try:
                    with metadata_path.open("r", encoding="utf-8") as f:
                        metadata = json.load(f)
                    
                    version_id = metadata.get("version_id", 0)
                    created_at = metadata.get("created_at", "")
                    versions.append({
                        "version_id": version_id,
                        "created_at": created_at,
                        "version_dir": version_dir,
                        "version_dir_name": version_dir.name
                    })
                except Exception as e:
                    logger.warning(f"读取版本 metadata 失败: {version_dir}, error={e}")
                    continue
            
            if len(versions) <= max_keep_versions:
                return  # 版本数未超过限制，无需清理
            
            # 3. 按版本 ID 排序（降序，最新的在前）
            versions.sort(key=lambda x: x["version_id"], reverse=True)
            
            # 4. 保留最新的 max_keep_versions 个版本，删除其余的
            versions_to_delete = versions[max_keep_versions:]
            
            if not versions_to_delete:
                return
            
            logger.info(
                f"🧹 开始清理旧版本: 策略={strategy_name}, 模式={mode}, "
                f"版本总数={len(versions)}, "
                f"保留={max_keep_versions}, "
                f"删除={len(versions_to_delete)}"
            )
            
            deleted_count = 0
            for version_info in versions_to_delete:
                version_dir = version_info["version_dir"]
                try:
                    import shutil
                    shutil.rmtree(version_dir)
                    deleted_count += 1
                    logger.info(f"  ✅ 已删除旧版本: {version_info['version_dir_name']} (version_id={version_info['version_id']})")
                except Exception as e:
                    logger.warning(f"  ⚠️  删除版本失败: {version_info['version_dir_name']}, error={e}")
            
            if deleted_count > 0:
                logger.info(f"✅ 版本清理完成 ({mode}): 已删除 {deleted_count} 个旧版本")
        
        except Exception as e:
            logger.error(f"❌ 清理旧版本时发生错误 ({mode}): {e}", exc_info=True)
