/** 特征标签列表：`/advanced/tags` */
export function matchTagList(pathname) {
  const path = String(pathname || '').replace(/\/+$/, '') || '/';
  return path === '/advanced/tags';
}

export const TAG_LIST_HELP = {
  id: 'tag-list',
  version: 2,
  trigger: 'enter',
  match: matchTagList,
  steps: [
    {
      pages: [
        {
          title: '特征标签',
          body: '「标签」用来对任意数据进行分类、切割与标记。标签一旦定义并计算过，就可以在任何回测中直接引用使用。',
        },
      ],
    },
    {
      target: 'tag-list-filter',
      pages: [
        {
          title: '按归类筛选',
          body: '当前标签的分类，点击后可以按照分类过滤相应的标签。分类对应标签代码设置 settings.py 里的「meta.category」字段。',
        },
      ],
    },
    {
      target: 'tag-list-data-key',
      pages: [
        {
          title: '贴标对象',
          body: '表明当前的标签是贴给谁的，对象是一个数据契约名。',
        },
      ],
    },
    {
      target: 'tag-list-status',
      pages: [
        {
          title: '数据状态',
          body: '这里可以看到当前标签是否已经依据了最新的数据，是不是需要更新。',
        },
      ],
    },
    {
      target: 'tag-list-run',
      pages: [
        {
          title: '开始计算',
          body: '点击运行按钮开始计算该标签场景。系统忙时仍可加入全局管道队列，当前任务结束后会自动执行。',
        },
      ],
    },
    {
      target: 'tag-list-update-mode',
      pages: [
        {
          title: '更新方式',
          body: '这里说明该标签如何记录与更新结果，例如「增量」或「刷新」，决定再次运行时怎么写回计算结果。',
        },
      ],
    },
    {
      target: 'tag-list-definitions',
      pages: [
        {
          title: '可产生的标签',
          body: '当前场景计算后会产出哪些具体标签名。',
        },
      ],
    },
    {
      target: 'tag-list-visualize',
      pages: [
        {
          title: '可视化',
          body: '对已计算的标签做可视化展示；不同类型的标签会用不同的呈现方式。尚未计算过的场景无法打开可视化。',
        },
      ],
    },
  ],
};
