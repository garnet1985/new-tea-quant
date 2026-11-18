/** 后续处理：`/advanced/post-process` */
export function matchPostProcess(pathname) {
  const path = String(pathname || '').replace(/\/+$/, '') || '/';
  return path === '/advanced/post-process';
}

export const POST_PROCESS_HELP = {
  id: 'post-process',
  version: 1,
  trigger: 'enter',
  match: matchPostProcess,
  steps: [
    {
      pages: [
        {
          title: '后续处理',
          body: '这里管理策略扫描到机会之后，如何处理这些机会。机会的后续处理由「处理方案」和「执行单元」两部分组成。',
        },
      ],
    },
    {
      target: 'post-process-schemes',
      pages: [
        {
          title: '处理方案',
          body: '这里管理后续处理的执行方案：把多个执行单元按依赖组合成一套计划，扫描结束后会按启用的方案去跑。',
        },
      ],
    },
    {
      target: 'post-process-enabled',
      pages: [
        {
          title: '启用',
          body: '只有启用的后续处理方案才会真正执行；未启用的方案会保留配置，但扫描后不会跑。',
        },
      ],
    },
    {
      target: 'post-process-steps',
      pages: [
        {
          title: '包含的执行步骤',
          body: '当前方案里会按依赖执行的动作。绿色表示可用，黄色表示测试模式，红色表示缺配置、当前不可用。',
        },
      ],
    },
    {
      target: 'post-process-adapters',
      pages: [
        {
          title: '执行单元',
          body: '这里配置处理方案里用到的每个可执行单元，例如通知、展示、下单等；方案通过组合这些单元完成机会后续处理。',
        },
      ],
    },
  ],
};
