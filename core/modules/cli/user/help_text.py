"""CLI command reference (``cli.py -h`` help text template)."""

from __future__ import annotations

CLI_COMMAND_REFERENCE = """
规则:  xx=命令  -f/-n=全局开关  --xx=对象参数

  python cli.py                         先显示帮助，再显示版本（默认）  同 version / v / -v / --version
  python cli.py c                       扫描          同 scan [--strategy NAME] [--demo]
  python cli.py se                      机会盘点      同 strategy_enumerate [--strategy NAME]
  python cli.py sp                      价格因子模拟  同 strategy_price_factor [--strategy NAME]
  python cli.py so                      组合模拟      同 strategy_portfolio [--strategy NAME]
  python cli.py sd                      决策者 REPL   同 strategy_decision [--strategy NAME] [--version ID] [--session N] [--new-session]
  python cli.py sdl                     列出决策者会话 同 strategy_decision_list [--strategy NAME] [--version ID]
  python cli.py sdd --session N         删除一局决策者 同 strategy_decision_delete --session N
  python cli.py sim                     三层回测      同 strategy_simulate [--strategy NAME]（机会盘点 → 价格 → 资金；-f 忽略缓存重跑）
  python cli.py sea                     机会盘点层归因    同 strategy_attribute_enumerate [--strategy NAME]（须先 se；-f 忽略缓存）
  python cli.py spa                     价格层归因    同 strategy_attribute_price [--strategy NAME]（须先 sp）
  python cli.py soa                     组合层归因    同 strategy_attribute_portfolio [--strategy NAME]（须先 so）
  python cli.py sr                      滚动对照      同 strategy_rolling [--strategy NAME]（读 rolling.py；须先完成三层回测；-f 忽略缓存重跑）
  python cli.py sdv --strategy rsi_v1:3 删一份回测产物 同 strategy_delete_version（策略:版本）

  python cli.py r [SOURCE]              更新数据      同 renew [SOURCE]；list --json 为任务栏；--clear-logs 清已结束的运行状态
  python cli.py ls [RESOURCE]           列出选项      同 list；stock.* / datakeys / tags / tag.<key> / strategies / indicators / tables（单数别名可用）；--json
  python cli.py t                       执行标签      同 tag [--scenario NAME]
  python cli.py srel KEY                序列关系      同 series_relation KEY；--list 列出场景（无 UI）
  python cli.py a "你好"                助理对话      同 agent MESSAGE [--provider ID] [--session ID]
  python cli.py a --tools|--clear|--prefs|--settings|--remember RULE|--forget RULE|--set-provider ID|--set-context TEXT
  python cli.py ex [NAME]               导出策略包    同 export_strategy [NAME] [-o PATH]
  python cli.py im [PATH]               导入策略包    同 import_strategy [PATH] [--skip-existing] [--dry-run]
  python cli.py id                      导入演示数据  同 import_data（本地无 zip 则从官网下载；-f 重新下载并重导）
  python cli.py auth                    会员凭证      密码式输入写入；auth --status 查看；auth --clear 清除
  python cli.py u                       升级 core     同 update
  python cli.py v                       查看版本      同 version

  python cli.py -n PATH                 从模版新建策略到 PATH（userspace 内相对路径）
  python cli.py t -n PATH               从模版新建 Tag 到 PATH

  -f                                    全局：强制刷新 / 重算 / 覆盖
  -n PATH                               全局：从模版新建到 PATH
  --verbose                             开发日志（DEBUG，默认关闭）

  例: python cli.py sp -f --strategy demo/foo
      同 python cli.py strategy_price_factor -f --strategy demo/foo
""".strip()
