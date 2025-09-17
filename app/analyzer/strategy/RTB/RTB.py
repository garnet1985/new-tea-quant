#!/usr/bin/env python3
"""
HistoricLow 策略 - 寻找股票的历史低点，识别可能的买入机会
"""
from typing import Dict, List, Any, Optional
from loguru import logger

from app.analyzer.libs.data_processor.data_loader import DataLoader
from app.analyzer.libs.simulator.simulator import Simulator
from app.analyzer.strategy.RTB.settings import settings
from ...libs.base_strategy import BaseStrategy
from app.analyzer.libs.investment import InvestmentRecorder

class ReverseTrendBet(BaseStrategy):
    """ReverseTrendBet 策略实现"""
    
    # 策略启用状态
    is_enabled = False
    
    def __init__(self, db, is_verbose: bool = False):
        super().__init__(
            db=db, 
            is_verbose=is_verbose,
            name="ReverseTrendBet",
            abbreviation="RTB"
        )
        
        # 加载策略设置（字典）
        self.settings = settings
        
        # 初始化投资记录器
        self.invest_recorder = InvestmentRecorder(self.settings['folder_name'])

        self.simulator = Simulator()
        self.loader = DataLoader()

    def initialize(self):
        # 注册所需基础表
        self.required_tables = {
            "stock_index": self.db.get_table_instance("stock_index"),
            "stock_kline": self.db.get_table_instance("stock_kline"),
            "adj_factor": self.db.get_table_instance("adj_factor"),
        }

    # ========================================================
    # External (Bridge) APIs:
    # ========================================================
    async def scan(self) -> List[Dict[str, Any]]:
        stock_idx = self.required_tables["stock_index"].load_filtered_index()

        if not stock_idx:
            return []

        opportunities = self.scan_stocks_on_parallel(stock_idx)

        # self.report(opportunities)

        return opportunities

    def simulate(self) -> Dict[str, Any]:
        # 运行模拟 - 传递单日模拟函数和自定义汇总函数
        result = self.simulator.run(
            settings=settings,
            on_simulate_one_day=ReverseTrendBet.simulate_single_day,
            on_single_stock_summary=None,
            on_simulate_complete=None
        )
        return result

    def report(self, opportunities: List[Dict[str, Any]]) -> None:
        pass

    # ========================================================
    # Core logic:
    # ========================================================

    @staticmethod
    def scan_opportunity(stock_id: str, all_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """扫描单只股票的投资机会 - Debug版：安全打印入参结构"""
        try:
            data_type = type(all_data).__name__
            data_len = len(all_data) if hasattr(all_data, '__len__') else 'NA'
            logger.info(f"[RTB] scan_opportunity | stock={stock_id} | all_data_type={data_type} | len={data_len}")
            if isinstance(all_data, list) and all_data:
                sample = all_data[0]
                if isinstance(sample, dict):
                    keys_preview = list(sample.keys())[:10]
                    logger.info(f"[RTB] sample_keys={keys_preview}")
                    logger.debug(f"[RTB] sample_pick={{'date': {sample.get('date')}, 'open': {sample.get('open')}, 'close': {sample.get('close')}}}")
                else:
                    logger.info(f"[RTB] sample_type={type(sample).__name__}")
            elif isinstance(all_data, dict):
                logger.info(f"[RTB] dict_keys={list(all_data.keys())[:10]}")
        except Exception as e:
            logger.error(f"[RTB] scan_opportunity debug failed: {e}")
            return None

        # TODO: 在这里加入实际的机会识别逻辑
        return None






    @staticmethod
    def simulate_single_day(stock_id: str, current_date: str, current_record: Dict[str, Any], 
                           all_data: List[Dict[str, Any]], current_investment: Optional[Dict[str, Any]], settings: Dict[str, Any]) -> Dict[str, Any]:
        # 示例占位：此处可基于 all_data 与 settings 计算交易信号
        # 暂不生成新建仓或结算，保持最小实现
        if current_investment:
            logger.debug("RTB simulate: position open")
        else:
            opportunity = ReverseTrendBet.scan_opportunity(stock_id, all_data)

        return {
            'new_investment': None,
            'settled_investments': [],
            'current_investment': current_investment
        }


























    # ========================================================
    # Result presentation:
    # ========================================================

    # def to_presentable_report(self, opportunities: List[Dict[str, Any]]) -> None:
    #     """
    #     将投资机会转换为可呈现的报告格式
        
    #     Args:
    #         opportunities: 投资机会列表
    #     """
    #     if not opportunities:
    #         logger.info("📊 无投资机会可报告")
    #         return
        
    #     logger.info("📊 HistoricLow 策略扫描报告")
    #     logger.info("=" * 50)
        
    #     # 按股票分组统计
    #     stock_stats = {}
    #     for opp in opportunities:
    #         stock_id = opp.get('stock', {}).get('id', 'unknown')
    #         if stock_id not in stock_stats:
    #             stock_stats[stock_id] = 0
    #         stock_stats[stock_id] += 1
        
    #     # 显示统计信息
    #     logger.info(f"📈 发现投资机会: {len(opportunities)} 个")
    #     logger.info(f"📊 涉及股票: {len(stock_stats)} 只")
        
    #     # 显示每只股票的详细信息
    #     for stock_id, count in sorted(stock_stats.items()):
    #         logger.info(f"  {stock_id}: {count} 个机会")
        
    #     logger.info("=" * 50)



    # def stock_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
    #     """
    #     在HL策略中，按需简化每个投资的 opportunity 字段
        
    #     Args:
    #         result: 单只股票的模拟结果（包含 investments/settled_investments）
            
    #     Returns:
    #         Dict: 追加到默认summary的track（此处无额外统计，返回空）
    #     """
    #     # 就地简化：仅保留 HL 关键信息，避免污染通用框架
    #     for key in ('settled_investments', 'investments'):
    #         for inv in result.get(key, []) or []:
    #             opp = inv.get('opportunity')
    #             if not opp:
    #                 continue
    #             inv['opportunity'] = {
    #                 'date': opp.get('date'),
    #                 'price': opp.get('price'),
    #                 'lower_bound': opp.get('lower_bound'),
    #                 'upper_bound': opp.get('upper_bound'),
    #                 'low_point_ref': opp.get('low_point_ref')
    #             }
    #     # 不新增额外summary字段
    #     return {}




    # ========================================================
    # Worker:
    # ========================================================
    def scan_stocks_on_parallel(self, stock_idx: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """使用多进程扫描股票"""
        from utils.worker.multi_process.process_worker import ProcessWorker
        
        # 构建任务
        jobs = []
        for stock in stock_idx:
            job = {
                'stock': stock,
                'data': self.loader.load_stock_klines_by_setting(stock['id'], self.settings),
                'settings': self.settings,
            }
            jobs.append(job)
        
        # 调试模式：串行执行，确保日志可见
        debug_serial = ((self.settings.get('mode') or {}).get('debug_serial')) is True
        if debug_serial:
            logger.info(f"[RTB] debug_serial is ON | jobs={len(jobs)}")
            results = []
            for job in jobs:
                res = ReverseTrendBet.scan_opportunity_job(job)
                # 组装一个与并行结果结构兼容的对象
                results.append(type('R', (), {'success': True, 'result_data': res})())
        else:
            # 使用多进程执行
            worker = ProcessWorker(job_executor=ReverseTrendBet.scan_opportunity_job)
            results = worker.run_jobs(jobs)
        
        # 提取投资机会
        opportunities = []
        for result in results:
            if result.success and result.result_data:
                opportunities.extend(result.result_data)
        
        return opportunities

    @staticmethod
    def scan_opportunity_job(job: Dict[str, Any]) -> List[Dict[str, Any]]:
        """扫描单只股票的投资机会"""
        stock = job['stock']
        term_to_k = job['data']
        settings = job.get('settings') or {}
        
        if not term_to_k:
            return []
        
        # 基础周期数据
        base_term = ((settings.get('klines') or {}).get('base_term')) or 'daily'
        daily_k_lines = term_to_k.get(base_term, [])

        # Debug：打印当前股票与样本结构（仅首条）
        try:
            first_keys = list(daily_k_lines[0].keys())[:10] if daily_k_lines else []
            logger.info(f"[RTB] job | stock={stock.get('id')} | base_term={base_term} | len={len(daily_k_lines)} | first_keys={first_keys}")
        except Exception:
            pass

        # 扫描逻辑（占位）
        opportunities = []
        for i in range(len(daily_k_lines)):
            current_data = daily_k_lines[:i+1]
            opportunity = ReverseTrendBet.scan_opportunity(stock['id'], current_data)
            if opportunity:
                opportunities.append(opportunity)
        
        return opportunities