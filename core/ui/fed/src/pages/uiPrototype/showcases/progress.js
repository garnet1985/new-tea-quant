import React from 'react';
import LoadingBars from 'ui/progress/loadingBars';
import Loading from 'ui/progress/loading';
import ProgressBar from 'ui/progress/progressBar';
import ProgressRing from 'ui/progress/progressRing';
import Section from 'ui/layout/section';
import Block from 'ui/layout/block';
import Text from 'ui/text/text';
import { Box } from '@mui/material';
import { Showcase, SampleDim, SampleRow, SampleNA } from './sample';

function LoadingBarsShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleNA>
          无
          {' '}
          <Text variant="code">variant</Text>
          ；固定三柱动画。
        </SampleNA>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleRow label='size："md" | "sm"'>
          <Box className="ui-prototype__icon-size-cell">
            <LoadingBars size="md" />
            <Text variant="code">md</Text>
          </Box>
          <Box className="ui-prototype__icon-size-cell">
            <LoadingBars size="sm" />
            <Text variant="code">sm</Text>
          </Box>
        </SampleRow>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          本组件无
          {' '}
          <Text variant="code">gap</Text>
          {' '}
          参数。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>跟随主题 / 当前字色，无独立色调参数。</SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>无圆角参数。</SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function LoadingShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label='variant="inline"' block>
          <Loading variant="inline" message="加载中…" />
        </SampleRow>
        <SampleRow label='variant="inlineRow"' block>
          <Loading variant="inlineRow" message="同步中" />
        </SampleRow>
        <SampleRow label='variant="page"（缩略示意）' block>
          <Block bordered padding="md">
            <Loading
              variant="page"
              message="正在加载页面…"
              className="ui-prototype__loading-page-demo"
            />
          </Block>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          无独立
          {' '}
          <Text variant="code">size</Text>
          ；条高度由内嵌加载条决定。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          内部间距由组件样式控制，无
          {' '}
          <Text variant="code">gap</Text>
          {' '}
          参数。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>无独立色调参数。</SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>无圆角 / 外形参数。</SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function ProgressBarShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="有 value → 确定进度" block>
          <Section gap="sm">
            <ProgressBar value={35} />
            <ProgressBar value={72} />
          </Section>
        </SampleRow>
        <SampleRow label="无 value → 不确定进度" block>
          <ProgressBar />
        </SampleRow>
        <SampleRow label="label + showPercent（step 名 + 百分比）" block>
          <Section gap="sm">
            <ProgressBar value={42} label="枚举信号" showPercent />
            <ProgressBar value={78} label="回测" showPercent />
          </Section>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleRow label='size="sm"（默认，回测条高）' block>
          <ProgressBar value={50} size="sm" label="sm" showPercent />
        </SampleRow>
        <SampleRow label='size="md"' block>
          <ProgressBar value={50} size="md" label="md" showPercent />
        </SampleRow>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          文案与条之间固定
          {' '}
          <Text variant="code">xs</Text>
          ；与兄弟块的上下距交给父级
          {' '}
          <Text variant="code">gap</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>
          固定紫→青渐变（回测条），无独立 tone 参数。
        </SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>
          轨道微圆角；无独立
          {' '}
          <Text variant="code">radius</Text>
          {' '}
          参数。
        </SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function ProgressRingShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="有 value → 确定进度">
          <ProgressRing value={35} showPercent />
          <ProgressRing value={72} showPercent />
        </SampleRow>
        <SampleRow label="无 value → 不确定旋转">
          <ProgressRing />
        </SampleRow>
        <SampleRow label="label + showPercent">
          <ProgressRing value={40} label="枚举" showPercent />
          <ProgressRing value={85} label="回测" showPercent />
        </SampleRow>
        <SampleRow label="children 自定义环心（如步骤号）">
          <ProgressRing value={60}>3</ProgressRing>
          <ProgressRing value={100} label="完成">✓</ProgressRing>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleRow label='size="md"（默认，≈回测环）'>
          <ProgressRing value={55} size="md" showPercent />
        </SampleRow>
        <SampleRow label='size="sm"'>
          <ProgressRing value={55} size="sm" showPercent />
        </SampleRow>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          环与 label 之间固定
          {' '}
          <Text variant="code">xs</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>环填充固定青色（对齐 step 环），无独立 tone。</SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>细描边圆环；无独立 thickness / radius 参数。</SampleNA>
      </SampleDim>
    </Showcase>
  );
}

const progressShowcases = {
  loadingBars: LoadingBarsShowcase,
  loading: LoadingShowcase,
  progressBar: ProgressBarShowcase,
  progressRing: ProgressRingShowcase,
};

export default progressShowcases;
