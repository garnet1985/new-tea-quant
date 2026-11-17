import { ICON_NAMES } from './iconRegistry';

const doc = {
  summary: `图标原语。name 必须是注册表中的名字（共 ${ICON_NAMES.length} 个）；size / tone 用语义 token。`,
  params: [
    {
      name: 'name',
      type: 'string（注册表 key）',
      defaultValue: '—（必填）',
      description: '图标名。详细见下方列表 / 图鉴。',
    },
    {
      name: 'size',
      type: "'sm' | 'md' | 'lg' | 'xl' | 'xxl'",
      defaultValue: "'md'",
      description: '尺寸 token → --ui-icon-* / --ntq-icon-*（xxl = 3rem）。',
    },
    {
      name: 'tone',
      type: "'' | 'muted' | 'success' | 'error' | 'warning' | 'disabled' | 'cyan' | 'violet'",
      defaultValue: "''",
      description: '色调；空则继承 currentColor。',
    },
    {
      name: 'spin',
      type: 'boolean',
      defaultValue: 'false',
      description: '旋转动画。',
    },
    {
      name: 'title',
      type: 'string',
      defaultValue: "''",
      description: '无障碍标签。',
    },
  ],
  scenarios: [
    '按钮旁图标、列表操作、状态标记。',
    '加载：name="refresh" spin。',
  ],
  antiPatterns: [
    '禁止 size={24}。',
    '禁止使用未在 ICON_NAMES 中的 name。',
  ],
};

export default doc;
