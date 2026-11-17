const doc = {
  summary: '全页背景图 + 遮罩。从内置图库随机选一张；无图时不渲染。挂在壳层，不进业务页。',
  params: [
    {
      name: '（无 props）',
      type: '—',
      defaultValue: '—',
      description: 'URL 由 pageBackgroundCatalog 随机；通过 CSS 变量 --ntq-page-bg-url 注入。',
    },
  ],
  scenarios: [
    '应用壳层（App / PageLayout）一次挂载。',
  ],
  antiPatterns: [
    '不要在每个业务页各自再挂一份。',
    '不要在业务里硬编码背景图 URL。',
  ],
};

export default doc;
