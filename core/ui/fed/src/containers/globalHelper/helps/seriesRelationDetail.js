/** 序列关系内页：`/advanced/series-relation/:key` */
export function matchSeriesRelationDetail(pathname) {
  const path = String(pathname || '').replace(/\/+$/, '') || '/';
  const prefix = '/advanced/series-relation/';
  if (!path.startsWith(prefix)) return false;
  return Boolean(path.slice(prefix.length));
}

export const SERIES_RELATION_DETAIL_HELP = {
  id: 'series-relation-detail',
  version: 1,
  trigger: 'enter',
  match: matchSeriesRelationDetail,
  steps: [
    {
      target: 'series-relation-detail-globals',
      pages: [
        {
          title: '对比参数',
          body: '这一栏用来配置对比数据的时间段、归一方式，以及缺失值的填充方式。',
        },
      ],
    },
    {
      target: 'series-relation-detail-series',
      pages: [
        {
          title: '对比系列',
          body: '这里列出要对齐对比的数据系列。可追加行情 / 宏观契约或策略回测曲线，并分别编辑。',
        },
      ],
    },
    {
      target: 'series-relation-detail-run',
      pages: [
        {
          title: '执行',
          body: '配置完成后点这里开始计算序列关系；运行前会自动保存当前配置，结果会出现在下方报告区。',
        },
      ],
    },
  ],
};
