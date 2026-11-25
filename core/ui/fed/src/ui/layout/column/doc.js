const doc = {
  summary: '分栏布局原语。variant 选版式；gap / align / divider 用语义 token。表面样式用子级 Block。',
  params: [
    {
      name: 'variant',
      type: "'halves' | 'thirds' | 'quarters' | 'asideMain' | 'mainAside' | 'sidebar' | 'sidebarEnd'",
      defaultValue: "'halves'",
      description: '分栏形态：两/三/四等分；主从（1:2 / 2:1）；固定侧栏（左/右）。',
    },
    {
      name: 'gap',
      type: "'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl'",
      defaultValue: "'md'",
      description: '列间距 token → --ntq-space-*。',
    },
    {
      name: 'divider',
      type: "'none' | 'line'",
      defaultValue: "'none'",
      description: '列间竖线。贴边分栏（如侧栏|主区）常与 gap="none" 同用。',
    },
    {
      name: 'align',
      type: "'stretch' | 'start' | 'center' | 'end'",
      defaultValue: "'stretch'",
      description: 'align-items。',
    },
    {
      name: 'stack',
      type: 'boolean',
      defaultValue: 'true',
      description: '窄屏是否单列堆叠（堆叠时 divider 改为顶部分隔）。',
    },
    {
      name: 'children',
      type: 'ReactNode',
      defaultValue: '—',
      description: '按 variant 列数准备子节点。',
    },
  ],
  scenarios: [
    '卡片墙三等分：variant="thirds"。',
    '左摘要右主文：variant="asideMain"。',
    '图鉴/设置侧栏：variant="sidebar" gap="none" divider="line"。',
  ],
  antiPatterns: [
    '禁止 columns={3} / columns={[1,2]} / 手写 track 字符串。',
    '禁止 gap={16}。',
    '子节点数量应与 variant 匹配（如 thirds 放 3 个）。',
    '不要在 Column 上堆背景/圆角；用 Block surface / radius。',
  ],
};

export default doc;
