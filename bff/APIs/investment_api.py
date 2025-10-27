"""
投资跟踪相关 API
"""
import sys
import os
from flask import jsonify
from loguru import logger
import json as json_lib

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


class InvestmentApi:
    """投资跟踪相关API"""
    
    def __init__(self, db_manager=None):
        """初始化
        
        Args:
            db_manager: DatabaseManager实例，如果为None则自行创建
        """
        if db_manager is None:
            from utils.db.db_manager import DatabaseManager
            self.db_manager = DatabaseManager()
            self.db_manager.initialize()
        else:
            self.db_manager = db_manager
        
        # 缓存表实例
        self.trades_model = None
        self.operations_model = None
        self.stock_list_model = None
        self.kline_model = None
    
    def _get_trades_model(self):
        """获取trades表实例"""
        if self.trades_model is None:
            self.trades_model = self.db_manager.get_table_instance('investment_trades')
        return self.trades_model
    
    def _get_operations_model(self):
        """获取operations表实例"""
        if self.operations_model is None:
            self.operations_model = self.db_manager.get_table_instance('investment_operations')
        return self.operations_model
    
    def _get_stock_list_model(self):
        """获取stock_list表实例"""
        if self.stock_list_model is None:
            self.stock_list_model = self.db_manager.get_table_instance('stock_list')
        return self.stock_list_model
    
    def _get_kline_model(self):
        """获取kline表实例"""
        if self.kline_model is None:
            self.kline_model = self.db_manager.get_table_instance('stock_kline')
        return self.kline_model
    
    def get_all_open_trades(self):
        """
        获取所有正在进行中的交易
        """
        try:
            trades_model = self._get_trades_model()
            operations_model = self._get_operations_model()
            stock_list_model = self._get_stock_list_model()
            kline_model = self._get_kline_model()
            
            # 获取所有持仓中的交易
            trades = trades_model.load_all_open()
            
            # 获取股票信息映射
            stock_ids = [trade['stock_id'] for trade in trades if trade['stock_id']]
            stock_info_map = stock_list_model.load_stocks_by_ids(stock_ids)
            
            # 获取最新价格和日期
            latest_prices = {}
            latest_dates = {}
            for stock_id in stock_ids:
                latest_kline = kline_model.get_most_recent_one_by_term(stock_id, 'daily')
                if latest_kline:
                    latest_prices[stock_id] = float(latest_kline['close'])
                    latest_dates[stock_id] = latest_kline['date']
            
            # 计算每笔交易的持仓信息
            result = []
            for trade in trades:
                stock_id = trade['stock_id']
                
                # 计算当前持仓
                holding = operations_model.get_current_holding(trade['id'])
                
                # 获取最新价格和日期
                current_price = latest_prices.get(stock_id, 0)
                current_price_date = latest_dates.get(stock_id, None)
                
                # 计算收益
                if holding['avg_cost'] and current_price > 0:
                    profit_rate = (current_price - holding['avg_cost']) / holding['avg_cost']
                    profit_amount = (current_price - holding['avg_cost']) * holding['amount']
                else:
                    profit_rate = 0
                    profit_amount = 0
                
                # 计算当前投入金额（当前持仓数量 * 平均成本）
                total_invested = holding['amount'] * holding['avg_cost']
                
                # 获取股票信息
                stock_info = stock_info_map.get(stock_id, {})
                
                # 使用DataLoader获取股票详细信息（跨表业务）
                from app.data_loader import DataLoader
                data_loader = DataLoader(self.db_manager)
                stock_details = data_loader.get_stock_with_latest_price(stock_id) or {}
                
                # 调试：检查返回的数据
                if stock_details:
                    logger.debug(f"股票 {stock_id} 详细信息: {stock_details}")
                
                # 计算下一目标（使用 TargetCalculator）
                next_targets = None
                try:
                    from utils.db.tables.investment_trades.target_calculator import TargetCalculator
                    
                    # 获取操作记录
                    operations = operations_model.load_by_trade(trade['id'], order_by="date DESC")
                    
                    # 计算下一目标
                    next_targets = TargetCalculator.calculate_next_targets(
                        holding=holding,
                        current_price=current_price,
                        goal_config=trade.get('goal_config'),
                        operations=operations,
                        strategy_name=trade.get('strategy')
                    )
                except Exception as e:
                    logger.error(f"计算下一目标失败: {e}")
                
                result.append({
                    'id': trade['id'],
                    'stock_id': stock_id,
                    'stock_name': stock_info.get('name', ''),
                    'stock_industry': stock_info.get('industry', ''),
                    'stock_details': stock_details,
                    'strategy': trade.get('strategy', ''),
                    'status': trade.get('status', 'open'),
                    'note': trade.get('note', ''),
                    'created_at': trade.get('created_at'),
                    'holding': {
                        'amount': holding['amount'],
                        'avg_cost': holding['avg_cost'],
                        'total_cost': round(total_invested, 2),  # 当前投入金额
                        'first_buy_date': holding['first_buy_date'],
                        'first_buy_price': holding['first_buy_price']
                    },
                    'current_price': {
                        'price': current_price,
                        'date': current_price_date
                    },
                    'profit': {
                        'rate': round(profit_rate, 4),
                        'amount': round(profit_amount, 2)
                    },
                    'next_targets': next_targets
                })
            
            return jsonify({
                "success": True,
                "message": "获取成功",
                "data": result
            })
            
        except Exception as e:
            logger.error(f"获取持仓交易失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                "success": False,
                "message": f"获取失败: {str(e)}",
                "data": None
            }), 500

    def search_stocks(self, keyword: str):
        """
        搜索股票（用于自动完成）
        
        Args:
            keyword: 搜索关键词（股票代码或名称）
            
        Returns:
            dict: 股票列表
        """
        try:
            stock_model = self._get_stock_list_model()
            
            if not keyword or len(keyword) < 2:
                return jsonify({
                    "success": True,
                    "message": "关键词太短",
                    "data": []
                })
            
            # 搜索股票（按ID或名称）
            condition = "(id LIKE %s OR name LIKE %s) AND is_active = 1"
            params = (f"%{keyword}%", f"%{keyword}%")
            
            stocks = stock_model.load(condition, params, order_by="id", limit=20)
            
            result = [
                {
                    'id': stock['id'],
                    'name': stock['name'],
                    'industry': stock.get('industry', ''),
                    'type': stock.get('type', '')
                }
                for stock in stocks
            ]
            
            return jsonify({
                "success": True,
                "message": "获取成功",
                "data": result
            })
            
        except Exception as e:
            logger.error(f"搜索股票失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                "success": False,
                "message": f"搜索失败: {str(e)}",
                "data": None
            }), 500

    def get_trade_detail(self, trade_id: int):
        """
        获取单个交易详情（包含持仓、操作记录等）
        """
        try:
            trades_model = self._get_trades_model()
            operations_model = self._get_operations_model()
            stock_list_model = self._get_stock_list_model()
            kline_model = self._get_kline_model()
            
            # 获取交易详情
            trade = trades_model.load_one("id = %s", (trade_id,))
            if not trade:
                return jsonify({
                    "success": False,
                    "message": f"交易 {trade_id} 不存在",
                    "data": None
                }), 404
            
            # 获取股票名称
            stock_name = stock_list_model.load_name_by_id(trade['stock_id'])
            
            # 获取操作记录（降序，新的在前）
            operations = operations_model.load_by_trade(trade_id, order_by="date DESC")
            
            # 计算当前持仓
            holding = operations_model.get_current_holding(trade_id)
            
            # 获取最新价格
            latest_kline = kline_model.get_most_recent_one_by_term(trade['stock_id'], 'daily')
            current_price = float(latest_kline['close']) if latest_kline else 0
            
            # 计算收益
            if holding['avg_cost'] and current_price > 0:
                profit_rate = (current_price - holding['avg_cost']) / holding['avg_cost']
                profit_amount = (current_price - holding['avg_cost']) * holding['amount']
            else:
                profit_rate = 0
                profit_amount = 0
            
            return jsonify({
                "success": True,
                "message": "获取成功",
                "data": {
                    'id': trade['id'],
                    'stock_id': trade['stock_id'],
                    'stock_name': stock_name,
                    'strategy': trade.get('strategy', ''),
                    'status': trade.get('status', 'open'),
                    'note': trade.get('note', ''),
                    'created_at': trade.get('created_at'),
                    'operations': operations,
                    'holding': holding,
                    'current_price': current_price,
                    'profit': {
                        'rate': round(profit_rate, 4),
                        'amount': round(profit_amount, 2)
                    }
                }
            })
            
        except Exception as e:
            logger.error(f"获取交易详情失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                "success": False,
                "message": f"获取失败: {str(e)}",
                "data": None
            }), 500

    def get_trade_operations(self, trade_id: int):
        """
        根据trade_id获取所有操作记录
        """
        try:
            trades_model = self._get_trades_model()
            operations_model = self._get_operations_model()
            
            # 验证trade是否存在
            trade = trades_model.load_one("id = %s", (trade_id,))
            if not trade:
                return jsonify({
                    "success": False,
                    "message": f"交易 {trade_id} 不存在",
                    "data": None
                }), 404
            
            # 获取操作记录（降序，新的在前）
            operations = operations_model.load_by_trade(trade_id, order_by="date DESC")
            
            # 计算当前持仓
            holding = operations_model.get_current_holding(trade_id)
            
            return jsonify({
                "success": True,
                "message": "获取成功",
                "data": {
                    'trade': trade,
                    'operations': operations,
                    'holding': holding
                }
            })
            
        except Exception as e:
            logger.error(f"获取交易操作失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                "success": False,
                "message": f"获取失败: {str(e)}",
                "data": None
            }), 500

    def create_trade(self, data: dict):
        """
        创建一笔交易
        """
        try:
            trades_model = self._get_trades_model()
            
            # 验证必填字段
            if 'stock_id' not in data:
                return jsonify({
                    "success": False,
                    "message": "缺少必填字段: stock_id",
                    "data": None
                }), 400
            
            # 获取策略的goal配置快照
            goal_config = None
            if 'strategy' in data and data['strategy']:
                try:
                    import importlib.util
                    strategies_dir = os.path.join(project_root, 'app', 'analyzer', 'strategy')
                    strategy_path = os.path.join(strategies_dir, data['strategy'], 'settings.py')
                    
                    if os.path.exists(strategy_path):
                        spec = importlib.util.spec_from_file_location("settings", strategy_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        if hasattr(module, 'settings') and 'goal' in module.settings:
                            # 存储goal配置的快照
                            goal_config = json_lib.dumps(module.settings['goal'])
                except Exception as e:
                    logger.warning(f"读取策略goal配置失败: {e}")
            
            # 创建交易记录
            trade_data = {
                'stock_id': data['stock_id'],
                'strategy': data.get('strategy', ''),
                'status': 'open',
                'note': data.get('note', ''),
                'goal_config': goal_config
            }
            
            trades_model.insert_one(trade_data)
            
            # 返回创建的记录
            trade = trades_model.load_one("stock_id = %s", (data['stock_id'],), order_by="id DESC")
            
            return jsonify({
                "success": True,
                "message": "创建成功",
                "data": trade
            })
            
        except Exception as e:
            logger.error(f"创建交易失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                "success": False,
                "message": f"创建失败: {str(e)}",
                "data": None
            }), 500

    def create_operation(self, trade_id: int, data: dict):
        """
        创建一笔操作（买入/卖出/补仓）
        """
        try:
            trades_model = self._get_trades_model()
            operations_model = self._get_operations_model()
            
            # 验证trade是否存在
            trade = trades_model.load_one("id = %s", (trade_id,))
            if not trade:
                return jsonify({
                    "success": False,
                    "message": f"交易 {trade_id} 不存在",
                    "data": None
                }), 404
            
            # 验证必填字段
            required_fields = ['type', 'date', 'price', 'amount']
            for field in required_fields:
                if field not in data:
                    return jsonify({
                        "success": False,
                        "message": f"缺少必填字段: {field}",
                        "data": None
                    }), 400
            
            # 创建操作记录
            operation_data = {
                'trade_id': trade_id,
                'type': data['type'],
                'date': data['date'],
                'price': data['price'],
                'amount': data['amount'],
                'note': data.get('note', ''),
                'is_first': data.get('is_first', 0)  # 是否首次买入，默认为0
            }
            
            operations_model.insert_one(operation_data)
            
            # 重新计算持仓
            holding = operations_model.get_current_holding(trade_id)
            
            # 如果持仓为0，更新trade状态为closed
            if holding['amount'] == 0:
                trades_model.update({'status': 'closed'}, "id = %s", (trade_id,))
            
            # 返回创建的记录
            operation = operations_model.load_one("trade_id = %s", (trade_id,), order_by="id DESC")
            
            return jsonify({
                "success": True,
                "message": "创建成功",
                "data": {
                    'operation': operation,
                    'updated_holding': holding
                }
            })
            
        except Exception as e:
            logger.error(f"创建操作失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                "success": False,
                "message": f"创建失败: {str(e)}",
                "data": None
            }), 500

    def update_trade(self, trade_id: int, data: dict):
        """
        更新一笔交易
        """
        try:
            trades_model = self._get_trades_model()
            
            # 验证trade是否存在
            trade = trades_model.load_one("id = %s", (trade_id,))
            if not trade:
                return jsonify({
                    "success": False,
                    "message": f"交易 {trade_id} 不存在",
                    "data": None
                }), 404
            
            # 更新交易记录
            update_data = {}
            if 'strategy' in data:
                update_data['strategy'] = data['strategy']
            if 'note' in data:
                update_data['note'] = data['note']
            
            trades_model.update(update_data, "id = %s", (trade_id,))
            
            # 返回更新后的记录
            updated_trade = trades_model.load_one("id = %s", (trade_id,))
            
            return jsonify({
                "success": True,
                "message": "更新成功",
                "data": updated_trade
            })
            
        except Exception as e:
            logger.error(f"更新交易失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                "success": False,
                "message": f"更新失败: {str(e)}",
                "data": None
            }), 500

    def delete_trade(self, trade_id: int):
        """
        删除一笔交易（包括所有操作记录）
        """
        try:
            trades_model = self._get_trades_model()
            operations_model = self._get_operations_model()
            
            # 验证trade是否存在
            trade = trades_model.load_one("id = %s", (trade_id,))
            if not trade:
                return jsonify({
                    "success": False,
                    "message": f"交易 {trade_id} 不存在",
                    "data": None
                }), 404
            
            # 删除所有操作记录
            operations_model.delete("trade_id = %s", (trade_id,))
            
            # 删除交易记录
            trades_model.delete("id = %s", (trade_id,))
            
            return jsonify({
                "success": True,
                "message": "删除成功",
                "data": None
            })
            
        except Exception as e:
            logger.error(f"删除交易失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                "success": False,
                "message": f"删除失败: {str(e)}",
                "data": None
            }), 500

    def get_strategies_list(self):
        """
        获取可用策略列表
        
        Returns:
            dict: 策略列表
        """
        try:
            strategies = []
            strategies_dir = os.path.join(project_root, 'app', 'analyzer', 'strategy')
            
            if os.path.exists(strategies_dir):
                for item in os.listdir(strategies_dir):
                    item_path = os.path.join(strategies_dir, item)
                    if os.path.isdir(item_path) and not item.startswith('__'):
                        # 检查是否有settings.py
                        settings_file = os.path.join(item_path, 'settings.py')
                        if os.path.exists(settings_file):
                            # 读取策略配置获取名称
                            try:
                                import importlib.util
                                spec = importlib.util.spec_from_file_location("settings", settings_file)
                                module = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(module)
                                
                                strategy_name = module.settings.get('name', item) if hasattr(module, 'settings') else item
                                
                                strategies.append({
                                    'key': item,
                                    'name': strategy_name,
                                    'enabled': module.settings.get('is_enabled', False) if hasattr(module, 'settings') else False
                                })
                            except Exception as e:
                                logger.warning(f"读取策略 {item} 配置失败: {e}")
                                strategies.append({
                                    'key': item,
                                    'name': item,
                                    'enabled': False
                                })
            
            return jsonify({
                "success": True,
                "message": "获取成功",
                "data": strategies
            })
            
        except Exception as e:
            logger.error(f"获取策略列表失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                "success": False,
                "message": f"获取失败: {str(e)}",
                "data": None
            }), 500


    def update_operation(self, trade_id: int, operation_id: int, data: dict):
        """更新一笔操作（买入/卖出）"""
        try:
            trades_model = self._get_trades_model()
            operations_model = self._get_operations_model()
            
            trade = trades_model.load_one("id = %s", (trade_id,))
            if not trade:
                return jsonify({"success": False, "message": f"交易 {trade_id} 不存在", "data": None}), 404
            
            operation = operations_model.load_one("id = %s AND trade_id = %s", (operation_id, trade_id))
            if not operation:
                return jsonify({"success": False, "message": f"操作 {operation_id} 不存在", "data": None}), 404
            
            update_data = {k: v for k, v in data.items() if k in ['type', 'date', 'price', 'amount', 'note']}
            operations_model.update(update_data, "id = %s AND trade_id = %s", (operation_id, trade_id))
            
            holding = operations_model.get_current_holding(trade_id)
            status = 'closed' if holding['amount'] == 0 else 'open'
            trades_model.update({'status': status}, "id = %s", (trade_id,))
            
            updated_operation = operations_model.load_one("id = %s", (operation_id,))
            return jsonify({"success": True, "message": "更新成功", "data": {'operation': updated_operation, 'updated_holding': holding}})
        except Exception as e:
            logger.error(f"更新操作失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({"success": False, "message": f"更新失败: {str(e)}", "data": None}), 500

    def delete_operation(self, trade_id: int, operation_id: int):
        """删除一笔操作（买入/卖出）"""
        try:
            trades_model = self._get_trades_model()
            operations_model = self._get_operations_model()
            
            trade = trades_model.load_one("id = %s", (trade_id,))
            if not trade:
                return jsonify({"success": False, "message": f"交易 {trade_id} 不存在", "data": None}), 404
            
            operation = operations_model.load_one("id = %s AND trade_id = %s", (operation_id, trade_id))
            if not operation:
                return jsonify({"success": False, "message": f"操作 {operation_id} 不存在", "data": None}), 404
            
            if operation.get('is_first', 0) == 1:
                return jsonify({"success": False, "message": "不能删除首次买入操作", "data": None}), 400
            
            operations_model.delete("id = %s AND trade_id = %s", (operation_id, trade_id))
            
            holding = operations_model.get_current_holding(trade_id)
            status = 'closed' if holding['amount'] == 0 else 'open'
            trades_model.update({'status': status}, "id = %s", (trade_id,))
            
            return jsonify({"success": True, "message": "删除成功", "data": {'deleted_operation_id': operation_id, 'updated_holding': holding}})
        except Exception as e:
            logger.error(f"删除操作失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({"success": False, "message": f"删除失败: {str(e)}", "data": None}), 500

