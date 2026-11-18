/** 序列关系列表：`/advanced/series-relation` */
export function matchSeriesRelationList(pathname) {
  const path = String(pathname || '').replace(/\/+$/, '') || '/';
  return path === '/advanced/series-relation';
}

export const SERIES_RELATION_LIST_HELP = {
  id: 'series-relation-list',
  version: 1,
  trigger: 'enter',
  match: matchSeriesRelationList,
  steps: [
    {
      pages: [
        {
          title: '序列关系',
          body: '「序列关系」用来看两条或多条曲线的相关度：是一起上升，还是一个升另一个降；形状是否相似，却总是一快一慢。用这个工具可以把这些关系直观对比出来。',
        },
      ],
    },
    {
      target: 'series-relation-list-refresh',
      pages: [
        {
          title: '刷新',
          body: '重新加载当前的序列关系场景列表而无需重启app。',
        },
      ],
    },
    {
      target: 'series-relation-list-create',
      pages: [
        {
          title: '新建',
          body: '创建一个新的序列关系场景，并找到和显示他们之间的关系。',
        },
      ],
    },
  ],
};
