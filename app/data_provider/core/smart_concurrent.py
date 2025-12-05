#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SmartConcurrentExecutor - 智能并发执行器

⭐ 解决问题：
- 一个data_type可能调用多个API
- 不同API限流速率不同
- 需要智能选择串行/并行策略

策略：
- sequential: 串行执行（简单安全）
- parallel: 并行执行（需要协调）
- adaptive: 自适应（根据限流速率自动选择）
"""

import asyncio
from typing import Dict, List, Callable, Any
from loguru import logger

from .rate_limit_registry import RateLimitRegistry


class SmartConcurrentExecutor:
    """
    智能并发执行器
    
    ⭐ 处理多个API的限流协调
    """
    
    def __init__(self, rate_limit_registry: RateLimitRegistry):
        """
        初始化执行器
        
        Args:
            rate_limit_registry: API限流注册表
        """
        self.rate_limit_registry = rate_limit_registry
    
    async def execute_multi_api_jobs(
        self,
        jobs_by_api: Dict[str, List[Dict]],
        executor_by_api: Dict[str, Callable],
        strategy: str = "adaptive"
    ) -> Dict[str, Any]:
        """
        执行多个API的任务
        
        Args:
            jobs_by_api: 按API分组的任务 {api_identifier: [jobs]}
            executor_by_api: 每个API的执行器 {api_identifier: executor_func}
            strategy: 执行策略（sequential | parallel | adaptive）
        
        Returns:
            Dict: 执行结果 {api_identifier: result}
        """
        if strategy == "adaptive":
            return await self._execute_adaptive(jobs_by_api, executor_by_api)
        elif strategy == "sequential":
            return await self._execute_sequential(jobs_by_api, executor_by_api)
        elif strategy == "parallel":
            return await self._execute_parallel(jobs_by_api, executor_by_api)
        else:
            raise ValueError(f"不支持的策略: {strategy}")
    
    async def _execute_sequential(
        self, 
        jobs_by_api: Dict[str, List[Dict]], 
        executor_by_api: Dict[str, Callable]
    ) -> Dict[str, Any]:
        """
        串行执行
        
        ⭐ 简单安全，但慢
        
        Args:
            jobs_by_api: 按API分组的任务
            executor_by_api: 每个API的执行器
        
        Returns:
            Dict: 执行结果
        """
        results = {}
        
        for api_id, jobs in jobs_by_api.items():
            logger.info(f"▶️  执行API [{api_id}]，共 {len(jobs)} 个任务")
            
            executor = executor_by_api[api_id]
            results[api_id] = await self._execute_jobs(jobs, executor)
        
        return results
    
    async def _execute_parallel(
        self, 
        jobs_by_api: Dict[str, List[Dict]], 
        executor_by_api: Dict[str, Callable]
    ) -> Dict[str, Any]:
        """
        并行执行
        
        ⭐ 快但需要协调限流
        
        挑战：
        - 日线API：100次/分钟（快）
        - 周线API：50次/分钟（中）
        - 月线API：30次/分钟（慢）
        
        如果并行执行，需要确保：
        - 日线不会占用所有资源
        - 月线不会被饿死
        
        Args:
            jobs_by_api: 按API分组的任务
            executor_by_api: 每个API的执行器
        
        Returns:
            Dict: 执行结果
        """
        # 为每个API创建独立的任务
        tasks = []
        
        for api_id, jobs in jobs_by_api.items():
            executor = executor_by_api[api_id]
            
            # 创建任务
            task = asyncio.create_task(
                self._execute_jobs_with_fairness(api_id, jobs, executor)
            )
            tasks.append((api_id, task))
        
        # 并发执行
        task_results = await asyncio.gather(*[t[1] for t in tasks])
        
        # 组装结果
        results = {}
        for (api_id, _), result in zip(tasks, task_results):
            results[api_id] = result
        
        return results
    
    async def _execute_adaptive(
        self, 
        jobs_by_api: Dict[str, List[Dict]], 
        executor_by_api: Dict[str, Callable]
    ) -> Dict[str, Any]:
        """
        自适应策略
        
        ⭐ 根据API限流情况智能选择
        
        规则：
        - 如果所有API限流速率相近 → 并行
        - 如果有明显瓶颈API → 串行
        
        Args:
            jobs_by_api: 按API分组的任务
            executor_by_api: 每个API的执行器
        
        Returns:
            Dict: 执行结果
        """
        # 分析限流速率
        rates = {}
        for api_id in jobs_by_api.keys():
            limiter = self.rate_limit_registry.get_limiter(api_id)
            rates[api_id] = limiter.max_per_minute if limiter else 1000
        
        if not rates:
            # 没有限流信息，使用串行
            logger.info("📊 无限流信息，使用串行策略")
            return await self._execute_sequential(jobs_by_api, executor_by_api)
        
        min_rate = min(rates.values())
        max_rate = max(rates.values())
        
        # 判断
        if max_rate / min_rate < 2:
            # 速率差异小 → 并行
            logger.info(
                f"📊 使用并行策略（API限流相近：{min_rate}-{max_rate}次/分钟）"
            )
            return await self._execute_parallel(jobs_by_api, executor_by_api)
        else:
            # 速率差异大 → 串行
            logger.info(
                f"📊 使用串行策略（API限流差异大：{min_rate}-{max_rate}次/分钟）"
            )
            return await self._execute_sequential(jobs_by_api, executor_by_api)
    
    async def _execute_jobs_with_fairness(
        self, 
        api_id: str, 
        jobs: List[Dict],
        executor: Callable
    ) -> Any:
        """
        执行任务（带公平性保证）
        
        ⭐ 确保慢API不会被快API饿死
        
        Args:
            api_id: API标识
            jobs: 任务列表
            executor: 执行器函数
        
        Returns:
            执行结果
        """
        limiter = self.rate_limit_registry.get_limiter(api_id)
        
        # 根据限流速率计算合理的并发数
        # 限流慢 → 并发数小
        # 限流快 → 并发数大
        if limiter:
            max_workers = min(4, max(1, limiter.max_per_minute // 20))  # 简化计算
        else:
            max_workers = 4
        
        # 执行
        return await self._execute_jobs(jobs, executor, max_workers=max_workers)
    
    async def _execute_jobs(
        self, 
        jobs: List[Dict], 
        executor: Callable,
        max_workers: int = 4
    ) -> List[Any]:
        """
        执行任务列表（并发）
        
        Args:
            jobs: 任务列表
            executor: 执行器函数
            max_workers: 最大并发数
        
        Returns:
            List: 执行结果列表
        """
        # 使用asyncio.Semaphore控制并发
        semaphore = asyncio.Semaphore(max_workers)
        
        async def execute_with_semaphore(job):
            async with semaphore:
                # 如果是同步函数，需要包装
                if asyncio.iscoroutinefunction(executor):
                    return await executor(job)
                else:
                    # 同步函数，在线程池中执行
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, executor, job)
        
        # 并发执行
        results = await asyncio.gather(*[
            execute_with_semaphore(job) for job in jobs
        ])
        
        return results

