const doc = {
  summary: '图表壳：标题 / tip / note + ECharts。只渲染上层拼好的 option；K 线与业务 series 不进本组件。',
  params: [
    {
      name: 'title',
      type: 'ReactNode',
      defaultValue: 'undefined',
      description: '图标题；省略则无标题行。',
    },
    {
      name: 'tip',
      type: 'ReactNode',
      defaultValue: 'undefined',
      description: '标题旁 HelpTooltip。',
    },
    {
      name: 'note',
      type: 'ReactNode',
      defaultValue: 'undefined',
      description: '标题下的次要说明。',
    },
    {
      name: 'option',
      type: 'object',
      defaultValue: 'undefined',
      description: 'ECharts option；由上层 / L2 构建。',
    },
    {
      name: 'fallback',
      type: 'ReactNode',
      defaultValue: 'null',
      description: '无 option 且非 loading 时展示（如「暂无数据」）。',
    },
    {
      name: 'height',
      type: 'number | string',
      defaultValue: '180',
      description: '画布高度；数字按 px，也可传 CSS 长度。',
    },
    {
      name: 'framed',
      type: 'boolean',
      defaultValue: 'true',
      description: '描边 + 圆角内边距。',
    },
    {
      name: 'spaced',
      type: 'boolean',
      defaultValue: 'false',
      description: '额外上边距（优先仍用父级 gap）。',
    },
    {
      name: 'loading',
      type: 'boolean',
      defaultValue: 'false',
      description: '显示 Loading，不渲染 option。',
    },
    {
      name: 'onEvents',
      type: 'object',
      defaultValue: 'undefined',
      description: '透传 echarts-for-react 事件。',
    },
  ],
  scenarios: [
    '报告柱状 / 折线：上层 withChartTheme(option) 后传入。',
    '市场 K 线：L2 buildMarketChartOption → 本壳展示。',
    '空态：fallback；加载：loading。',
  ],
  antiPatterns: [
    '不要在 ChartPanel 里写 candlestick / 财报标记（那是 L2 marketChart）。',
    '不要把业务数据适配逻辑塞进本组件。',
  ],
};

export default doc;
