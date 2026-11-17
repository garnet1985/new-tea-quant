const doc = {
  summary: '线性进度条（回测风格：紫→青渐变）。size 用 sm/md；value 0–100。可选 label（step 名）与 showPercent。',
  params: [
    {
      name: 'value',
      type: 'number | null',
      defaultValue: 'null',
      description: '0–100；null 表示 indeterminate。',
    },
    {
      name: 'size',
      type: "'sm' | 'md'",
      defaultValue: "'sm'",
      description: '条高 token；sm=回测 4px 条。',
    },
    {
      name: 'label',
      type: 'ReactNode',
      defaultValue: 'null',
      description: '左侧文案，如 step 名。',
    },
    {
      name: 'showPercent',
      type: 'boolean',
      defaultValue: 'false',
      description: '右侧显示取整百分比。',
    },
    {
      name: 'aria-label',
      type: 'string',
      defaultValue: '由 label /「进度」',
      description: '无障碍。',
    },
  ],
  scenarios: [
    '回测执行：value={pct} label="枚举信号" showPercent。',
    '仅条：value={pct}。',
    '未知耗时：不传 value。',
  ],
  antiPatterns: [
    '禁止 height={8} 写死条高。',
    '循环等待优先 Loading；有明确百分比再用 ProgressBar。',
  ],
};

export default doc;
