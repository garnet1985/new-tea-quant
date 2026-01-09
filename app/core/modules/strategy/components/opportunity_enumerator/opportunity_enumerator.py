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
        # 解析 max_workers
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
        
        # 1. 加载策略配置（通用 StrategySettings 模型）
        base_settings = OpportunityEnumerator._load_strategy_settings(strategy_name)

        # 1.1 通过枚举器专用 Settings 视图进行校验与补全（组合，而非继承）
        enum_settings = OpportunityEnumeratorSettings.from_base(base_settings)
        validated_settings = enum_settings.to_dict()

        # 1.2 准备版本目录（一次枚举 = 一个版本）
        root_dir = Path("app") / "userspace" / "strategies" / strategy_name / "results" / "opportunity_enums"
        root_dir.mkdir(parents=True, exist_ok=True)

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
        output_dir = root_dir / version_dir_name
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1.3 立刻更新 meta.json（版本管理），不依赖后续流程是否成功
        new_meta = {
            "next_version_id": next_version_id + 1,
            "last_updated": now.isoformat(),
            "strategy_name": strategy_name,
        }
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(new_meta, f, indent=2, ensure_ascii=False)

        # 2. 构建作业（每只股票一个 job）
        jobs = []
        for stock_id in stock_list:
            jobs.append({
                'stock_id': stock_id,
                'strategy_name': strategy_name,
                # 传入“已校验 & 补全”的 settings 视图，供 Worker 使用
                'settings': validated_settings,
                'start_date': start_date,
                'end_date': end_date,
                # 让子进程知道自身应将 CSV 写到哪里
                'output_dir': str(output_dir),
            })
        
        # 3. 多进程执行
        from app.core.infra.worker.multi_process.process_worker import ProcessWorker, ExecutionMode
        
        # 创建 ProcessWorker 实例
        worker_pool = ProcessWorker(
            max_workers=max_workers,
            execution_mode=ExecutionMode.QUEUE,
            job_executor=OpportunityEnumerator._execute_single_job,
            is_verbose=False
        )
        
        # 构建 ProcessWorker 格式的 jobs
        process_jobs = [{'id': job['stock_id'], 'payload': job} for job in jobs]
        
        # 执行作业
        worker_pool.run_jobs(process_jobs)
        
        # 获取结果
        job_results = worker_pool.get_results()
        
        # 4. 聚合结果（只聚合 summary，不再拉回全量 opportunities）
        total_opportunities = 0
        success_count = 0
        failed_count = 0
        
        for job_result in job_results:
            if job_result.status.value == 'completed':
                result = job_result.result
                if result.get('success'):
                    success_count += 1
                    total_opportunities += int(result.get('opportunity_count', 0))
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
        
        # 5. 保存 metadata（含 settings 快照、版本信息）
        OpportunityEnumerator._save_results(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            output_dir=output_dir,
            version_id=next_version_id,
            version_dir_name=version_dir_name,
            opportunity_count=total_opportunities,
            settings_snapshot=validated_settings,
        )
        
        # 6. 返回结果（目前直接返回 summary，而不是全量 opportunities）
        return [{
            'strategy_name': strategy_name,
            'version_id': next_version_id,
            'version_dir': version_dir_name,
            'opportunity_count': total_opportunities,
            'success_stocks': success_count,
            'failed_stocks': failed_count,
        }]
    
    @staticmethod
    def _execute_single_job(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Worker 包装函数（在子进程中调用，必须是模块级函数才能被 pickle）"""
        from app.core.modules.strategy.components.opportunity_enumerator.enumerator_worker import OpportunityEnumeratorWorker
        worker = OpportunityEnumeratorWorker(payload)
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
        settings_snapshot: Dict[str, Any]
    ):
        """
        保存本次枚举运行的 metadata（不再在这里写 CSV，CSV 由子进程按股票各自写出）
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
            'settings_snapshot': settings_snapshot
        }
        
        with open(output_dir / 'metadata.json', 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ 枚举 metadata 已保存: {output_dir}")
