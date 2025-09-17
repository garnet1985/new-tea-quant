#!/usr/bin/env python3
"""
HistoricLow 策略 - 寻找股票的历史低点，识别可能的买入机会
"""
from typing import Dict, List, Any
from loguru import logger

from app.analyzer.libs.simulator.simulator import Simulator
from ...libs.base_strategy import BaseStrategy
from .example_simulator import ExampleSimulator
from .settings import settings
from app.analyzer.libs.investment import InvestmentRecorder

class Example(BaseStrategy):
    """HistoricLow 策略实现"""
    
    # 策略启用状态
    # 如果不启用，在start.py运行时则会自动跳过这个策略的机会扫描和模拟
    is_enabled = False
    
    def __init__(self, db, is_verbose: bool = False):
        super().__init__(
            db=db, 
            is_verbose=is_verbose,
            name="example strategy",
            abbreviation="EXAMPLE"
        )
        
        # 加载策略设置
        self.settings = settings
        
        # 初始化投资记录器
        self.invest_recorder = InvestmentRecorder(self.settings['folder_name'])

        # 这个simulator是simulator库，当前文件夹下的simulator（ExampleSimulator）是存放simulator所有逻辑的主文件
        self.simulator = Simulator()

    def initialize(self):
        self._initialize_tables()

    def _initialize_tables(self):
        self.required_tables = {
            "stock_index": self.db.get_table_instance("stock_index"),
            "stock_kline": self.db.get_table_instance("stock_kline"),
            "adj_factor": self.db.get_table_instance("adj_factor"),
        }

    # ========================================================
    # External (Bridge) APIs:
    # ========================================================
    async def scan(self) -> List[Dict[str, Any]]:
        # 这个函数会在策略启用时自动调用，是用来扫描当前数据下的投资机会的

        # 这里可以添加一些策略的逻辑，比如：
        # 1. 根据策略的设置，加载一些数据
        # 2. 根据数据，生成一些投资机会
        # 3. 返回投资机会

        stock_idx = self.required_tables["stock_index"].load_filtered_index()

        if not stock_idx:
            return []

        opportunities = self._scan_stocks_with_worker(stock_idx)

        self.report(opportunities)

        return opportunities

    def simulate(self) -> Dict[str, Any]:
        # 这个函数会在策略启用时自动调用，是用来模拟策略的
        # 注意：模拟过程默认使用多进程，如果是使用类函数，函数必须是静态
        
        result = self.simulator.run(
            settings=settings,
            on_simulate_one_day=ExampleSimulator.simulate_single_day,
            on_single_stock_summary=self.stock_summary,
            on_simulate_complete=None
        )
        
        return result

    def report(self, opportunities: List[Dict[str, Any]]) -> None:
        # 这个函数会在策略启用时自动调用，是用来报告策略的扫描结果的
        # 这里可以添加一些汇总的逻辑，比如：
        # - 为找到的机会加上历史模拟结果

        if not opportunities:
            logger.info("🔍 未发现投资机会")
            return
        
        logger.info(f"🔍 发现 {len(opportunities)} 个投资机会")
        

    # ========================================================
    # Core logic:
    # ========================================================

    def _scan_stocks_with_worker(self, stock_idx: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        from utils.worker.multi_process.process_worker import ProcessWorker
        
        # 构建任务
        jobs = []
        for stock in stock_idx:
            job = {
                'stock': stock,
                'data': self.required_tables["stock_kline"].load_stock_kline_data(stock['id'], 'daily')
            }
            jobs.append(job)
        
        # 使用多进程执行
        worker = ProcessWorker(job_executor=self._scan_single_stock)
        results = worker.run_jobs(jobs)
        
        # 提取投资机会
        opportunities = []
        for result in results:
            if result.success and result.result_data:
                opportunities.extend(result.result_data)
        
        return opportunities

    def _scan_single_stock(self, job: Dict[str, Any]) -> List[Dict[str, Any]]:
        """扫描单只股票的投资机会"""
        stock = job['stock']
        daily_k_lines = job['data']
        # 使用ExampleSimulator的扫描逻辑
        # 这里可以添加一些策略的逻辑
        opportunities = []
        return opportunities


    # ========================================================
    # Result presentation:
    # ========================================================

    def stock_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        # 这个函数会在策略启用时自动调用，是用来汇总单只股票的模拟结果的
        # 这里可以添加一些汇总的逻辑，比如：
        # - 为找到的机会加上历史模拟结果
        return {}