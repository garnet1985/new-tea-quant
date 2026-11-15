import React from 'react';
import LoadingBars from 'ui/progress/loadingBars';
import Loading from 'ui/progress/loading';
import ProgressBar from 'ui/progress/progressBar';
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
            <ProgressBar value={35} size="md" />
            <ProgressBar value={72} size="md" />
          </Section>
        </SampleRow>
        <SampleRow label="无 value → 不确定进度" block>
          <ProgressBar size="md" />
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleRow label='size="md"' block>
          <ProgressBar value={50} size="md" />
        </SampleRow>
        <SampleRow label='size="sm"' block>
          <ProgressBar value={50} size="sm" />
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
        <SampleNA>跟随主题主色，无独立色调参数。</SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>
          轨道圆角来自组件样式 / 全局圆角变量，无独立
          {' '}
          <Text variant="code">radius</Text>
          {' '}
          参数。
        </SampleNA>
      </SampleDim>
    </Showcase>
  );
}

const progressShowcases = {
  loadingBars: LoadingBarsShowcase,
  loading: LoadingShowcase,
  progressBar: ProgressBarShowcase,
};

export default progressShowcases;
