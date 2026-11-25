const doc = {
  summary: '步骤条（回测视觉）。activeId 管当前选中；item.status 管执行态。可点击跳转（href / to+component / onClick）。进度环可用 showProgress 关掉。layout=spread 时等分铺满并与文案对齐。',
  params: [
    {
      name: 'items',
      type: 'StepperItem[]',
      defaultValue: '[]',
      description: '步骤列表。字段：id、label、status、progress?、no?、href?、to?、component?、onClick?、disabled?。',
    },
    {
      name: 'activeId',
      type: 'string | null',
      defaultValue: 'null',
      description: '当前选中步骤 id（激活态）。',
    },
    {
      name: 'layout',
      type: "'compact' | 'spread'",
      defaultValue: "'compact'",
      description: 'compact：固定间距内容宽（回测）；spread：等分铺满父宽，圆点与文案一对齐（安装引导）。',
    },
    {
      name: 'showLabels',
      type: 'boolean',
      defaultValue: 'false',
      description: '是否在圆点下方渲染 item.label。',
    },
    {
      name: 'showProgress',
      type: 'boolean',
      defaultValue: 'true',
      description: '是否在 running/pending 时画进度环；false 则退回 active/idle 圆点。',
    },
    {
      name: 'onItemClick',
      type: '(item, event) => void',
      defaultValue: 'undefined',
      description: '统一点击回调（与 item.onClick 可并存）。',
    },
    {
      name: 'aria-label',
      type: 'string',
      defaultValue: "'步骤'",
      description: '导航无障碍名。',
    },
  ],
  scenarios: [
    '回测四步：activeId + status=done/running，item.href 或 RouterLink。',
    '只要导航不关心执行：status 默认 idle，靠 activeId。',
    '暂不要环上进度：showProgress={false}。',
    '安装引导全宽对齐：layout="spread" showLabels。',
  ],
  antiPatterns: [
    '不要在 Stepper 内写死路由/会话；页面层拼 items。',
    '不要传入像素尺寸。',
    '禁止用本组件冒充 Tabs（页内切换用 Tabs）。',
    '不要在页面层再叠一层等分 label grid；用 showLabels。',
  ],
};

export default doc;
