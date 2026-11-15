import React from 'react';
import { Box } from '@mui/material';
import NtqButton from 'ui/button/ntqButton';
import RainbowButton from 'ui/button/rainbowButton';
import Text from 'ui/text/text';
import { Showcase, SampleDim, SampleRow, SampleNA } from './sample';

function NtqButtonShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label='variant：glass | primary | attention | ghost'>
          <NtqButton variant="glass">玻璃</NtqButton>
          <NtqButton variant="primary">主要</NtqButton>
          <NtqButton variant="attention">强调</NtqButton>
          <NtqButton variant="ghost">轻量</NtqButton>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleRow label='size="small" 与默认；iconSize 语义档位'>
          <NtqButton variant="glass" size="small" icon="search" iconSize="sm">搜索</NtqButton>
          <NtqButton variant="glass" icon="add" iconSize="md">添加</NtqButton>
          <NtqButton variant="primary" icon="settings" iconSize="lg">设置</NtqButton>
        </SampleRow>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          按钮本身无
          {' '}
          <Text variant="code">gap</Text>
          ；组间距由外层布局负责。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleRow label="由形态决定，无独立色调参数">
          <NtqButton variant="primary">主要（实心）</NtqButton>
          <NtqButton variant="attention">强调（描边）</NtqButton>
          <NtqButton variant="glass">玻璃</NtqButton>
        </SampleRow>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleRow label="禁用态；圆角由按钮样式 / 全局圆角变量决定">
          <NtqButton variant="primary" disabled>不可用</NtqButton>
          <NtqButton variant="glass" disabled>不可用</NtqButton>
        </SampleRow>
      </SampleDim>
    </Showcase>
  );
}

function RainbowButtonShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label='shape="circle" · 图标 / 标记'>
          <RainbowButton icon="play" aria-label="运行" />
          <RainbowButton icon="refresh" aria-label="刷新" />
          <RainbowButton mark="help" size="lg" aria-label="帮助" />
          <RainbowButton mark="ai" size="lg" glow aria-label="助手" />
        </SampleRow>
        <SampleRow label='shape="pill"（胶囊）'>
          <RainbowButton shape="pill" ring="spin" icon="play" shimmer>
            开始运行
          </RainbowButton>
          <RainbowButton shape="pill" ring="plain">
            取消
          </RainbowButton>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleRow label='圆形：size="sm" | "lg"'>
          <Box className="ui-prototype__icon-size-cell">
            <RainbowButton icon="play" size="sm" aria-label="小" />
            <Text variant="code">sm</Text>
          </Box>
          <Box className="ui-prototype__icon-size-cell">
            <RainbowButton icon="play" size="lg" aria-label="大" />
            <Text variant="code">lg</Text>
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
        <SampleRow label="彩虹环 / 发光 / 安静态（非独立色调）">
          <Box className="ui-prototype__icon-size-cell">
            <RainbowButton mark="ai" size="lg" glow aria-label="发光" />
            <Text variant="code">glow</Text>
          </Box>
          <Box className="ui-prototype__icon-size-cell">
            <RainbowButton mark="ai" size="lg" glow quiet aria-label="安静" />
            <Text variant="code">quiet</Text>
          </Box>
        </SampleRow>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleRow label='ring="spin" | "still" | "plain"'>
          <Box className="ui-prototype__icon-size-cell">
            <RainbowButton icon="play" ring="spin" aria-label="旋转环" />
            <Text variant="code">spin</Text>
          </Box>
          <Box className="ui-prototype__icon-size-cell">
            <RainbowButton icon="play" ring="still" aria-label="静止环" />
            <Text variant="code">still</Text>
          </Box>
          <Box className="ui-prototype__icon-size-cell">
            <RainbowButton icon="cancel" ring="plain" aria-label="无环" />
            <Text variant="code">plain</Text>
          </Box>
        </SampleRow>
        <SampleRow label="胶囊 + 禁用">
          <RainbowButton shape="pill" ring="spin" disabled>
            排队中
          </RainbowButton>
        </SampleRow>
      </SampleDim>
    </Showcase>
  );
}

const buttonShowcases = {
  ntqButton: NtqButtonShowcase,
  rainbowButton: RainbowButtonShowcase,
};

export default buttonShowcases;
