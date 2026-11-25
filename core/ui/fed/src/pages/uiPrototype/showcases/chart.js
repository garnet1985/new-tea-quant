import React, { useMemo, useState } from 'react';
import ChartPanel from 'ui/chart/chartPanel';
import {
  CHART_AXIS_LABEL,
  CHART_AXIS_LINE,
  CHART_BAR_NEG,
  CHART_BAR_POS,
  CHART_GRID_BASE,
  CHART_SPLIT_LINE,
  withChartTheme,
} from 'ui/chart/chartTheme';
import Text from 'ui/text/text';
import { Showcase, SampleDim, SampleRow, SampleNA } from './sample';

function buildBarOption() {
  return withChartTheme({
    grid: CHART_GRID_BASE,
    xAxis: {
      type: 'category',
      data: ['0–1', '1–2', '2–3', '3–5', '5+'],
      axisLabel: CHART_AXIS_LABEL,
      axisLine: CHART_AXIS_LINE,
    },
    yAxis: {
      type: 'value',
      axisLabel: CHART_AXIS_LABEL,
      axisLine: CHART_AXIS_LINE,
      splitLine: CHART_SPLIT_LINE,
    },
    series: [
      {
        type: 'bar',
        data: [4, 12, 9, 5, 2],
        itemStyle: { color: CHART_BAR_POS },
        barMaxWidth: 28,
      },
    ],
  });
}

function buildSignedBarOption() {
  return withChartTheme({
    grid: CHART_GRID_BASE,
    xAxis: {
      type: 'category',
      data: ['A', 'B', 'C', 'D'],
      axisLabel: CHART_AXIS_LABEL,
      axisLine: CHART_AXIS_LINE,
    },
    yAxis: {
      type: 'value',
      axisLabel: CHART_AXIS_LABEL,
      splitLine: CHART_SPLIT_LINE,
    },
    series: [
      {
        type: 'bar',
        data: [
          { value: 3.2, itemStyle: { color: CHART_BAR_POS } },
          { value: -1.4, itemStyle: { color: CHART_BAR_NEG } },
          { value: 0.8, itemStyle: { color: CHART_BAR_POS } },
          { value: -2.1, itemStyle: { color: CHART_BAR_NEG } },
        ],
        barMaxWidth: 28,
      },
    ],
  });
}

function ChartPanelShowcase() {
  const [loading, setLoading] = useState(false);
  const barOption = useMemo(() => buildBarOption(), []);
  const signedOption = useMemo(() => buildSignedBarOption(), []);

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="标题 + tip + 柱状（上层拼 option）" block>
          <ChartPanel
            title="每股机会数分布"
            tip="示意数据；真实报告由 L2 / 页面构建 option"
            note="ChartPanel 只负责壳与主题色约定"
            height={200}
            option={barOption}
          />
        </SampleRow>
        <SampleRow label="正负柱" block>
          <ChartPanel
            title="分组收益示意"
            height={200}
            option={signedOption}
          />
        </SampleRow>
        <SampleRow label="loading / fallback" block>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <label className="ntq-caption" style={{ display: 'inline-flex', gap: '0.5rem', alignItems: 'center' }}>
              <input
                type="checkbox"
                checked={loading}
                onChange={(e) => setLoading(e.target.checked)}
              />
              模拟 loading
            </label>
            <ChartPanel
              title="加载态"
              height={160}
              loading={loading}
              option={loading ? undefined : barOption}
              fallback={<p className="ntq-muted" style={{ margin: 0 }}>暂无数据</p>}
            />
            <ChartPanel
              title="空态 fallback"
              height={120}
              fallback={<p className="ntq-muted" style={{ margin: 0 }}>暂无数据</p>}
            />
          </div>
        </SampleRow>
        <SampleRow label='framed={false}' block>
          <ChartPanel
            title="无边框"
            framed={false}
            height={160}
            option={barOption}
          />
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          用
          {' '}
          <Text variant="code">height</Text>
          （默认 180px）；无独立 size token，避免和业务图高度打架。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          卡内标题 / note 间距固定；与兄弟块用父级
          {' '}
          <Text variant="code">gap</Text>
          （
          <Text variant="code">spaced</Text>
          仅兼容旧用法）。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>
          轴 / tooltip 用
          {' '}
          <Text variant="code">ui/chart/chartTheme</Text>
          ；系列色由 option 指定。阴阳烛等业务色在 L2。
        </SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>
          默认
          {' '}
          <Text variant="code">framed</Text>
          ：描边 +
          {' '}
          <Text variant="code">radius-sm</Text>
          。K 线请上层
          {' '}
          <Text variant="code">buildMarketChartOption</Text>
          后传入本壳。
        </SampleNA>
      </SampleDim>
    </Showcase>
  );
}

const showcases = {
  chartPanel: ChartPanelShowcase,
};

export default showcases;
