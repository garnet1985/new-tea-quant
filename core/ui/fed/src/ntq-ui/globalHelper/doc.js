/** 图鉴用规范摘要（中文）。 */
const doc = {
  summary:
    '页面引导壳：遮罩 + 可选挖洞高亮 + 说明卡。展示层在 ntq-ui；路由匹配、文案目录与关闭账本在 containers/globalHelper。',
  params: [
    {
      name: 'hole',
      type: '{ left, top, width, height } | null',
      defaultValue: 'null',
      description: '挖洞矩形；null 时全屏 dim，不聚焦任何元素。',
    },
    {
      name: 'title / body / image',
      type: 'string | ReactNode',
      defaultValue: "''",
      description: '说明卡内容；文案里用「专有名词」会自动青色高亮。image 可选截图 URL。',
    },
    {
      name: 'stepLabel',
      type: 'string',
      defaultValue: "''",
      description: '多页时的「当前 / 总数」；单页可空。',
    },
    {
      name: 'isFirst / isLast',
      type: 'boolean',
      defaultValue: 'true',
      description: '控制上一步 / 下一页 / 我知道了。末页无「下一页」，只有「我知道了」。',
    },
    {
      name: 'onPrev / onNext / onClose',
      type: '() => void',
      defaultValue: '—',
      description: '上一步；下一页或末页确认；关闭（角标 X / Esc 由 Host 接）。',
    },
  ],
  scenarios: [
    '进页自动引导：containers Host + catalog help（可无 target = 不挖洞）。',
    '问号 FAB：GlobalHelperButton 重开当前路由的 enter help。',
    '图鉴：直接挂 Overlay 演示挖洞 / 无洞 / 按钮态。',
  ],
  antiPatterns: [
    '不要在 ntq-ui 里写死路由或 help 文案；文案进 containers/globalHelper/helps。',
    '不要同时放「跳过」和「下一页」——语义重复，只留「下一页」与末页「我知道了」。',
    '不要用硬编码色值；走 --ntq-* / --ui-*。',
  ],
};

export default doc;
