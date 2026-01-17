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
import time

from core.modules.strategy.components.opportunity_enumerator.enumerator_settings import (
    OpportunityEnumeratorSettings,
)
from core.modules.strategy.models.strategy_settings import StrategySettings

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
        from core.infra.worker.multi_process.process_worker import ProcessWorker
        max_workers = ProcessWorker.resolve_max_workers(
            max_workers=max_workers,
            module_name='OpportunityEnumerator'
        )
        
        # 记录开始时间
        start_time = time.time()
        
        logger.info(
            f"🚀 开始枚举: strategy={strategy_name}, "
            f"period={start_date}~{end_date}, "
            f"stocks={len(stock_list)}, "
            f"workers={max_workers}"
        )
        
        # 0. 初始化性能分析器（在开始时就创建，以准确统计总时间）
        from core.modules.strategy.components.opportunity_enumerator.performance_profiler import (
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
        from core.modules.strategy.managers.version_manager import VersionManager
        output_dir, version_id = VersionManager.create_enumerator_version(
            strategy_name=strategy_name,
            use_sampling=enum_settings.use_sampling
        )
        # 记录版本目录信息，便于后续保存 metadata 和清理旧版本
        sub_dir = output_dir.parent            # test/ 或 output/ 目录
        version_dir_name = output_dir.name     # 版本目录名（自增ID）
        use_sampling = enum_settings.use_sampling

        # 2. 构建作业（每只股票一个 job）
        # 重要：枚举器（Layer 0）始终做“全量枚举”，不再按照调用方传入的 start_date 截断历史。
        # start_date/end_date 只用于：
        #   - metadata 记录
        #   - 上层应用决定如何消费结果（例如只用某个时间窗口内的机会）
        # 实际加载的数据范围由 Worker 使用统一的 DEFAULT_START_DATE 决定。
        from core.utils.date.date_utils import DateUtils
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
        from core.infra.worker import (
            # 新架构组件
            ProcessExecutor,
            MemoryAwareScheduler,
            ProcessExecutionMode,
        )
        
        # ⚠️ 说明：
        # 使用多进程执行器（ProcessExecutor + OpportunityEnumeratorWorker）
        # 但由于每个 job 的 payload 都包含完整的 K 线列表，跨进程序列化开销非常大，
        # 在本机测试中，2000 支股票多进程版本反而比单进程慢很多（> 3 分钟）。
        #
        # 为了保证“先跑通、结果稳定”，这里暂时回退到单线程多线程执行器：
        # - 子进程按需查询数据，通过 max_workers 限制并发数
        # - 子进程按需查询数据，通过 max_workers 限制并发数
        #
        # 后续如果要进一步提速，需要引入共享内存 / 批次级数据共享，避免序列化 klines。
        # 使用多进程执行器（ProcessExecutor + OpportunityEnumeratorWorker）
        # - 子进程使用 OpportunityEnumeratorWorker 按需查询数据
        # - 通过 max_workers 限制并发数，避免同时太多进程访问 DB，防止内存爆炸
        # - 对于 CPU 密集型任务，多进程可以真正利用多核 CPU
        # - 多进程通常比多线程（受 GIL 限制）更有效
        executor = ProcessExecutor(
            max_workers=max_workers,  # 使用计算出的 worker 数量
            execution_mode=ProcessExecutionMode.QUEUE,  # 队列模式：持续填充进程池
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
                "🔀 Worker 配置: executor=ProcessExecutor, max_workers=%d (原因: 多进程可以真正利用多核 CPU，适合 CPU 密集型任务)",
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

        # 批量执行（内存优化：按 batch 提交，子进程加载数据）
        # 注意：主进程严格禁止加载大型数据（K线数据等），只准备参数
        # 子进程使用 OpportunityEnumeratorWorker 按需查询数据
        # ProcessWorker 的 QUEUE 模式会持续填充进程池，保证多进程并行执行
        # 通过 max_workers 限制，保证同时只有有限数量的子进程在加载数据，避免内存爆炸
        
        # 按 batch 提交任务（主进程只准备参数，不加载数据）
        # 确定总任务数（用于进度跟踪）
        total_jobs = len(jobs)
        
        job_results = []
        finished_jobs = 0
        batch_count = 0
        total_batch_size = 0
        min_batch_size = None
        max_batch_size = 0
        
        for batch in scheduler.iter_batches():
            batch_stock_ids = [job['stock_id'] for job in batch]
            batch_size = len(batch_stock_ids)
            batch_count += 1
            total_batch_size += batch_size
            if min_batch_size is None or batch_size < min_batch_size:
                min_batch_size = batch_size
            if batch_size > max_batch_size:
                max_batch_size = batch_size
            
            # 构建 payload（只包含参数，不包含数据）
            # 子进程会使用 OpportunityEnumeratorWorker 按需查询数据
            process_jobs = []
            for job in batch:
                payload = {
                    'stock_id': job['stock_id'],
                    'strategy_name': job['strategy_name'],
                    'settings': job['settings'],
                    'start_date': job['start_date'],
                    'end_date': job['end_date'],
                    'output_dir': job['output_dir'],
                }
                process_jobs.append({'id': job['stock_id'], 'payload': payload})
            
            # 提交当前 batch 的任务（ProcessWorker 的 QUEUE 模式会持续填充进程池）
            # 传入总任务数，确保进度跟踪准确
            batch_jobs_for_executor = [{'id': job['id'], 'data': job['payload']} for job in process_jobs]
            batch_results = executor.run_jobs(batch_jobs_for_executor, total_jobs=total_jobs)
            
            # 释放当前 batch 的引用（帮助 GC）
            del process_jobs, batch_jobs_for_executor
            import gc
            gc.collect()
            
            # 更新调度器状态
            finished_jobs += len(batch)
            scheduler.update_after_batch(
                batch_size=len(batch),
                batch_results=batch_results,
                finished_jobs=finished_jobs,
            )
            
            # 收集结果
            job_results.extend(batch_results)
            
            # 定期输出监控信息
            should_log = (
                scheduler.should_log_progress() or 
                batch_count == 1  # 第一个 batch 完成后立即输出
            )
            if should_log:
                progress = scheduler.get_progress()
                stats = scheduler.get_monitor_stats()
                
                # 计算已用时间和预计剩余时间
                elapsed_time = time.time() - start_time
                if progress["finished_jobs"] > 0 and progress["progress_percent"] > 0:
                    avg_time_per_job = elapsed_time / progress["finished_jobs"]
                    remaining_jobs = progress["total_jobs"] - progress["finished_jobs"]
                    estimated_remaining = avg_time_per_job * remaining_jobs
                    eta_str = f", ETA: {estimated_remaining:.1f}s"
                else:
                    eta_str = ""
                
                # 格式化已用时间
                if elapsed_time < 60:
                    elapsed_str = f"{elapsed_time:.1f}s"
                elif elapsed_time < 3600:
                    elapsed_str = f"{elapsed_time/60:.1f}min"
                else:
                    hours = int(elapsed_time // 3600)
                    minutes = int((elapsed_time % 3600) // 60)
                    elapsed_str = f"{hours}h{minutes}min"
                
                logger.info(
                    "📊 枚举进度: %.1f%% (%d/%d), batch=%d, 内存=%.1f%%, 已用=%s%s",
                    progress["progress_percent"],
                    progress["finished_jobs"],
                    progress["total_jobs"],
                    batch_count,
                    stats["memory"]["usage_percent"],
                    elapsed_str,
                    eta_str,
                )
            
            # 检查内存告警
            warning = scheduler.get_memory_warning()
            if warning:
                logger.warning(f"⚠️  {warning}")
        
        all_results = job_results
        
        # 第三步：更新调度器状态（所有任务已完成）
        job_results = all_results
        finished_jobs = len(all_results)
        
        # 更新调度器最终状态
        scheduler.update_after_batch(
            batch_size=len(all_results),
            batch_results=all_results,
            finished_jobs=finished_jobs,
        )
        
        # 输出最终进度
        progress = scheduler.get_progress()
        stats = scheduler.get_monitor_stats()
        elapsed_time = time.time() - start_time
        
        if elapsed_time < 60:
            elapsed_str = f"{elapsed_time:.1f}s"
        elif elapsed_time < 3600:
            elapsed_str = f"{elapsed_time/60:.1f}min"
        else:
            hours = int(elapsed_time // 3600)
            minutes = int((elapsed_time % 3600) // 60)
            elapsed_str = f"{hours}h{minutes}min"
        
        logger.info(
            "📊 枚举完成: %.1f%% (%d/%d), 内存=%.1f%%, 总耗时=%s",
            progress["progress_percent"],
            progress["finished_jobs"],
            progress["total_jobs"],
            stats["memory"]["usage_percent"],
            elapsed_str,
        )
        
        # 检查内存告警
        warning = scheduler.get_memory_warning()
        if warning:
            logger.warning(f"⚠️  {warning}")
        
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
        
        logger.info(
            f"✅ 枚举完成: 成功={success_count}, 失败={failed_count}, "
            f"机会数={total_opportunities}, 总耗时={total_time_str}"
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
            # 全量模式：清理 output/ 目录
            OpportunityEnumerator._cleanup_old_versions(
                root_dir=sub_dir,
                max_keep_versions=enum_settings.max_output_versions,
                strategy_name=strategy_name,
                mode="output"
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
        from core.modules.strategy.components.opportunity_enumerator.enumerator_worker import OpportunityEnumeratorWorker
        worker = OpportunityEnumeratorWorker(payload)
        return worker.run()

    @staticmethod
    def _execute_single_job_compute_only(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Worker 包装函数（多进程执行）
        
        子进程使用 OpportunityEnumeratorWorker 按需查询数据。
        通过 max_workers 限制并发数，保证同时只有有限数量的子进程在加载数据，避免内存爆炸。
        """
        from core.modules.strategy.components.opportunity_enumerator.enumerator_worker import (
            OpportunityEnumeratorWorker,
        )

        # 子进程自行加载数据（通过 max_workers 限制，避免同时太多进程访问 DB）
        worker = OpportunityEnumeratorWorker(payload)
        return worker.run()
    
    @staticmethod
    def _load_strategy_settings(strategy_name: str) -> StrategySettings:
        """加载策略配置，并封装为通用 StrategySettings 模型"""
        import importlib
        
        module_path = f"userspace.strategies.{strategy_name}.settings"
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
            root_dir: 版本目录的根目录（test/ 或 output/）
            max_keep_versions: 最多保留的版本数
            strategy_name: 策略名称（用于日志）
            mode: 模式名称（"test" 或 "output"），用于日志
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
