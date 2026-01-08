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
import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class OpportunityEnumerator:
    """机会枚举器（主进程）"""
    
    # 固定配置
    OUTPUT_BASE_DIR = "results/opportunity_enumerator"
    
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
        
        # 1. 加载策略配置
        settings = OpportunityEnumerator._load_strategy_settings(strategy_name)
        
        # 2. 构建作业
        jobs = []
        for stock_id in stock_list:
            jobs.append({
                'stock_id': stock_id,
                'strategy_name': strategy_name,
                'settings': settings,
                'start_date': start_date,
                'end_date': end_date
            })
        
        # 3. 多进程执行
        from app.core.infra.worker.multi_process.process_worker import ProcessWorker
        from app.core.modules.strategy.components.opportunity_enumerator.enumerator_worker import OpportunityEnumeratorWorker
        
        results = ProcessWorker.execute(
            worker_class=OpportunityEnumeratorWorker,
            job_payloads=jobs,
            max_workers=max_workers
        )
        
        # 4. 聚合结果
        all_opportunities = []
        success_count = 0
        failed_count = 0
        
        for result in results:
            if result['success']:
                success_count += 1
                all_opportunities.extend(result['opportunities'])
            else:
                failed_count += 1
                logger.warning(
                    f"枚举失败: stock={result['stock_id']}, "
                    f"error={result.get('error')}"
                )
        
        logger.info(
            f"✅ 枚举完成: 成功={success_count}, 失败={failed_count}, "
            f"机会数={len(all_opportunities)}"
        )
        
        # 5. 保存结果到 CSV
        OpportunityEnumerator._save_results(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            opportunities=all_opportunities
        )
        
        # 6. 返回结果（字典列表）
        return all_opportunities
    
    @staticmethod
    def _load_strategy_settings(strategy_name: str) -> Dict[str, Any]:
        """加载策略配置"""
        import importlib
        
        module_path = f"app.userspace.strategies.{strategy_name}.settings"
        try:
            module = importlib.import_module(module_path)
            return module.settings
        except Exception as e:
            logger.error(f"加载策略配置失败: {strategy_name}, error={e}")
            raise
    
    @staticmethod
    def _save_results(
        strategy_name: str,
        start_date: str,
        end_date: str,
        opportunities: List[Dict[str, Any]]
    ):
        """
        保存枚举结果到 CSV
        
        文件结构：
        results/opportunity_enumerator/
        └── {strategy_name}/
            └── {start_date}_{end_date}/
                ├── opportunities.csv  # 主表
                ├── targets.csv        # 子表
                └── metadata.json      # 元信息
        """
        # 1. 构建输出路径
        output_dir = Path(OpportunityEnumerator.OUTPUT_BASE_DIR) / strategy_name / f"{start_date}_{end_date}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. 准备数据
        opps_data = []
        targets_data = []
        
        for opp in opportunities:
            # 主表数据（排除 completed_targets）
            opp_row = {k: v for k, v in opp.items() if k != 'completed_targets'}
            opps_data.append(opp_row)
            
            # 子表数据
            for target in opp.get('completed_targets', []):
                target_row = {
                    'opportunity_id': opp['opportunity_id'],
                    **target
                }
                targets_data.append(target_row)
        
        # 3. 保存 CSV
        df_opps = pd.DataFrame(opps_data)
        df_targets = pd.DataFrame(targets_data)
        
        df_opps.to_csv(output_dir / 'opportunities.csv', index=False)
        df_targets.to_csv(output_dir / 'targets.csv', index=False)
        
        # 4. 保存元信息
        metadata = {
            'strategy_name': strategy_name,
            'start_date': start_date,
            'end_date': end_date,
            'opportunity_count': len(opportunities),
            'created_at': pd.Timestamp.now().isoformat()
        }
        
        with open(output_dir / 'metadata.json', 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ 结果已保存: {output_dir}")
