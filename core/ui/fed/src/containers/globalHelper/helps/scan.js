/** 策略选股：`/scan` */
export function matchScan(pathname) {
  const path = String(pathname || '').replace(/\/+$/, '') || '/';
  return path === '/scan';
}

export const SCAN_HELP = {
  id: 'scan',
  version: 1,
  trigger: 'enter',
  match: matchScan,
  steps: [
    {
      target: 'scan-mode',
      pages: [
        {
          title: '扫描模式',
          body: '「严格模式」要求依赖数据已更新到最近交易日，否则会中断并提示缺口。「演示模式」会使用「数据设置」中假设的最新交易日进行扫描，便于在非实时数据下试用。',
        },
      ],
    },
    {
      target: 'scan-post-process',
      pages: [
        {
          title: '扫描后机会处理',
          body: '这里决定扫描到机会之后如何处理它们（例如通知、过滤、下单、喂给机器学习等）。可在「高级功能 → 扫描后机会处理」中配置和更改方案。',
        },
      ],
    },
    {
      target: 'scan-strategy-list',
      pages: [
        {
          title: '策略列表',
          body: '这里列出所有可以用于扫描机会的策略。一次只能扫描一个策略；运行中会禁用其它策略的「开始扫描」按钮。',
        },
      ],
    },
    {
      target: 'scan-start',
      pages: [
        {
          title: '开始扫描',
          body: '点击后会在当前最新数据中用该策略扫描机会并生成报告。结果会出现在表格对应行内，以及表格下方的「报告区」。',
        },
      ],
    },
  ],
};
