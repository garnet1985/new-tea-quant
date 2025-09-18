#!/usr/bin/env python3
"""
扫描执行器组件 - 封装多进程扫描逻辑，完全隐藏多进程实现细节
"""
from typing import Dict, List, Any, Optional
from loguru import logger
from utils.worker.multi_process.process_worker import ProcessWorker
from .data_loader import DataLoader


def _scan_single_stock_standalone(job_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    独立的股票扫描函数 - 每个子进程创建独立数据库连接
    
    Args:
        job_payload: 任务载荷，包含stock_id、stock_name、settings等轻量级信息
        
    Returns:
            Dict: 包含扫描结果的字典，格式为:
            {
                'stock_id': str,
                'stock_name': str,
                'opportunities': List[Dict],  # 发现的机会列表
                'has_opportunities': bool     # 是否发现机会
            }
    """
    if not isinstance(job_payload, dict):
        return {'stock_id': '', 'stock_name': '', 'opportunities': [], 'has_opportunities': False}
    
    stock_id = job_payload.get('stock_id')
    stock_name = job_payload.get('stock_name', '')
    stock_symbol = job_payload.get('stock_symbol', '')
    settings = job_payload.get('settings', {})
    strategy_class_name = job_payload.get('strategy_class_name', '')
    strategy_module_path = job_payload.get('strategy_module_path', '')
    
    if not isinstance(stock_id, str) or not stock_id:
        return {'stock_id': stock_id or '', 'stock_name': stock_name, 'opportunities': [], 'has_opportunities': False}
    
    # 步骤3: 在进程中获取股票数据（每个子进程独立的简单连接）
    try:
        import os
        
        # 获取当前进程ID，用于日志标识
        process_id = str(os.getpid())
        
        # 每个子进程创建自己独立的pymysql连接，完全绕过DatabaseManager
        import pymysql
        from utils.db.db_config import DB_CONFIG
        
        # 创建独立的pymysql连接
        connection = pymysql.connect(
            host=DB_CONFIG['base']['host'],
            port=DB_CONFIG['base']['port'],
            user=DB_CONFIG['base']['user'],
            password=DB_CONFIG['base']['password'],
            database=DB_CONFIG['base']['database'],
            charset='utf8mb4',
            autocommit=True
        )
        
        # 直接使用pymysql连接进行数据查询，完全绕过DatabaseManager
        # 这样可以避免任何连接冲突问题
        cursor = connection.cursor()
        
        # 直接查询股票数据
        stock_data = {}
        
        # 查询日K线数据
        cursor.execute("""
            SELECT date, open, close, highest, lowest, volume, amount
            FROM stock_kline 
            WHERE id = %s AND term = 'daily'
            ORDER BY date ASC
        """, (stock_id,))
        
        daily_k_lines = []
        for row in cursor.fetchall():
            daily_k_lines.append({
                'date': row[0],  # 策略期望的字段名是 'date'
                'open': float(row[1]),
                'close': float(row[2]),
                'high': float(row[3]),
                'low': float(row[4]),
                'vol': float(row[5]),
                'amount': float(row[6])
            })
        
        stock_data['daily'] = daily_k_lines
        
        cursor.close()
        
        # 关闭连接
        connection.close()
        
    except Exception as e:
        logger.error(f"❌ 子进程加载股票 {stock_id}({stock_name}) 数据失败: {e}")
        return {'stock_id': stock_id, 'stock_name': stock_name, 'opportunities': [], 'has_opportunities': False}
    
    # 获取基础周期数据
    kline_config = settings.get('klines', {})
    base_term = kline_config.get('base_term', 'daily')
    daily_k_lines = stock_data.get(base_term, [])
    
    if not daily_k_lines:
        return {'stock_id': stock_id, 'stock_name': stock_name, 'opportunities': [], 'has_opportunities': False}
    
    # 步骤4: 在子进程中重新创建策略实例，避免pickle问题
    try:
        import importlib
        strategy_module = importlib.import_module(strategy_module_path)
        strategy_class = getattr(strategy_module, strategy_class_name)
        
        # 创建策略实例（不调用initialize，避免数据库操作）
        # 创建一个简单的模拟数据库对象，避免策略初始化时的数据库操作
        class MockDB:
            def get_table_instance(self, table_name):
                return None
        
        strategy_instance = strategy_class(db=MockDB(), is_verbose=False)
        
    except Exception as e:
        logger.error(f"❌ 子进程创建策略实例失败: {e}")
        return {'stock_id': stock_id, 'stock_name': stock_name, 'opportunities': [], 'has_opportunities': False}
    
    # 使用用户定义的scan_opportunity逻辑寻找机会
    opportunities: List[Dict[str, Any]] = []
    
    # 扫描每一天的投资机会
    for i in range(len(daily_k_lines)):
        current_data = daily_k_lines[:i+1]
        
        # 调用用户定义的scan_opportunity方法
        opportunity = strategy_instance.scan_opportunity(stock_id, current_data)
        
        if opportunity:
            # 确保机会包含股票信息
            if 'stock' not in opportunity:
                opportunity['stock'] = {}
            
            opportunity['stock'].update({
                'id': stock_id,
                'name': stock_name,
                'symbol': stock_symbol
            })
            
            opportunities.append(opportunity)
    
    return {
        'stock_id': stock_id,
        'stock_name': stock_name,
        'stock_symbol': stock_symbol,
        'opportunities': opportunities,
        'has_opportunities': len(opportunities) > 0
    }


class ScanExecutor:
    """扫描执行器 - 封装多进程扫描逻辑，对用户完全透明"""
    
    def __init__(self, strategy, db_manager=None, is_verbose: bool = False):
        """
        初始化扫描执行器
        
        Args:
            strategy: 策略实例
            db_manager: 全局数据库管理器实例（可选）
            is_verbose: 是否启用详细日志
        """
        self.strategy = strategy
        self.db_manager = db_manager
        self.is_verbose = is_verbose
    
    def scan_all_stocks(self, settings: Dict[str, Any], 
                       max_workers: Optional[int] = None,
                       batch_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        扫描所有股票的投资机会 - 完全隐藏多进程实现
        
        Args:
            settings: 策略设置
            max_workers: 最大并行进程数，None时使用CPU核心数
            batch_size: Batch模式下的batch大小，None时使用CPU核心数
            
        Returns:
            List[Dict]: 所有发现的投资机会列表
        """
        # 步骤1: 使用DataLoader获取目标股票清单（轻量级数据）
        if self.db_manager:
            data_loader = DataLoader(self.db_manager)
        else:
            # 使用连接池的DatabaseManager
            from utils.db.db_manager import DatabaseManager
            db = DatabaseManager(use_connection_pool=True, is_verbose=False)
            db.initialize()
            data_loader = DataLoader(db)
        
        stock_list = data_loader.load_stock_list(settings)
        
        if not stock_list:
            logger.info("🔍 未找到可扫描的股票")
            return []
        
        logger.info(f"🔍 开始扫描 {len(stock_list)} 只股票的投资机会")
        
        # 步骤2: 调用scan_with_worker函数开始多进程搜寻机会
        opportunities = self._scan_with_worker(stock_list, settings, max_workers, batch_size)
        
        # 步骤5: 汇总机会并调用report函数输出结果
        if opportunities:
            logger.info(f"🔍 发现 {len(opportunities)} 个投资机会")
            self.strategy.report(opportunities)
        else:
            logger.info("🔍 未发现投资机会")
        
        return opportunities
    
    def _get_stock_list(self, settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        步骤1: 使用DataLoader获取目标股票清单（轻量级数据）
        
        Args:
            settings: 策略设置
            
        Returns:
            List[Dict]: 股票清单，只包含id和name等轻量级信息
        """
        try:
            # 获取股票列表（只包含基本信息，避免内存爆炸）
            stock_list = self.data_loader.load_stock_list(settings, self.strategy.name)
            
            # 只保留必要的轻量级字段
            lightweight_stocks = []
            for stock in stock_list:
                lightweight_stocks.append({
                    'id': stock.get('id'),
                    'name': stock.get('name', ''),
                    'symbol': stock.get('symbol', '')
                })
            
            return lightweight_stocks
            
        except Exception as e:
            logger.error(f"❌ 获取股票清单失败: {e}")
            return []
    
    def _scan_with_worker(self, stock_list: List[Dict[str, Any]], 
                         settings: Dict[str, Any],
                         max_workers: Optional[int] = None,
                         batch_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        步骤2: 调用scan_with_worker函数开始多进程搜寻机会
        
        Args:
            stock_list: 股票清单
            settings: 策略设置
            max_workers: 最大并行进程数
            batch_size: Batch模式下的batch大小
            
        Returns:
            List[Dict]: 所有发现的投资机会列表
        """
        # 构建任务（只传递轻量级数据）
        jobs = self._build_scan_jobs(stock_list, settings)
        
        # 使用多进程执行扫描
        opportunities = self._execute_scan_jobs(jobs, max_workers, batch_size)
        
        return opportunities
    
    def _build_scan_jobs(self, stock_list: List[Dict[str, Any]], 
                        settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        构建扫描任务 - 只传递轻量级数据
        
        Args:
            stock_list: 股票清单
            settings: 策略设置
            
        Returns:
            List[Dict]: 任务列表
        """
        jobs = []
        for idx, stock in enumerate(stock_list, start=1):
            # 只传递轻量级数据，避免内存爆炸和pickle问题
            job_data = {
                'stock_id': stock['id'],
                'stock_name': stock.get('name', ''),
                'stock_symbol': stock.get('symbol', ''),
                'settings': settings,
                'strategy_class_name': self.strategy.__class__.__name__,
                'strategy_module_path': f"app.analyzer.strategy.{self.strategy.get_abbr()}.{self.strategy.get_abbr()}"
            }
            
            jobs.append({
                'id': f"{self.strategy.get_abbr()}_scan_{stock['id']}",
                'data': job_data
            })
            
            # 构建进度日志（每200只打印一次）
            if idx % 200 == 0:
                logger.info(f"[{self.strategy.get_abbr()}] building jobs progress: {idx}/{len(stock_list)} ({idx/len(stock_list)*100:.2f}%)")
        
        return jobs
    
    def _execute_scan_jobs(self, jobs: List[Dict[str, Any]], 
                          max_workers: Optional[int] = None,
                          batch_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        执行扫描任务 - 多进程扫描，带进度打印
        
        Args:
            jobs: 任务列表
            max_workers: 最大并行进程数
            batch_size: Batch模式下的batch大小
            
        Returns:
            List[Dict]: 所有发现的投资机会列表
        """
        # 使用标准multiprocessing，每个子进程创建独立数据库连接
        if max_workers is None:
            import os
            max_workers = os.cpu_count() or 4
        
        logger.info(f"[{self.strategy.get_abbr()}] 使用标准多进程扫描，进程数: {max_workers}")
        
        # 提取任务数据
        job_data_list = [job['data'] for job in jobs]
        
        # 使用标准multiprocessing
        import multiprocessing
        with multiprocessing.Pool(processes=max_workers) as pool:
            # 使用imap_unordered获得实时进度反馈
            results = []
            total_jobs = len(job_data_list)
            
            # 使用imap_unordered获得实时进度
            for i, result in enumerate(pool.imap_unordered(_scan_single_stock_standalone, job_data_list), 1):
                results.append(result)
                
                # 每完成一个任务就打印进度
                if isinstance(result, dict):
                    stock_id = result.get('stock_id', '')
                    stock_name = result.get('stock_name', '')
                    has_opportunities = result.get('has_opportunities', False)
                    
                    if has_opportunities:
                        logger.info(f"🔍 [{self.strategy.get_abbr()}] {stock_id}({stock_name}): 发现机会 - 进度: {i}/{total_jobs} ({i/total_jobs*100:.1f}%)")
                    else:
                        logger.info(f"🔍 [{self.strategy.get_abbr()}] {stock_id}({stock_name}): 未发现机会 - 进度: {i}/{total_jobs} ({i/total_jobs*100:.1f}%)")
                else:
                    logger.info(f"🔍 [{self.strategy.get_abbr()}] 任务完成 - 进度: {i}/{total_jobs} ({i/total_jobs*100:.1f}%)")
                
                # 每100个任务打印一次汇总进度
                if i % 100 == 0:
                    logger.info(f"🔍 [{self.strategy.get_abbr()}] 已完成 {i}/{total_jobs} 个任务 ({i/total_jobs*100:.1f}%)")
        
        # 汇总进度
        logger.info(f"[{self.strategy.get_abbr()}] executed jobs: total={len(jobs)} success={len(results)}")
        
        # 提取投资机会并统计结果
        opportunities: List[Dict[str, Any]] = []
        opportunities_found = 0
        
        for result in results:
            if isinstance(result, dict):
                stock_opportunities = result.get('opportunities', [])
                has_opportunities = result.get('has_opportunities', False)
                
                if has_opportunities:
                    opportunities_found += 1
                
                # 收集所有机会
                opportunities.extend(stock_opportunities)
        
        # 打印最终统计
        logger.info(f"🔍 [{self.strategy.get_abbr()}] 扫描完成: {opportunities_found}/{len(results)} 只股票发现机会，共发现 {len(opportunities)} 个投资机会")
        
        return opportunities
    
