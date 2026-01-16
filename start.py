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
    python start.py enumerate            # 枚举投资机会（测试用）
    python start.py price_factor         # 价格因子回放模拟（基于 SOT 结果）
    python start.py capital_allocation   # 资金分配模拟（基于 SOT 结果，真实资金约束）
    
    python start.py -c                   # 快捷: 扫描（等价于: python start.py scan）
    python start.py -s                   # 快捷: 模拟（等价于: python start.py simulate）
    python start.py -r                   # 快捷: 更新（等价于: python start.py renew）
    python start.py -a                   # 快捷: 分析（等价于: python start.py analysis）
    python start.py -t                   # 快捷: 标签（等价于: python start.py tag）
    python start.py -e                   # 快捷: 枚举（等价于: python start.py enumerate）
    python start.py -h                   # 查看帮助
"""
import sys
import os
import argparse
from loguru import logger
import asyncio

# 在导入其他模块之前设置警告抑制
# 警告抑制（直接使用 warnings 模块）
import warnings
warnings.filterwarnings('ignore', category=FutureWarning, module='tushare')
warnings.filterwarnings('ignore', category=FutureWarning, message='.*fillna.*method.*')
warnings.filterwarnings('ignore', category=FutureWarning, module='pandas')
warnings.filterwarnings('ignore', category=DeprecationWarning, module='pandas')
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
warnings.filterwarnings('ignore', category=DeprecationWarning, module='numpy')

from core.modules.data_manager import DataManager
from core.modules.data_source.data_source_manager import DataSourceManager
# from core.modules.analyzer_legacy.analyzer import Analyzer  # 暂时注释，测试枚举器
from core.modules.tag import TagManager
from core.utils.icon.icon_service import IconService
from core.modules.strategy.components import PriceFactorSimulator
from core.modules.strategy.components.simulator.capital_allocation import CapitalAllocationSimulator


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
        # self.analyzer = Analyzer(is_verbose=self.is_verbose)  # 暂时注释
        
        # 4. 初始化策略（这会注册表到数据库）
        # self.analyzer.initialize()  # 暂时注释
        
        # 5. 初始化 TagManager（延迟初始化，只在需要时创建）
        self.tag_manager = None

    async def get_latest_completed_trading_date(self):
        """
        获取最新交易日
        
        Returns:
            str: 最新交易日（YYYYMMDD 格式）
        """
        # 使用 data_manager 的 TradingDateCache（更高效）
        return self.data_manager.service.calendar.get_latest_completed_trading_date()
    
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
        # self.analyzer.simulate()  # 暂时注释
        logger.warning("⚠️ simulate 功能暂时禁用，正在测试枚举器")

    def scan(self):
        """扫描投资机会"""
        # self.analyzer.scan()  # 暂时注释
        logger.warning("⚠️ scan 功能暂时禁用，正在测试枚举器")

    def analysis(self, session_id: str = None):
        """分析所有策略的模拟结果"""
        # self.analyzer.analysis(session_id)  # 暂时注释
        logger.warning("⚠️ analysis 功能暂时禁用，正在测试枚举器")
    
    def tag(self, scenario_name: str = None):
        """执行标签计算"""
        if self.tag_manager is None:
            self.tag_manager = TagManager(is_verbose=self.is_verbose)
        self.tag_manager.execute(scenario_name=scenario_name)

    def price_factor_simulate(self, strategy_name: str = 'example'):
        """
        基于 SOT 结果的价格因子回放模拟（PriceFactorSimulator）
        
        - 输入：opportunity_enumerator 的 SOT 版本（由 userspace settings 决定）
        - 行为：对每只股票按机会时间轴做 1 股级机会回放，统计因子/信号质量
        """
        logger.info(f"🎯 运行 PriceFactorSimulator, strategy={strategy_name}")
        simulator = PriceFactorSimulator(is_verbose=self.is_verbose)
        summary = simulator.run(strategy_name=strategy_name)
        if not summary:
            logger.warning("PriceFactorSimulator 未返回任何结果")
            return

    def capital_allocation_simulate(self, strategy_name: str = 'example'):
        """
        基于 SOT 结果的资金分配模拟（CapitalAllocationSimulator）
        
        - 输入：opportunity_enumerator 的 SOT 版本（由 userspace settings 决定）
        - 行为：在真实资金约束下，对枚举器 SOT 结果进行全市场回放，维护全局账户和持仓
        """
        logger.info(f"💰 运行 CapitalAllocationSimulator, strategy={strategy_name}")
        simulator = CapitalAllocationSimulator(is_verbose=self.is_verbose)
        summary = simulator.run(strategy_name=strategy_name)
        if not summary:
            logger.warning("CapitalAllocationSimulator 未返回任何结果")
            return
    
    def enumerate(self, strategy_name: str = 'example', stock_count: int = None):
        """
        枚举投资机会
        
        Args:
            strategy_name: 策略名称
            stock_count: 测试股票数量（可选，如果不提供则从 settings 读取）
        """
        from core.modules.strategy.components.opportunity_enumerator import OpportunityEnumerator
        from core.modules.strategy.models.strategy_settings import StrategySettings
        from core.modules.strategy.helper.stock_sampling_helper import StockSamplingHelper
        
        # 1. 加载策略配置
        from core.modules.strategy.strategy_manager import StrategyManager
        strategy_manager = StrategyManager()
        strategy_info = strategy_manager.strategy_cache.get(strategy_name)
        if not strategy_info:
            logger.error(f"策略不存在: {strategy_name}")
            return []
        
        settings = StrategySettings.from_dict(strategy_info['settings'])
        
        # 2. 获取枚举器设置
        from core.modules.strategy.components.opportunity_enumerator.enumerator_settings import OpportunityEnumeratorSettings
        enum_settings = OpportunityEnumeratorSettings.from_base(settings)
        use_sampling = enum_settings.use_sampling
        max_workers = enum_settings.max_workers
        
        # 3. 获取股票列表（根据 use_sampling 决定使用采样还是全量）
        all_stocks = self.data_manager.service.stock.list.load(filtered=True)  # 加载所有活跃股票（已过滤）
        
        if use_sampling:
            # 采样模式：使用 sampling 配置进行采样
            # 如果提供了 stock_count 参数，优先使用（用于测试）
            if stock_count is not None:
                sampling_amount = stock_count
                sampling_config = {'strategy': 'continuous', 'continuous': {'start_idx': 0}}
                logger.info(f"🔍 开始枚举机会: strategy={strategy_name}, stocks={stock_count} (采样模式)")
            else:
                # 从 settings 读取采样配置
                sampling_amount = settings.sampling_amount
                sampling_config = settings.sampling_config
                logger.info(f"🔍 开始枚举机会: strategy={strategy_name}, sampling_amount={sampling_amount}, sampling_strategy={sampling_config.get('strategy')} (采样模式)")
            
            # 使用 StockSamplingHelper 获取股票列表
            stock_list = StockSamplingHelper.get_stock_list(
                all_stocks=all_stocks,
                sampling_amount=sampling_amount,
                sampling_config=sampling_config
            )
        else:
            # 全量模式：使用全量股票列表
            stock_list = [s['id'] for s in all_stocks]
            logger.info(f"🔍 开始枚举机会: strategy={strategy_name}, stocks={len(stock_list)} (全量枚举模式)")
        
        logger.info(f"📊 实际股票数量: {len(stock_list)}")
        
        # 4. 设置时间范围（从 settings 读取，如果没有则使用默认值）
        latest_date = self.data_manager.service.calendar.get_latest_completed_trading_date()
        start_date = settings.start_date or ''
        
        # 如果 start_date 为空，使用默认开始日期
        if not start_date:
            from core.utils.date.date_utils import DateUtils
            start_date = DateUtils.DEFAULT_START_DATE
        
        end_date = settings.end_date or latest_date
        
        logger.info(f"📅 时间范围: {start_date} ~ {end_date}")
        
        # 5. 枚举所有机会（返回 summary，而不是全量机会列表）
        summary_results = OpportunityEnumerator.enumerate(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            stock_list=stock_list,
            max_workers=max_workers  # 从枚举器设置读取
        )
        
        # 按当前设计，enumerator 返回的是 summary 列表，每个元素是一次 run 的概要信息
        if summary_results:
            total_opps = summary_results[0].get('opportunity_count', 0)
        else:
            total_opps = 0

        logger.info(f"✅ 枚举完成！找到 {total_opps} 个机会")

        # 显示概要信息（版本目录等），不再尝试打印具体机会字段
        if summary_results:
            logger.info(f"\n枚举结果概要:")
            for res in summary_results:
                logger.info(
                    f"  strategy={res.get('strategy_name')}, "
                    f"version={res.get('version_dir')}, "
                    f"opportunities={res.get('opportunity_count', 0)}, "
                    f"success_stocks={res.get('success_stocks', 0)}, "
                    f"failed_stocks={res.get('failed_stocks', 0)}"
                )
        
        return summary_results

    def export_adj_factor_csv(self, base_date: str = None):
        """
        手动导出复权因子事件季度 CSV。
        
        - base_date: 基准日期（YYYYMMDD 或 YYYY-MM-DD），用于推断“上一个完整季度”
                     如果不提供，则使用当前日期所在季度的上一个季度。
        """
        adj_model = self.data_manager.stock.kline._adj_factor_event
        file_name = adj_model.get_current_quarter_csv_name(base_date=base_date)
        file_path = os.path.join(adj_model.csv_dir, file_name)
        logger.info(f"📤 准备导出复权因子事件 CSV: {file_name}")
        exported = adj_model.export_to_csv(file_path=file_path)
        logger.info(f"✅ 手动导出复权因子事件 CSV 完成: {exported} 条记录 -> {file_path}")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='📊 股票分析应用 - 数据更新、扫描、模拟、分析',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
命令说明:
  scan                 扫描投资机会（根据策略筛选当前符合条件的股票）
  simulate             模拟回测（使用历史数据测试策略表现）
  renew                更新数据（更新股票行情、标签等数据）
  analysis             分析结果（分析模拟回测的结果）
  tag                  执行标签计算（计算并存储所有或指定场景的标签）
  enumerate            枚举投资机会（测试用，枚举所有可能的机会）
  price_factor         价格因子回放模拟（基于 SOT 机会结果）
  capital_allocation   资金分配模拟（基于 SOT 机会结果，真实资金约束）
  export_adj_factor_csv 手动导出复权因子事件季度 CSV

快捷缩写:
  -c           等同于 scan（Check opportunities）
  -s           等同于 simulate（Simulate backtest）
  -r           等同于 renew（Renew data）
  -a           等同于 analysis（Analysis results）
  -t           等同于 tag（Tag calculation）
  -e           等同于 enumerate（Enumerate opportunities）
  -p           等同于 price_factor（PriceFactorSimulator）

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
    %(prog)s simulate --strategy RTB        只运行指定策略
    %(prog)s analysis --session xxx         分析指定session
    %(prog)s tag --scenario xxx             执行指定标签场景
    %(prog)s price_factor --strategy xx     使用 PriceFactorSimulator 对指定策略做因子回放
    %(prog)s -s -v                          详细输出模式

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        '''
    )
    
    # 位置参数（主命令）
    # 注意：choices 不能和 nargs='*' 一起用在空列表的情况，所以我们在后面验证
    parser.add_argument(
        'command',
        nargs='?',
        help='要执行的命令（scan/simulate/renew/analysis/tag/enumerate/price_factor/capital_allocation/export_adj_factor_csv），省略则默认 simulate'
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
    parser.add_argument('-e', '--enumerate-flag', dest='enumerate_flag', action='store_true', 
                        help='枚举投资机会（enumerate）')
    parser.add_argument('-p', '--price-factor-flag', dest='price_factor_flag', action='store_true',
                        help='运行价格因子回放模拟（price_factor）')
    
    # 额外参数
    parser.add_argument('--strategy', type=str, help='指定策略名称（用于 scan/simulate/enumerate）')
    parser.add_argument('--session', type=str, help='指定session ID（用于 analysis）')
    parser.add_argument('--scenario', type=str, help='指定场景名称（用于 tag）')
    parser.add_argument('--stocks', type=int, default=None, help='测试股票数量（用于 enumerate，如果不提供则从 settings 读取）')
    parser.add_argument('--base-date', type=str, help='基准日期（YYYYMMDD 或 YYYY-MM-DD，用于 export_adj_factor_csv）')
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
    valid_commands = {'scan', 'simulate', 'renew', 'analysis', 'tag', 'enumerate', 'price_factor', 'capital_allocation'}
    
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
    if args.enumerate_flag:
        flags.append('enumerate')
    if getattr(args, 'price_factor_flag', False):
        flags.append('price_factor')
    
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
        elif command == 'enumerate':
            logger.info("🔢 枚举投资机会...")
            strategy = args.strategy or 'example'
            app.enumerate(strategy_name=strategy, stock_count=args.stocks)
        elif command == 'price_factor':
            logger.info("🎯 运行价格因子回放模拟 (PriceFactorSimulator)...")
            strategy = args.strategy or 'example'
            app.price_factor_simulate(strategy_name=strategy)
        elif command == 'capital_allocation':
            logger.info("💰 运行资金分配模拟 (CapitalAllocationSimulator)...")
            strategy = args.strategy or 'example'
            app.capital_allocation_simulate(strategy_name=strategy)
        elif command == 'export_adj_factor_csv':
            logger.info("📤 手动导出复权因子事件季度 CSV...")
            app.export_adj_factor_csv(base_date=args.base_date)
        
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
