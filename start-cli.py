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
import asyncio
import warnings
from loguru import logger

# ============================================================================
# 路径设置（必须在导入其他模块之前）
# ============================================================================
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ============================================================================
# 警告抑制（必须在导入第三方库之前）
# ============================================================================
def setup_warnings():
    """配置警告抑制"""
    warnings.filterwarnings('ignore', category=FutureWarning, module='tushare')
    warnings.filterwarnings('ignore', category=FutureWarning, message='.*fillna.*method.*')
    warnings.filterwarnings('ignore', category=FutureWarning, module='pandas')
    warnings.filterwarnings('ignore', category=DeprecationWarning, module='pandas')
    warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
    warnings.filterwarnings('ignore', category=DeprecationWarning, module='numpy')

setup_warnings()

# ============================================================================
# 导入应用模块
# ============================================================================
from core.modules.data_manager import DataManager
from core.modules.data_source.data_source_manager import DataSourceManager
from core.modules.tag import TagManager
from core.modules.strategy.components import PriceFactorSimulator
from core.modules.strategy.components.simulator.capital_allocation import CapitalAllocationSimulator


# ============================================================================
# 应用主类
# ============================================================================
class App:
    """股票分析应用主类"""
    
    def __init__(self, is_verbose: bool = False):
        """
        初始化应用
        
        Args:
            is_verbose: 是否启用详细日志
        """
        self.is_verbose = is_verbose
        
        # 初始化核心组件
        self.data_manager = DataManager(is_verbose=self.is_verbose)
        self.db = self.data_manager.db  # 向后兼容
        self.data_source = DataSourceManager(is_verbose=self.is_verbose)
        
        # 延迟初始化的组件
        self.tag_manager = None
    
    # ========================================================================
    # 数据更新相关
    # ========================================================================
    
    async def get_latest_completed_trading_date(self) -> str:
        """
        获取最新交易日
        
        Returns:
            str: 最新交易日（YYYYMMDD 格式）
        """
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
    
    # ========================================================================
    # 策略相关（暂时禁用）
    # ========================================================================
    
    def simulate(self):
        """运行模拟回测"""
        logger.warning("⚠️ simulate 功能暂时禁用，正在测试枚举器")
    
    def scan(self):
        """扫描投资机会"""
        logger.warning("⚠️ scan 功能暂时禁用，正在测试枚举器")
    
    def analysis(self, session_id: str = None):
        """分析所有策略的模拟结果"""
        logger.warning("⚠️ analysis 功能暂时禁用，正在测试枚举器")
    
    # ========================================================================
    # 标签相关
    # ========================================================================
    
    def tag(self, scenario_name: str = None):
        """
        执行标签计算
        
        Args:
            scenario_name: 场景名称（可选，不提供则执行所有场景）
        """
        if self.tag_manager is None:
            self.tag_manager = TagManager(is_verbose=self.is_verbose)
        self.tag_manager.execute(scenario_name=scenario_name)
    
    # ========================================================================
    # 枚举器相关
    # ========================================================================
    
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
        from core.modules.strategy.strategy_manager import StrategyManager
        from core.modules.strategy.components.opportunity_enumerator.enumerator_settings import OpportunityEnumeratorSettings
        from core.utils.date.date_utils import DateUtils
        
        # 1. 加载策略配置
        strategy_manager = StrategyManager()
        strategy_info = strategy_manager.strategy_cache.get(strategy_name)
        if not strategy_info:
            logger.error(f"策略不存在: {strategy_name}")
            return []
        
        settings = StrategySettings.from_dict(strategy_info['settings'])
        enum_settings = OpportunityEnumeratorSettings.from_base(settings)
        
        # 2. 获取股票列表
        all_stocks = self.data_manager.service.stock.list.load(filtered=True)
        stock_list = self._get_stock_list(
            all_stocks=all_stocks,
            settings=settings,
            enum_settings=enum_settings,
            stock_count=stock_count
        )
        
        # 3. 设置时间范围
        latest_date = self.data_manager.service.calendar.get_latest_completed_trading_date()
        start_date = settings.start_date or DateUtils.DEFAULT_START_DATE
        end_date = settings.end_date or latest_date
        
        logger.info(f"📅 时间范围: {start_date} ~ {end_date}")
        logger.info(f"📊 实际股票数量: {len(stock_list)}")
        
        # 4. 执行枚举
        summary_results = OpportunityEnumerator.enumerate(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            stock_list=stock_list,
            max_workers=enum_settings.max_workers
        )
        
        # 5. 显示结果
        self._display_enumerate_results(summary_results)
        
        return summary_results
    
    def _get_stock_list(self, all_stocks, settings, enum_settings, stock_count):
        """
        获取股票列表（采样或全量）
        
        Args:
            all_stocks: 所有股票列表
            settings: 策略设置
            enum_settings: 枚举器设置
            stock_count: 测试股票数量（可选）
        
        Returns:
            list: 股票代码列表
        """
        from core.modules.strategy.helper.stock_sampling_helper import StockSamplingHelper
        
        if enum_settings.use_sampling:
            if stock_count is not None:
                sampling_amount = stock_count
                sampling_config = {'strategy': 'continuous', 'continuous': {'start_idx': 0}}
                logger.info(f"🔍 开始枚举机会: strategy={settings.name}, stocks={stock_count} (采样模式)")
            else:
                sampling_amount = settings.sampling_amount
                sampling_config = settings.sampling_config
                logger.info(
                    f"🔍 开始枚举机会: strategy={settings.name}, "
                    f"sampling_amount={sampling_amount}, "
                    f"sampling_strategy={sampling_config.get('strategy')} (采样模式)"
                )
            
            stock_list = StockSamplingHelper.get_stock_list(
                all_stocks=all_stocks,
                sampling_amount=sampling_amount,
                sampling_config=sampling_config
            )
        else:
            stock_list = [s['id'] for s in all_stocks]
            logger.info(f"🔍 开始枚举机会: strategy={settings.name}, stocks={len(stock_list)} (全量枚举模式)")
        
        return stock_list
    
    def _display_enumerate_results(self, summary_results):
        """显示枚举结果"""
        if summary_results:
            total_opps = summary_results[0].get('opportunity_count', 0)
        else:
            total_opps = 0
        
        logger.info(f"✅ 枚举完成！找到 {total_opps} 个机会")
        
        if summary_results:
            logger.info("\n枚举结果概要:")
            for res in summary_results:
                logger.info(
                    f"  strategy={res.get('strategy_name')}, "
                    f"version={res.get('version_dir')}, "
                    f"opportunities={res.get('opportunity_count', 0)}, "
                    f"success_stocks={res.get('success_stocks', 0)}, "
                    f"failed_stocks={res.get('failed_stocks', 0)}"
                )
    
    # ========================================================================
    # 模拟器相关
    # ========================================================================
    
    def price_factor_simulate(self, strategy_name: str = 'example'):
        """
        基于 SOT 结果的价格因子回放模拟（PriceFactorSimulator）
        
        Args:
            strategy_name: 策略名称
        """
        logger.info(f"🎯 运行 PriceFactorSimulator, strategy={strategy_name}")
        simulator = PriceFactorSimulator(is_verbose=self.is_verbose)
        summary = simulator.run(strategy_name=strategy_name)
        if not summary:
            logger.warning("PriceFactorSimulator 未返回任何结果")
    
    def capital_allocation_simulate(self, strategy_name: str = 'example'):
        """
        基于 SOT 结果的资金分配模拟（CapitalAllocationSimulator）
        
        Args:
            strategy_name: 策略名称
        """
        logger.info(f"💰 运行 CapitalAllocationSimulator, strategy={strategy_name}")
        simulator = CapitalAllocationSimulator(is_verbose=self.is_verbose)
        summary = simulator.run(strategy_name=strategy_name)
        if not summary:
            logger.warning("CapitalAllocationSimulator 未返回任何结果")
    
    # ========================================================================
    # 工具方法
    # ========================================================================
    
    def export_adj_factor_csv(self, base_date: str = None):
        """
        手动导出复权因子事件季度 CSV
        
        Args:
            base_date: 基准日期（YYYYMMDD 或 YYYY-MM-DD），用于推断"上一个完整季度"
                      如果不提供，则使用当前日期所在季度的上一个季度
        """
        adj_model = self.data_manager.stock.kline._adj_factor_event
        file_name = adj_model.get_current_quarter_csv_name(base_date=base_date)
        file_path = os.path.join(adj_model.csv_dir, file_name)
        logger.info(f"📤 准备导出复权因子事件 CSV: {file_name}")
        exported = adj_model.export_to_csv(file_path=file_path)
        logger.info(f"✅ 手动导出复权因子事件 CSV 完成: {exported} 条记录 -> {file_path}")


# ============================================================================
# 命令行参数解析
# ============================================================================
def create_argument_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description='📊 股票分析应用 - 数据更新、扫描、模拟、分析',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_get_help_epilog()
    )
    
    # 位置参数（主命令）
    parser.add_argument(
        'command',
        nargs='?',
        help='要执行的命令（scan/simulate/renew/analysis/tag/enumerate/price_factor/capital_allocation/export_adj_factor_csv）'
    )
    
    # 快捷 flag
    _add_shortcut_flags(parser)
    
    # 额外参数
    _add_extra_arguments(parser)
    
    return parser


def _add_shortcut_flags(parser):
    """添加快捷 flag"""
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


def _add_extra_arguments(parser):
    """添加额外参数"""
    parser.add_argument('--strategy', type=str,
                       help='指定策略名称（用于 scan/simulate/enumerate）')
    parser.add_argument('--session', type=str,
                       help='指定session ID（用于 analysis）')
    parser.add_argument('--scenario', type=str,
                       help='指定场景名称（用于 tag）')
    parser.add_argument('--stocks', type=int, default=None,
                       help='测试股票数量（用于 enumerate，如果不提供则从 settings 读取）')
    parser.add_argument('--base-date', type=str,
                       help='基准日期（YYYYMMDD 或 YYYY-MM-DD，用于 export_adj_factor_csv）')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='详细输出模式')


def _get_help_epilog() -> str:
    """获取帮助信息的 epilog"""
    return '''
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

  额外参数:
    %(prog)s simulate --strategy RTB        只运行指定策略
    %(prog)s analysis --session xxx         分析指定session
    %(prog)s tag --scenario xxx             执行指定标签场景
    %(prog)s price_factor --strategy xx     使用 PriceFactorSimulator 对指定策略做因子回放
    %(prog)s -s -v                          详细输出模式

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    '''


def resolve_command(args) -> str:
    """
    解析本次运行要执行的命令
    
    Args:
        args: 解析后的命令行参数
    
    Returns:
        str: 要执行的命令名称
    
    Raises:
        SystemExit: 如果命令冲突或无效
    """
    valid_commands = {
        'scan', 'simulate', 'renew', 'analysis', 'tag',
        'enumerate', 'price_factor', 'capital_allocation', 'export_adj_factor_csv'
    }
    
    # 从位置参数获取命令
    cmd_from_positional = None
    if args.command:
        if args.command not in valid_commands:
            logger.error(f"❌ 无效的命令: {args.command}")
            logger.info(f"有效命令: {', '.join(sorted(valid_commands))}")
            sys.exit(1)
        cmd_from_positional = args.command
    
    # 从快捷 flag 获取命令
    flag_to_command = {
        'renew_flag': 'renew',
        'scan_flag': 'scan',
        'simulate_flag': 'simulate',
        'analysis_flag': 'analysis',
        'tag_flag': 'tag',
        'enumerate_flag': 'enumerate',
        'price_factor_flag': 'price_factor',
    }
    
    flags = [flag_to_command[k] for k, v in flag_to_command.items() if getattr(args, k, False)]
    
    # 验证命令一致性
    if cmd_from_positional and flags and cmd_from_positional not in flags:
        logger.error("❌ 命令冲突：位置参数和快捷 flag 指定了不同的命令")
        logger.info("请只使用一种方式指定命令，例如：`start.py renew` 或 `start.py -r`")
        sys.exit(1)
    
    if not cmd_from_positional and len(set(flags)) > 1:
        logger.error("❌ 命令冲突：同时指定了多个快捷命令 (-c/-s/-r/-a)")
        logger.info("每次运行只能执行一个命令，请保留一个 flag 即可")
        sys.exit(1)
    
    # 返回命令（优先位置参数，其次 flag，最后默认值）
    if cmd_from_positional:
        return cmd_from_positional
    if flags:
        return flags[0]
    
    # 默认：simulate
    return 'simulate'


# ============================================================================
# 命令执行器
# ============================================================================
class CommandExecutor:
    """命令执行器"""
    
    def __init__(self, app: App):
        """
        初始化命令执行器
        
        Args:
            app: 应用实例
        """
        self.app = app
        self.command_handlers = self._build_command_handlers()
    
    def _build_command_handlers(self) -> dict:
        """构建命令处理器映射"""
        return {
            'renew': self._handle_renew,
            'scan': self._handle_scan,
            'simulate': self._handle_simulate,
            'analysis': self._handle_analysis,
            'tag': self._handle_tag,
            'enumerate': self._handle_enumerate,
            'price_factor': self._handle_price_factor,
            'capital_allocation': self._handle_capital_allocation,
            'export_adj_factor_csv': self._handle_export_adj_factor_csv,
        }
    
    def execute(self, command: str, args):
        """
        执行命令
        
        Args:
            command: 命令名称
            args: 命令行参数
        """
        handler = self.command_handlers.get(command)
        if not handler:
            logger.error(f"❌ 未知命令: {command}")
            sys.exit(1)
        
        handler(args)
    
    def _handle_renew(self, args):
        """处理 renew 命令"""
        logger.info("🔄 更新数据...")
        asyncio.run(self.app.renew_data())
    
    def _handle_scan(self, args):
        """处理 scan 命令"""
        logger.info("🔍 扫描投资机会...")
        self.app.scan()
    
    def _handle_simulate(self, args):
        """处理 simulate 命令"""
        logger.info("🎮 运行模拟回测...")
        self.app.simulate()
    
    def _handle_analysis(self, args):
        """处理 analysis 命令"""
        logger.info("📊 分析模拟结果...")
        self.app.analysis(session_id=args.session)
    
    def _handle_tag(self, args):
        """处理 tag 命令"""
        logger.info("🏷️  执行标签计算...")
        self.app.tag(scenario_name=args.scenario)
    
    def _handle_enumerate(self, args):
        """处理 enumerate 命令"""
        logger.info("🔢 枚举投资机会...")
        strategy = args.strategy or 'example'
        self.app.enumerate(strategy_name=strategy, stock_count=args.stocks)
    
    def _handle_price_factor(self, args):
        """处理 price_factor 命令"""
        logger.info("🎯 运行价格因子回放模拟 (PriceFactorSimulator)...")
        strategy = args.strategy or 'example'
        self.app.price_factor_simulate(strategy_name=strategy)
    
    def _handle_capital_allocation(self, args):
        """处理 capital_allocation 命令"""
        logger.info("💰 运行资金分配模拟 (CapitalAllocationSimulator)...")
        strategy = args.strategy or 'example'
        self.app.capital_allocation_simulate(strategy_name=strategy)
    
    def _handle_export_adj_factor_csv(self, args):
        """处理 export_adj_factor_csv 命令"""
        logger.info("📤 手动导出复权因子事件季度 CSV...")
        self.app.export_adj_factor_csv(base_date=args.base_date)


# ============================================================================
# 主函数
# ============================================================================
def main():
    """主函数"""
    # 解析参数
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # 解析命令
    command = resolve_command(args)
    
    # 创建应用实例
    app = App(is_verbose=args.verbose)
    
    # 执行命令
    try:
        logger.info("=" * 60)
        logger.info(f"▶️  执行命令: {command}")
        logger.info("=" * 60)
        
        executor = CommandExecutor(app)
        executor.execute(command, args)
        
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
