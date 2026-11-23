/** 制定策略列表页：`/strategy-design`（不含单策略工作台）。 */
export function matchStrategyList(pathname) {
  const path = String(pathname || '').replace(/\/+$/, '') || '/';
  return path === '/strategy-design';
}

export const STRATEGY_LIST_HELP = {
  id: 'strategy-list',
  version: 2,
  trigger: 'enter',
  match: matchStrategyList,
  steps: [
    {
      pages: [
        {
          title: '制定策略',
          body: '这里列出您用户空间里的全部策略。可以筛选归类、刷新本地新建项，或导入策略包；点「进入制定」打开工作台去调参与回测。',
        },
      ],
    },
    {
      target: 'strategy-list-table',
      pages: [
        {
          title: '策略表格',
          body: '这里是所有策略的表格，列出您用户空间里已有的策略。',
        },
      ],
    },
    {
      target: 'strategy-list-filter',
      pages: [
        {
          title: '归类过滤',
          body: '这里可以按归类快速过滤策略，点一下就能快速过滤出某一类策略。',
        },
      ],
    },
    {
      target: 'strategy-list-refresh-import',
      pages: [
        {
          title: '刷新与导入',
          body: '如果您在本地新建了一个策略，别忘了点刷新。也可以通过导入策略包来建立新的策略。',
        },
      ],
    },
    {
      target: 'strategy-list-enter',
      pages: [
        {
          title: '进入制定',
          body: '点「进入制定」打开该策略，可调参数、分步回测并对比版本；需要分享或备份时可以用旁边的「导出」。',
        },
      ],
    },
  ],
};
