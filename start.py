#!/usr/bin/env python3
"""
股票分析应用主入口

使用示例：
    python start.py                      # 默认: simulate
    python start.py scan                 # 扫描投资机会
    python start.py simulate             # 模拟回测
    python start.py renew                # 更新数据
    python start.py analysis             # 分析结果
    python start.py tag                  # 执行所有标签场景
    python start.py tag --scenario xxx   # 执行指定标签场景
    
    python start.py -c                   # 快捷: 扫描（等价于: python start.py scan）
    python start.py -s                   # 快捷: 模拟（等价于: python start.py simulate）
    python start.py -r                   # 快捷: 更新（等价于: python start.py renew）
    python start.py -a                   # 快捷: 分析（等价于: python start.py analysis）
    python start.py -t                   # 快捷: 标签（等价于: python start.py tag）
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

from app.core_modules.data_manager import DataManager
from app.core_modules.data_source.data_source_manager import DataSourceManager
from app.analyzer import Analyzer
from app.core_modules.tag import TagManager
from utils.icon.icon_service import IconService


# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class App:
    def __init__(self, is_verbose: bool = False):
        self.is_verbose = is_verbose
        
        # 1. 首先初始化 DataManager（统一的数据访问入口）
        # DataManager 内部会创建和管理 DatabaseManager，并自动初始化
        self.data_manager = DataManager(is_verbose=self.is_verbose)
        
        # 2. 获取 DatabaseManager 实例（用于向后兼容，某些遗留代码可能仍需要直接访问 db）
        self.db = self.data_manager.db
        
        # 3. 创建数据源和策略管理器
        # 所有模块都接收 is_verbose 参数以控制日志详细程度
        self.data_source = DataSourceManager(is_verbose=self.is_verbose)
        self.analyzer = Analyzer(is_verbose=self.is_verbose)
        
        # 4. 初始化策略（这会注册表到数据库）
        self.analyzer.initialize()
        
        # 5. 初始化 TagManager（延迟初始化，只在需要时创建）
        self.tag_manager = None

    async def get_latest_completed_trading_date(self):
        """
        获取最新交易日
        
        Returns:
            str: 最新交易日（YYYYMMDD 格式）
        """
        # 使用 data_manager 的 TradingDateCache（更高效）
        return self.data_manager.get_latest_completed_trading_date()
    
    async def renew_data(
        self,
        latest_completed_trading_date: str = None,
        stock_list: list = None,
        test_mode: bool = False,
        dry_run: bool = False,
    ):
        """
        一站式更新行情 + 标签数据（由 DataSourceManager 统一调度）
        
        Args:
            latest_completed_trading_date: 最新交易日（可选）
            stock_list: 预先准备好的股票列表（可选，全局共用）
            test_mode: 测试模式，只处理少量股票
            dry_run: 干运行模式，只检查流程，不写入标签
        """
        await self.data_source.renew_data(
            latest_completed_trading_date=latest_completed_trading_date,
            stock_list=stock_list,
            test_mode=test_mode,
            dry_run=dry_run,
        )
    
    def simulate(self):
        """运行模拟回测"""
        self.analyzer.simulate()

    def scan(self):
        """扫描投资机会"""
        self.analyzer.scan()

    def analysis(self, session_id: str = None):
        """分析所有策略的模拟结果"""
        self.analyzer.analysis(session_id)
    
    def tag(self, scenario_name: str = None):
        """执行标签计算"""
        if self.tag_manager is None:
            self.tag_manager = TagManager(is_verbose=self.is_verbose)
        self.tag_manager.execute(scenario_name=scenario_name)


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
  tag         执行标签计算（计算并存储所有或指定场景的标签）

快捷缩写:
  -c          等同于 scan（Check opportunities）
  -s          等同于 simulate（Simulate backtest）
  -r          等同于 renew（Renew data）
  -a          等同于 analysis（Analysis results）
  -t          等同于 tag（Tag calculation）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
使用示例:

  单一命令:
    %(prog)s                      默认运行 simulate
    %(prog)s scan                 扫描投资机会
    %(prog)s simulate             模拟回测
    %(prog)s renew                更新数据
    %(prog)s analysis             分析结果
    %(prog)s tag                  执行所有标签场景
    %(prog)s tag --scenario xxx   执行指定标签场景

  快捷方式:
    %(prog)s -c                   快速扫描
    %(prog)s -s                   快速模拟
    %(prog)s -r                   快速更新
    %(prog)s -t                   快速标签

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
    %(prog)s tag --scenario xxx         执行指定标签场景
    %(prog)s -s -v                      详细输出模式

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        '''
    )
    
    # 位置参数（主命令）
    # 注意：choices 不能和 nargs='*' 一起用在空列表的情况，所以我们在后面验证
    parser.add_argument(
        'command',
        nargs='?',
        help='要执行的命令（scan/simulate/renew/analysis/tag），省略则默认 simulate'
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
    parser.add_argument('-t', '--tag-flag', dest='tag_flag', action='store_true', 
                        help='执行标签计算（tag）')
    
    # 额外参数
    parser.add_argument('--strategy', type=str, help='指定策略名称（用于 scan/simulate）')
    parser.add_argument('--session', type=str, help='指定session ID（用于 analysis）')
    parser.add_argument('--scenario', type=str, help='指定场景名称（用于 tag）')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出模式')
    
    return parser.parse_args()


def resolve_command(args) -> str:
    """
    解析本次运行要执行的“单个命令”。
    
    规则：
    - 位置参数 `command` 优先（scan/simulate/renew/analysis）
    - 否则根据快捷 flag (-c/-s/-r/-a) 决定
    - 如果同时给了多个互斥命令，报错退出
    - 如果都没给，默认 simulate
    """
    valid_commands = {'scan', 'simulate', 'renew', 'analysis', 'tag'}
    
    cmd_from_positional = None
    if args.command:
        if args.command not in valid_commands:
            logger.error(f"❌ 无效的命令: {args.command}")
            logger.info(f"有效命令: {', '.join(valid_commands)}")
            sys.exit(1)
        cmd_from_positional = args.command
    
    flags = []
    if args.renew_flag:
        flags.append('renew')
    if args.scan_flag:
        flags.append('scan')
    if args.simulate_flag:
        flags.append('simulate')
    if args.analysis_flag:
        flags.append('analysis')
    if args.tag_flag:
        flags.append('tag')
    
    # 如果位置参数和 flag 同时指定，并且不一致，则报错
    if cmd_from_positional and flags and cmd_from_positional not in flags:
        logger.error("❌ 命令冲突：位置参数和快捷 flag 指定了不同的命令")
        logger.info("请只使用一种方式指定命令，例如：`start.py renew` 或 `start.py -r`")
        sys.exit(1)
    
    # 如果通过 flag 指定了多个不同命令，也报错
    if not cmd_from_positional and len(set(flags)) > 1:
        logger.error("❌ 命令冲突：同时指定了多个快捷命令 (-c/-s/-r/-a)")
        logger.info("每次运行只能执行一个命令，请保留一个 flag 即可")
        sys.exit(1)
    
    if cmd_from_positional:
        return cmd_from_positional
    if flags:
        return flags[0]
    
    # 默认：simulate
    return 'simulate'


def main():
    # 解析参数
    args = parse_args()
    
    # 解析本次要执行的单个命令
    command = resolve_command(args)
    
    # 创建应用实例
    app = App(is_verbose=args.verbose)
    
    # 根据命令执行对应动作
    try:
        logger.info("=" * 60)
        logger.info(f"▶️  执行命令: {command}")
        logger.info("=" * 60)
        
        if command == 'renew':
            # latest_completed_trading_date 会在 renew_data() 内部统一获取，这里不再提前获取
            # 避免缓存过期数据，确保每次 renew 都使用最新的交易日
            asyncio.run(app.renew_data())
        elif command == 'scan':
            logger.info("🔍 扫描投资机会...")
            app.scan()
        elif command == 'simulate':
            logger.info("🎮 运行模拟回测...")
            app.simulate()
        elif command == 'analysis':
            logger.info("📊 分析模拟结果...")
            app.analysis(session_id=args.session)
        elif command == 'tag':
            logger.info("🏷️  执行标签计算...")
            app.tag(scenario_name=args.scenario)
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ 命令执行完成")
        logger.info("=" * 60)
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
