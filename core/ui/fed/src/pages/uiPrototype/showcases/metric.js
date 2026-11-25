import React, { useRef, useState } from 'react';
import CountTab from 'ui/metric/countTab';
import CountBadge from 'ui/metric/countBadge';
import MetricCard from 'ui/metric/metricCard';
import MetricGrid from 'ui/metric/metricGrid';
import Text from 'ui/text/text';
import { Showcase, SampleDim, SampleRow, SampleNA } from './sample';

const CATEGORIES = [
  { id: '', label: '全部', count: 12, wide: true },
  { id: 'momentum', label: '动量', count: 4 },
  { id: 'mean-reversion', label: '均值回归', count: 3 },
  { id: 'event', label: '事件驱动超长名称示例', count: 2 },
  { id: 'other', label: '其它', count: 3 },
];

function CountTabShowcase() {
  const [query, setQuery] = useState('');
  const selectedRef = useRef(null);

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="筛选条（全部 + 归类，上层持有 query）" block>
          <div
            style={{
              display: 'flex',
              flexWrap: 'nowrap',
              alignItems: 'center',
              gap: '0.5rem',
              minWidth: 0,
              overflowX: 'auto',
              padding: '0.125rem 0',
            }}
            role="group"
            aria-label="按归类筛选"
          >
            {CATEGORIES.map((item) => {
              const selected = query === item.id;
              return (
                <CountTab
                  key={item.id || 'all'}
                  label={item.label}
                  count={item.count}
                  wide={item.wide}
                  title={item.label}
                  selected={selected}
                  ref={selected ? selectedRef : undefined}
                  onClick={() => setQuery(item.id)}
                />
              );
            })}
          </div>
          <p className="ntq-caption" style={{ margin: '0.75rem 0 0' }}>
            当前 query：
            {' '}
            <Text variant="code">{query || '(全部)'}</Text>
          </p>
        </SampleRow>
        <SampleRow label="无 count / 禁用" block>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            <CountTab label="无计数" selected />
            <CountTab label="禁用" count={0} disabled />
          </div>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          高度固定
          {' '}
          <Text variant="code">1.75rem</Text>
          （28px），与列表工具栏 Chip 对齐；无独立
          {' '}
          <Text variant="code">size</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          多个 Tab 的间距交给父级
          {' '}
          <Text variant="code">gap</Text>
          （图鉴示例
          {' '}
          <Text variant="code">0.5rem</Text>
          ）；横向滚动容器由上层提供。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleRow label="默认 / 选中" block>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            <CountTab label="默认" count={5} />
            <CountTab label="选中" count={5} selected />
          </div>
        </SampleRow>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleRow label='wide：不限制 max-width' block>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', maxWidth: '16rem' }}>
            <CountTab label="全部" count={99} wide selected />
            <CountTab label="很长的归类名称会被截断" count={1} title="很长的归类名称会被截断" />
          </div>
        </SampleRow>
      </SampleDim>
    </Showcase>
  );
}

function CountBadgeShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="行内计数" block>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>信号</span>
            <CountBadge count={3} label="信号数" />
            <CountBadge count={12} label="子项" />
            <CountBadge count={0} label="零" />
          </div>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          固定胶囊
          {' '}
          <Text variant="code">1.375rem</Text>
          ；无
          {' '}
          <Text variant="code">size</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>与相邻文案的间距交给父级 gap。</SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>
          中性白叠色；状态色用
          {' '}
          <Text variant="code">Tag</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>
          <Text variant="code">radius-pill</Text>
          ；可点击筛选用
          {' '}
          <Text variant="code">CountTab</Text>
          。
        </SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function MetricCardShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="单卡 / 带 tip / 带 hint" block>
          <MetricGrid columns={2}>
            <MetricCard title="机会总数" value="1,280" tip="统计窗口内触发次数" />
            <MetricCard
              title="涨停无法买入"
              value="12 / 100"
              hint="占比 12%"
              tip="买入日涨停无法成交的样本"
            />
          </MetricGrid>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          无独立
          {' '}
          <Text variant="code">size</Text>
          ；主值字号
          {' '}
          <Text variant="code">font-md</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          卡内 padding / 标题-主值间距固定；多卡间距交给
          {' '}
          <Text variant="code">MetricGrid</Text>
          {' '}
          的
          {' '}
          <Text variant="code">gap</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>
          中性 panel 表面；状态色不要写进卡面（用
          {' '}
          <Text variant="code">Tag</Text>
          ；业务映射属 L2）。
        </SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>
          描边 +
          {' '}
          <Text variant="code">radius-sm</Text>
          {' '}
          + 浅底；与报告区块对齐。
        </SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function MetricGridShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label='columns={2}（默认）' block>
          <MetricGrid columns={2}>
            <MetricCard title="A" value="1" />
            <MetricCard title="B" value="2" />
          </MetricGrid>
        </SampleRow>
        <SampleRow label='columns={3}' block>
          <MetricGrid columns={3}>
            <MetricCard title="A" value="1" />
            <MetricCard title="B" value="2" />
            <MetricCard title="C" value="3" />
          </MetricGrid>
        </SampleRow>
        <SampleRow label='columns={4} + denseXs' block>
          <MetricGrid columns={4} denseXs>
            <MetricCard title="A" value="1" />
            <MetricCard title="B" value="2" />
            <MetricCard title="C" value="3" />
            <MetricCard title="D" value="4" />
          </MetricGrid>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          列数由
          {' '}
          <Text variant="code">columns</Text>
          控制；无独立 size。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          格子
          {' '}
          <Text variant="code">gap = space-sm</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>网格本身无色；颜色在子卡。</SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>
          窄屏 1 列（
          <Text variant="code">denseXs</Text>
          时 2 列）；≥900px 按 columns。
        </SampleNA>
      </SampleDim>
    </Showcase>
  );
}

const showcases = {
  countTab: CountTabShowcase,
  countBadge: CountBadgeShowcase,
  metricCard: MetricCardShowcase,
  metricGrid: MetricGridShowcase,
};

export default showcases;
