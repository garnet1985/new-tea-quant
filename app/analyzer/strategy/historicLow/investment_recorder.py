#!/usr/bin/env python3
"""
投资记录器 - 记录投资结算信息
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger

# 导入策略设置
try:
    from .strategy_settings import invest_settings
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    try:
        from app.analyzer.strategy.historicLow.strategy_settings import invest_settings
    except ImportError:
        # 如果都失败，使用默认值
        invest_settings = {
            "goal": {
                "win": 1.4,
                "loss": 0.85,
                "opportunityRange": 0.1,
                "kellyCriterionDivider": 5,
                "invest_reference_day_distance_threshold": 90
            },
            "terms": [60, 96],
            "min_required_monthly_records": 100
        }

class InvestmentRecorder:
    """投资记录器 - 记录投资结算信息"""
    
    def __init__(self, tmp_dir: str = "tmp"):
        """
        初始化投资记录器
        
        Args:
            tmp_dir: 临时文件夹路径
        """
        self.tmp_dir = tmp_dir
        self.current_session_dir = None
        self.meta_file = os.path.join(tmp_dir, "meta.json")
        
        # 确保tmp目录存在
        os.makedirs(tmp_dir, exist_ok=True)
        
        # 创建新的会话目录
        self._create_new_session()
    
    def _create_new_session(self):
        """创建新的会话目录"""
        # 获取当前日期
        current_date = datetime.now().strftime("%Y_%m_%d")
        
        # 从meta.json获取下一个ID
        next_id = self._get_next_session_id()
        
        # 创建会话名称
        session_name = f"{current_date}-{next_id:03d}"
        self.current_session_dir = os.path.join(self.tmp_dir, session_name)
        
        # 创建会话目录和子目录
        os.makedirs(self.current_session_dir, exist_ok=True)
        os.makedirs(os.path.join(self.current_session_dir, "success"), exist_ok=True)
        os.makedirs(os.path.join(self.current_session_dir, "fail"), exist_ok=True)
        os.makedirs(os.path.join(self.current_session_dir, "open"), exist_ok=True)
        
        # 更新meta.json
        self._update_meta_file(next_id, session_name)
        
        logger.info(f"📁 创建新的投资记录会话: {session_name}")
        
        # 创建会话信息文件
        session_info = {
            "session_id": next_id,
            "session_name": session_name,
            "created_at": datetime.now().isoformat(),
            "date": current_date,
            "description": "HistoricLow策略投资记录会话",
            "total_stocks_tested": 0,
            "investment_summary": {
                "total_investment_count": 0,
                "success_count": 0,
                "fail_count": 0,
                "open_count": 0,
                "win_rate": 0.0,
                "annual_return": 0.0,
                "avg_duration_days": 0.0,
                "avg_roi": 0.0,
                "total_investments": 0,
                "win_count": 0,
                "loss_count": 0
            },
            "strategy_settings": {
                "goal": invest_settings["goal"],
                "terms": invest_settings["terms"],
                "min_required_monthly_records": invest_settings["min_required_monthly_records"]
            }
        }
        
        session_info_file = os.path.join(self.current_session_dir, "session_info.json")
        with open(session_info_file, "w", encoding="utf-8") as f:
            json.dump(session_info, f, ensure_ascii=False, indent=2)
    
    def _get_next_session_id(self) -> int:
        """从meta.json获取下一个会话ID"""
        if not os.path.exists(self.meta_file):
            # 如果meta.json不存在，创建初始文件
            initial_meta = {
                "current_max_id": 0,
                "last_updated": datetime.now().isoformat(),
                "sessions": []
            }
            with open(self.meta_file, "w", encoding="utf-8") as f:
                json.dump(initial_meta, f, ensure_ascii=False, indent=2)
            return 1
        
        try:
            with open(self.meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            return meta.get("current_max_id", 0) + 1
        except Exception as e:
            logger.error(f"❌ 读取meta.json失败: {e}")
            return 1
    
    def _update_meta_file(self, session_id: int, session_name: str):
        """更新meta.json文件"""
        try:
            if os.path.exists(self.meta_file):
                with open(self.meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            else:
                meta = {
                    "current_max_id": 0,
                    "last_updated": datetime.now().isoformat(),
                    "sessions": []
                }
            
            # 更新最大ID
            meta["current_max_id"] = max(meta.get("current_max_id", 0), session_id)
            meta["last_updated"] = datetime.now().isoformat()
            
            # 添加新会话信息
            session_info = {
                "id": session_id,
                "name": session_name,
                "created_at": datetime.now().isoformat(),
                "path": self.current_session_dir
            }
            meta["sessions"].append(session_info)
            
            # 保存更新后的meta.json
            with open(self.meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"❌ 更新meta.json失败: {e}")
    
    def _convert_decimal(self, value):
        """转换Decimal类型为float，处理JSON序列化问题"""
        if value is None:
            return None
        try:
            # 如果是Decimal类型，转换为float
            if hasattr(value, '__float__'):
                return float(value)
            # 如果是字符串，尝试转换为float
            elif isinstance(value, str):
                return float(value)
            # 其他类型直接返回
            else:
                return value
        except (ValueError, TypeError):
            return value
    
    def record_investment_settlement(self, stock: Dict[str, Any], investment: Dict[str, Any], 
                                   result: str, exit_price: float, exit_date: str) -> None:
        """
        记录投资结算信息
        
        Args:
            stock: 股票基本信息
            investment: 投资数据
            result: 投资结果 ('win', 'loss', 'open')
            exit_price: 退出价格
            exit_date: 退出日期
        """
        try:
            # 获取股票代码和名称
            stock_code = stock.get('id', 'Unknown')
            stock_name = stock.get('name', 'Unknown')
            
            # 计算投资持续天数
            start_date = investment.get('invest_start_date')
            duration_days = None
            if start_date and exit_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y%m%d")
                    exit_dt = datetime.strptime(exit_date, "%Y%m%d")
                    duration_days = (exit_dt - start_dt).days
                except ValueError:
                    logger.warning(f"⚠️ 日期格式错误，无法计算持续天数: start_date={start_date}, exit_date={exit_date}")
            
            # 生成文件名
            file_name = f"{stock_code}_{exit_date}_{result}.json"
            
            # 根据结果选择子目录
            if result == 'win':
                sub_dir = "success"
            elif result == 'loss':
                sub_dir = "fail"
            elif result == 'open':
                sub_dir = "open"
            else:
                sub_dir = "unknown"
            
            file_path = os.path.join(self.current_session_dir, sub_dir, file_name)
            
            # 准备记录数据
            record_data = {
                "stock_info": {
                    "code": stock_code,
                    "name": stock_name,
                    "market": stock.get('market', '')
                },
                "investment_info": {
                    "start_date": start_date,
                    "purchase_price": self._convert_decimal(investment.get('goal', {}).get('purchase')),
                    "target_win": self._convert_decimal(investment.get('goal', {}).get('win')),
                    "target_loss": self._convert_decimal(investment.get('goal', {}).get('loss')),
                    "historic_low_ref": {
                        "date": investment.get('historic_low_ref', {}).get('lowest_date'),
                        "term": investment.get('historic_low_ref', {}).get('period_name'),
                        "lowest_price": self._convert_decimal(investment.get('historic_low_ref', {}).get('lowest_price'))
                    }
                },
                "settlement_info": {
                    "result": result,
                    "exit_price": exit_price,
                    "exit_date": exit_date,
                    "duration_days": duration_days,  # 添加投资持续天数
                    "profit_loss": (exit_price - self._convert_decimal(investment.get('goal', {}).get('purchase'))) if exit_price else None,
                    "profit_loss_rate": ((exit_price - self._convert_decimal(investment.get('goal', {}).get('purchase'))) / self._convert_decimal(investment.get('goal', {}).get('purchase')) * 100) if exit_price else None,
                    "settled_at": datetime.now().isoformat()
                }
            }
            
            # 保存到文件
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(record_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📊 已记录投资结算: {stock_code} {stock_name} - {result} -> {sub_dir}/{file_name}")
            
        except Exception as e:
            logger.error(f"❌ 记录投资结算失败: {e}")
    
    def get_session_info(self) -> Dict[str, Any]:
        """获取当前会话信息"""
        return {
            "session_dir": self.current_session_dir,
            "created_at": datetime.now().isoformat()
        }
    
    def update_session_summary(self, summary_data: Dict[str, Any]) -> None:
        """
        更新会话信息文件中的投资摘要
        
        Args:
            summary_data: 投资摘要数据
        """
        try:
            session_info_file = os.path.join(self.current_session_dir, "session_info.json")
            
            if os.path.exists(session_info_file):
                with open(session_info_file, "r", encoding="utf-8") as f:
                    session_info = json.load(f)
            else:
                session_info = {}
            
            # 更新投资摘要信息
            session_info["investment_summary"] = summary_data
            session_info["last_updated"] = datetime.now().isoformat()
            
            # 写回文件
            with open(session_info_file, "w", encoding="utf-8") as f:
                json.dump(session_info, f, ensure_ascii=False, indent=2)
                
            logger.info(f"📝 已更新会话摘要信息: {self.current_session_dir}")
            
        except Exception as e:
            logger.error(f"❌ 更新会话摘要失败: {e}")

    def update_session_info(self, update_data: Dict[str, Any]) -> None:
        """
        更新会话信息文件中的外层字段
        
        Args:
            update_data: 要更新的字段数据
        """
        try:
            session_info_file = os.path.join(self.current_session_dir, "session_info.json")
            
            if os.path.exists(session_info_file):
                with open(session_info_file, "r", encoding="utf-8") as f:
                    session_info = json.load(f)
            else:
                session_info = {}
            
            # 更新外层字段
            session_info.update(update_data)
            session_info["last_updated"] = datetime.now().isoformat()
            
            # 写回文件
            with open(session_info_file, "w", encoding="utf-8") as f:
                json.dump(session_info, f, ensure_ascii=False, indent=2)
                
            logger.info(f"📝 已更新会话信息: {self.current_session_dir}")
            
        except Exception as e:
            logger.error(f"❌ 更新会话信息失败: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """获取投资记录摘要"""
        if not self.current_session_dir:
            return {}
        
        # 统计各个子目录下的投资记录数量
        success_count = len([f for f in os.listdir(os.path.join(self.current_session_dir, "success")) if f.endswith('.json')]) if os.path.exists(os.path.join(self.current_session_dir, "success")) else 0
        fail_count = len([f for f in os.listdir(os.path.join(self.current_session_dir, "fail")) if f.endswith('.json')]) if os.path.exists(os.path.join(self.current_session_dir, "fail")) else 0
        open_count = len([f for f in os.listdir(os.path.join(self.current_session_dir, "open")) if f.endswith('.json')]) if os.path.exists(os.path.join(self.current_session_dir, "open")) else 0
        
        total_count = success_count + fail_count + open_count
        
        return {
            "session_dir": self.current_session_dir,
            "total_investment_count": total_count,
            "success_count": success_count,
            "fail_count": fail_count,
            "open_count": open_count,
            "created_at": datetime.now().isoformat()
        }
