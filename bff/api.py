"""
BFF API 业务逻辑
"""

import sys
import os
import json
from flask import jsonify
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class BFFApi:
    def __init__(self):
        """初始化BFF API"""
        # 延迟初始化策略相关，避免自动创建tmp目录
        self.strategy = None
        self.simulator = None
        self._hl_components_initialized = False

    def health_check(self):
        """健康检查"""
        return jsonify({
            "success": True,
            "message": "BFF API 运行正常",
            "timestamp": "当前时间"
        })

    def get_stock_kline(self, stock_id: str, term: str = 'daily'):
        """
        获取股票K线数据
        
        Args:
            stock_id: 股票ID (如: 000002.SZ)
            term: K线周期 (daily, monthly)
            
        Returns:
            dict: 包含K线数据的响应
        """
        try:
            # 添加项目根目录到Python路径
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            sys.path.append(project_root)
            
            # 导入数据库管理器和DataLoader
            from utils.db.db_manager import DatabaseManager
            from app.data_loader import DataLoader
            
            # 连接数据库
            db_manager = DatabaseManager()
            db_manager.connect()
            
            # 使用DataLoader加载K线数据（自动复权和过滤）
            loader = DataLoader(db_manager)
            qfq_kline_data = loader.load_klines(
                stock_id=stock_id,
                term=term,
                adjust='qfq',
                filter_negative=True
            )
            
            if not qfq_kline_data:
                return jsonify({
                    "success": False,
                    "message": f"未找到股票 {stock_id} 的 {term} K线数据",
                    "data": None
                }), 404
            
            # 格式化数据
            formatted_klines = []
            for record in qfq_kline_data:
                formatted_kline = {
                    'date': record['date'],
                    'open': float(record['open']),
                    'close': float(record['close']),
                    'highest': float(record['highest']),
                    'lowest': float(record['lowest']),
                    'volume': float(record['volume']) if record.get('volume') else 0,
                    'amount': float(record['amount']) if record.get('amount') else 0,
                    'priceChangeDelta': float(record['priceChangeDelta']) if record.get('priceChangeDelta') else 0,
                    'priceChangeRateDelta': float(record['priceChangeRateDelta']) if record.get('priceChangeRateDelta') else 0,
                    'preClose': float(record['preClose']) if record.get('preClose') else 0
                }
                formatted_klines.append(formatted_kline)
            
            return jsonify({
                "success": True,
                "message": "获取成功",
                "data": {
                    "stock_id": stock_id,
                    "term": term,
                    "total_records": len(formatted_klines),
                    "klines": formatted_klines
                }
            })
            
        except Exception as e:
            logger.error(f"获取股票K线失败: {e}")
            return jsonify({
                "success": False,
                "message": f"获取失败: {str(e)}",
                "data": None
            }), 500

    def get_stock_scan(self, strategy: str, stock_id: str):
        """
        获取股票策略扫描结果
        
        Args:
            strategy: 策略名称 (如: historicLow)
            stock_id: 股票ID (如: 000002.SZ)
            
        Returns:
            dict: 包含扫描结果的响应
        """
        try:
            if strategy.lower() != 'historiclow':
                return jsonify({
                    "success": False,
                    "message": f"暂不支持策略: {strategy}",
                    "data": None
                }), 400
            
            # 这里先返回一个简单的响应，后续再完善
            return jsonify({
                "success": True,
                "message": "扫描完成",
                "data": {
                    "strategy": strategy,
                    "stock_id": stock_id,
                    "scan_time": "当前时间",
                    "opportunities": [],
                    "total_opportunities": 0
                }
            })
            
        except Exception as e:
            logger.error(f"股票扫描失败: {e}")
            return jsonify({
                "success": False,
                "message": f"扫描失败: {str(e)}",
                "data": None
            }), 500

    def get_stock_simulate(self, strategy: str, stock_id: str):
        """
        获取股票策略模拟结果
        
        Args:
            strategy: 策略名称 (如: historicLow)
            stock_id: 股票ID (如: 000002.SZ)
            
        Returns:
            dict: 包含模拟结果的响应
        """
        try:
            if strategy.lower() != 'historiclow':
                return jsonify({
                    "success": False,
                    "message": f"暂不支持策略: {strategy}",
                    "data": None
                }), 400
            
            # 这里先返回一个简单的响应，后续再完善
            return jsonify({
                "success": True,
                "message": "模拟完成",
                "data": {
                    "strategy": strategy,
                    "stock_id": stock_id,
                    "simulation_result": "模拟结果待实现"
                }
            })
            
        except Exception as e:
            logger.error(f"股票模拟失败: {e}")
            return jsonify({
                "success": False,
                "message": f"模拟失败: {str(e)}",
                "data": None
            }), 500

    def _get_latest_session_dir(self):
        """获取最新的模拟会话目录"""
        try:
            # 查找tmp目录
            tmp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                 "app", "analyzer", "strategy", "historicLow", "tmp")
            
            if not os.path.exists(tmp_dir):
                return None
            
            # 查找最新的会话目录
            session_dirs = [d for d in os.listdir(tmp_dir) if os.path.isdir(os.path.join(tmp_dir, d)) and d != '__pycache__']
            if not session_dirs:
                return None
            
            # 按名称排序，获取最新的
            latest_session = sorted(session_dirs)[-1]
            return os.path.join(tmp_dir, latest_session)
            
        except Exception as e:
            logger.error(f"获取最新会话目录失败: {e}")
            return None

    def get_stock_all_historic_lows(self, stock_id: str):
        """
        获取股票所有计算出的历史低点
        
        Args:
            stock_id: 股票ID (如: 000002.SZ)
            
        Returns:
            dict: 包含所有历史低点的响应
        """
        try:
            # 获取最新的会话目录
            latest_session_dir = self._get_latest_session_dir()
            if not latest_session_dir:
                return jsonify({
                    "success": False,
                    "message": "未找到模拟会话",
                    "data": None
                }), 404
            
            # 查找股票文件
            stock_file_path = os.path.join(latest_session_dir, f"{stock_id}.json")
            if not os.path.exists(stock_file_path):
                return jsonify({
                    "success": False,
                    "message": f"未找到股票 {stock_id} 的模拟结果",
                    "data": None
                }), 404
            
            # 读取股票数据
            with open(stock_file_path, 'r', encoding='utf-8') as f:
                stock_data = json.load(f)
            
            # 提取所有历史低点
            all_historic_lows = stock_data.get('all_historic_lows', [])
            
            return jsonify({
                "success": True,
                "message": "获取成功",
                "data": {
                    "stock_id": stock_id,
                    "total_low_points": len(all_historic_lows),
                    "all_historic_lows": all_historic_lows
                }
            })
            
        except Exception as e:
            logger.error(f"获取股票历史低点失败: {e}")
            return jsonify({
                "success": False,
                "message": f"获取失败: {str(e)}",
                "data": None
            }), 500

    def get_stock_hl_analysis(self, stock_id: str):
        """
        获取股票的HL策略分析结果
        
        Args:
            stock_id: 股票ID (如: 000002.SZ)
            
        Returns:
            dict: 包含HL分析结果的响应
        """
        try:
            # 获取最新的会话目录
            latest_session_dir = self._get_latest_session_dir()
            if not latest_session_dir:
                return jsonify({
                    "success": False,
                    "message": "未找到模拟会话",
                    "data": None
                }), 404
            
            # 查找股票文件
            stock_file_path = os.path.join(latest_session_dir, f"{stock_id}.json")
            if not os.path.exists(stock_file_path):
                return jsonify({
                    "success": False,
                    "message": f"未找到股票 {stock_id} 的模拟结果",
                    "data": None
                }), 404
            
            # 读取股票数据
            with open(stock_file_path, 'r', encoding='utf-8') as f:
                stock_data = json.load(f)
            
            return jsonify({
                "success": True,
                "message": "获取成功",
                "data": stock_data
            })
            
        except Exception as e:
            logger.error(f"获取股票HL分析失败: {e}")
            return jsonify({
                "success": False,
                "message": f"获取失败: {str(e)}",
                "data": None
            }), 500
