const doc = {
  summary: '线性进度条。size 用 sm/md token；value 为业务进度 0–100（数据，不是样式像素）。不传 value 则为不确定进度动画。',
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
      defaultValue: "'md'",
      description: '高度 token → --ntq-progress-height-*。',
    },
    {
      name: 'aria-label',
      type: 'string',
      defaultValue: "'进度'",
      description: '无障碍。',
    },
  ],
  scenarios: [
    '任务完成度：value={pct}。',
    '未知耗时：不传 value。',
  ],
  antiPatterns: [
    '禁止 height={8} 写死条高。',
    '循环等待优先 Loading；有明确百分比再用 ProgressBar。',
  ],
};

export default doc;
