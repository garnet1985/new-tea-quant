const doc = {
  summary: '月历壳（周一开始）。导航换月、选中/今日态；格子内容用 renderDay 由上层填。交易回测事件属 L2，不进本组件。',
  params: [
    {
      name: 'year / month',
      type: 'number',
      defaultValue: '当前年月',
      description: 'month 为 1–12。',
    },
    {
      name: 'selected / today',
      type: 'string (YYYY-MM-DD)',
      defaultValue: "''",
      description: '选中日 / 今日高亮。',
    },
    {
      name: 'density',
      type: "'sm' | 'md'",
      defaultValue: "'sm'",
      description: 'sm 紧凑；md 高格子可塞事件。',
    },
    {
      name: 'showNav',
      type: 'boolean',
      defaultValue: 'true',
      description: '显示上/下月按钮（需 onMonthChange 才可点）。',
    },
    {
      name: 'onMonthChange',
      type: '({ year, month }) => void',
      defaultValue: 'undefined',
      description: '换月回调。',
    },
    {
      name: 'onDayClick',
      type: '(date: string) => void',
      defaultValue: 'undefined',
      description: '点击日期。',
    },
    {
      name: 'renderDay',
      type: '(date: string) => ReactNode',
      defaultValue: 'undefined',
      description: '日数字下方内容（事件条等）。',
    },
    {
      name: 'disabledDates',
      type: 'string[] | Set',
      defaultValue: 'undefined',
      description: '禁用日期。',
    },
  ],
  scenarios: [
    '选日面板 density=sm。',
    '回测事件回溯：density=md + renderDay 画买卖/机会（L2）。',
  ],
  antiPatterns: [
    '不要在本组件写死机会/买入/卖出样式（那是 decision L2）。',
    '表单单日选择优先用 input/date；本组件是月视图网格。',
  ],
};

export default doc;
