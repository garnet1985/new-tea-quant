"""CLI command reference (``cli.py -h`` help text template)."""

from __future__ import annotations

CLI_COMMAND_REFERENCE = """
规则:  xx=命令  -f/-n=全局开关  --xx=对象参数

  python cli.py                         先显示帮助，再显示版本（默认）  同 version / v / -v / --version
  python cli.py c                       扫描          同 scan [--strategy NAME] [--demo]
  python cli.py se                      枚举          同 strategy_enumerate [--strategy NAME]
  python cli.py sp                      价格因子模拟  同 strategy_price_factor [--strategy NAME]
  python cli.py so                      组合模拟      同 strategy_portfolio [--strategy NAME]
  python cli.py s                       完整模拟链路  同 strategy_simulate

  python cli.py r [SOURCE]              更新数据      同 renew [SOURCE]
  python cli.py t                       执行标签      同 tag [--scenario NAME]
  python cli.py ex [NAME]               导出策略包    同 export_strategy [NAME] [-o PATH]
  python cli.py im [PATH]               导入策略包    同 import_strategy [PATH] [--skip-existing] [--dry-run]
  python cli.py id                      导入数据包    同 import_data（读 initialization/data 唯一 zip；-f 强制重导）
  python cli.py u                       升级 core     同 update
  python cli.py v                       查看版本      同 version

  python cli.py -n PATH                 从模版新建策略到 PATH（userspace 内相对路径）
  python cli.py t -n PATH               从模版新建 Tag 到 PATH

  -f                                    全局：强制刷新 / 重算 / 覆盖
  -n PATH                               全局：从模版新建到 PATH
  --verbose                             详细日志

  例: python cli.py sp -f --strategy demo/foo
      同 python cli.py strategy_price_factor -f --strategy demo/foo
""".strip()
