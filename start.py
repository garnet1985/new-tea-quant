#!/usr/bin/env python3
"""
股票分析应用主入口

使用示例：
    python start.py                      # 默认: simulate
    python start.py scan                 # 扫描投资机会
    python start.py simulate             # 模拟回测
    python start.py renew                # 更新数据
    python start.py analysis             # 分析结果
    
    python start.py -c                   # 快捷: 扫描
    python start.py -s                   # 快捷: 模拟
    python start.py -r -c -s             # 快捷: 更新→扫描→模拟
    
    python start.py renew scan simulate  # 完整: 全流程
    python start.py -h                   # 查看帮助
"""
import sys
import os
import argparse
from loguru import logger
import asyncio

# 在导入其他模块之前设置警告抑制
from utils.warning_suppressor import setup_warning_suppression
setup_warning_suppression()

from app.data_manager.data_manager import DataManager
from app.data_source.data_source_manager import DataSourceManager
from app.analyzer import Analyzer
from app.labeler import LabelerService
from utils.icon.icon_service import IconService


# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class App:
    def __init__(self, is_verbose: bool = False):
        self.is_verbose = is_verbose
        
        # 1. 首先初始化 DataManager（统一的数据访问入口）
        # DataManager 内部会创建和管理 DatabaseManager，并自动初始化
        self.data_manager = DataManager(is_verbose=self.is_verbose)
        
        # 2. 获取 DatabaseManager 实例（用于兼容旧模块）
        # 注意：这是过渡期方案，后续应该让这些模块也使用 DataManager 的接口
        # TODO: 逐步迁移以下模块使用 DataManager 而不是直接用 db：
        #   - DataSourceManager: 数据源管理（更新行情数据）
        #   - Analyzer: 策略分析器（扫描、模拟）
        #   - LabelerService: 标签服务（更新股票标签）
        self.db = self.data_manager.db
        
        # 3. 创建数据源和策略管理器
        # 注意：新的 DataSourceManager 使用新的框架，不再依赖 db
        # 但为了兼容，暂时保留 data_manager 参数
        self.data_source = DataSourceManager(data_manager=self.data_manager, is_verbose=self.is_verbose)
        self.analyzer = Analyzer(self.db, self.is_verbose)
        self.labeler = LabelerService(self.db)
        
        # 4. 初始化策略（这会注册表到数据库）
        self.analyzer.initialize()

    async def get_latest_market_open_day(self):
        """
        获取最新交易日
        
        Returns:
            str: 最新交易日（YYYYMMDD 格式）
        """
        # 使用 data_manager 的 TradingDateCache（更高效）
        return self.data_manager.get_latest_trading_date()
    
    async def renew_data(self, latest_market_open_day: str = None):
        """
        更新股票数据（使用新的 DataSourceManager）
        
        Args:
            latest_market_open_day: 最新交易日（可选，如果不提供则自动获取）
        """
        await self.data_source.renew_data(latest_market_open_day)
    
    def renew_labels(self, last_market_open_day: str, is_refresh: bool = False):
        """更新股票标签"""
        self.labeler.renew(last_market_open_day, is_refresh=is_refresh)
    
    def simulate(self):
        """运行模拟回测"""
        self.analyzer.simulate()

    def scan(self):
        """扫描投资机会"""
        self.analyzer.scan()

    def analysis(self, session_id: str = None):
        """分析所有策略的模拟结果"""
        self.analyzer.analysis(session_id)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='📊 股票分析应用 - 数据更新、扫描、模拟、分析',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
命令说明:
  scan        扫描投资机会（根据策略筛选当前符合条件的股票）
  simulate    模拟回测（使用历史数据测试策略表现）
  renew       更新数据（更新股票行情、标签等数据）
  analysis    分析结果（分析模拟回测的结果）

快捷缩写:
  -c          等同于 scan（Check opportunities）
  -s          等同于 simulate（Simulate backtest）
  -r          等同于 renew（Renew data）
  -a          等同于 analysis（Analysis results）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
使用示例:

  单一命令:
    %(prog)s                      默认运行 simulate
    %(prog)s scan                 扫描投资机会
    %(prog)s simulate             模拟回测
    %(prog)s renew                更新数据
    %(prog)s analysis             分析结果

  快捷方式:
    %(prog)s -c                   快速扫描
    %(prog)s -s                   快速模拟
    %(prog)s -r                   快速更新

  组合命令（按顺序执行）:
    %(prog)s renew scan           更新数据 → 扫描
    %(prog)s renew simulate       更新数据 → 模拟
    %(prog)s renew scan simulate  更新数据 → 扫描 → 模拟（全流程）
    
    %(prog)s -r -c                快捷: 更新 → 扫描
    %(prog)s -r -s                快捷: 更新 → 模拟
    %(prog)s -r -c -s             快捷: 全流程

  额外参数:
    %(prog)s simulate --strategy RTB    只运行指定策略
    %(prog)s analysis --session xxx     分析指定session
    %(prog)s -s -v                      详细输出模式

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        '''
    )
    
    # 位置参数（主命令）
    # 注意：choices 不能和 nargs='*' 一起用在空列表的情况，所以我们在后面验证
    parser.add_argument(
        'commands',
        nargs='*',
        help='要执行的命令（scan/simulate/renew/analysis），可以多个（按顺序执行）'
    )
    
    # 快捷flag（避免大小写混淆）
    parser.add_argument('-c', '--scan-flag', dest='scan_flag', action='store_true', 
                        help='扫描机会（scan）')
    parser.add_argument('-s', '--simulate-flag', dest='simulate_flag', action='store_true', 
                        help='模拟回测（simulate）')
    parser.add_argument('-r', '--renew-flag', dest='renew_flag', action='store_true', 
                        help='更新数据（renew）')
    parser.add_argument('-a', '--analysis-flag', dest='analysis_flag', action='store_true', 
                        help='分析结果（analysis）')
    
    # 额外参数
    parser.add_argument('--strategy', type=str, help='指定策略名称（用于 scan/simulate）')
    parser.add_argument('--session', type=str, help='指定session ID（用于 analysis）')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出模式')
    
    return parser.parse_args()


def build_command_pipeline(args):
    """构建命令执行流水线"""
    pipeline = []
    
    # 从位置参数构建
    if args.commands:
        # 验证命令有效性
        valid_commands = {'scan', 'simulate', 'renew', 'analysis'}
        for cmd in args.commands:
            if cmd not in valid_commands:
                logger.error(f"❌ 无效的命令: {cmd}")
                logger.info(f"有效命令: {', '.join(valid_commands)}")
                sys.exit(1)
        pipeline.extend(args.commands)
    
    # 从快捷flag构建
    flag_mapping = []
    if args.renew_flag:
        flag_mapping.append('renew')
    if args.scan_flag:
        flag_mapping.append('scan')
    if args.simulate_flag:
        flag_mapping.append('simulate')
    if args.analysis_flag:
        flag_mapping.append('analysis')
    
    # 合并（去重，保持顺序）
    for cmd in flag_mapping:
        if cmd not in pipeline:
            pipeline.append(cmd)
    
    # renew 总是最先执行
    if 'renew' in pipeline:
        pipeline.remove('renew')
        pipeline.insert(0, 'renew')
    
    # 默认行为：simulate
    if not pipeline:
        pipeline = ['simulate']
    
    return pipeline


async def execute_pipeline(app: App, pipeline: list, args):
    """执行命令流水线"""
    latest_market_open_day = None
    
    logger.info("=" * 60)
    logger.info(f"📋 执行计划: {' → '.join(pipeline)}")
    logger.info("=" * 60)
    
    for idx, command in enumerate(pipeline, 1):
        logger.info(f"")
        logger.info(f"▶️  [{idx}/{len(pipeline)}] 执行: {command}")
        logger.info("-" * 60)
        
        if command == 'renew':
            # 获取最新交易日
            if not latest_market_open_day:
                latest_market_open_day = await app.get_latest_market_open_day()
                logger.info(f"🔍 最新交易日: {latest_market_open_day}")
            
            # 更新股票数据
            logger.info("📥 更新股票行情数据...")
            await app.renew_data(latest_market_open_day)
            
            # 更新标签
            logger.info("🏷️  更新股票标签...")
            app.renew_labels(latest_market_open_day)
            
        elif command == 'scan':
            logger.info("🔍 扫描投资机会...")
            app.scan()
            
        elif command == 'simulate':
            logger.info("🎮 运行模拟回测...")
            app.simulate()
            
        elif command == 'analysis':
            logger.info("📊 分析模拟结果...")
            app.analysis(session_id=args.session)
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("✅ 全部完成！")
    logger.info("=" * 60)


def main():
    # 解析参数
    args = parse_args()
    
    # 构建命令流水线
    pipeline = build_command_pipeline(args)
    
    # 创建应用实例
    app = App(is_verbose=args.verbose)
    
    # 执行流水线
    try:
        asyncio.run(execute_pipeline(app, pipeline, args))
    except KeyboardInterrupt:
        logger.warning("\n⚠️  用户中断执行")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
