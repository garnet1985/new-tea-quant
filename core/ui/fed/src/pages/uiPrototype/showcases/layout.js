import React from 'react';
import { Box } from '@mui/material';
import Column from 'ui/layout/column';
import Block from 'ui/layout/block';
import Section from 'ui/layout/section';
import Text from 'ui/text/text';
import {
  COLUMN_VARIANTS,
  RADIUS_TOKENS,
  SPACE_TOKENS,
  SURFACE_TOKENS,
} from 'ui/tokens';
import { Showcase, SampleDim, SampleRow, SampleNA } from './sample';

function DemoCell({ children }) {
  return <Box className="ui-prototype__column-demo">{children}</Box>;
}

function cellsFor(variant) {
  if (variant === 'thirds') return ['一', '二', '三'];
  if (variant === 'quarters') return ['一', '二', '三', '四'];
  if (variant === 'asideMain') return ['侧栏', '主区'];
  if (variant === 'mainAside') return ['主区', '侧栏'];
  if (variant === 'sidebar') return ['侧栏', '内容'];
  if (variant === 'sidebarEnd') return ['内容', '侧栏'];
  return ['左', '右'];
}

const SURFACE_HINT = {
  none: '透明（本例加了描边）',
  soft: '浅底',
  panel: '稍实底（侧栏常用）',
  glass: '玻璃模糊',
  gradient: '纵向浅渐变',
};

function ColumnShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        {COLUMN_VARIANTS.map((variant) => (
          <SampleRow key={variant} label={`variant="${variant}"`} block>
            <Column variant={variant} gap="md">
              {cellsFor(variant).map((label) => (
                <DemoCell key={label}>{label}</DemoCell>
              ))}
            </Column>
          </SampleRow>
        ))}
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          本组件无
          {' '}
          <Text variant="code">size</Text>
          ；列宽由
          {' '}
          <Text variant="code">variant</Text>
          {' '}
          决定（侧栏宽见
          {' '}
          <Text variant="code">--ntq-layout-sidebar-width</Text>
          ）。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleRow
          label={`示意 none / sm / md / xl（全集：${SPACE_TOKENS.join(' | ')}）`}
          block
        >
          <Section gap="md">
            {['none', 'sm', 'md', 'xl'].map((gap) => (
              <Box key={gap}>
                <p className="ntq-caption">
                  <Text variant="code">{`gap="${gap}"`}</Text>
                </p>
                <Column variant="halves" gap={gap}>
                  <DemoCell>甲</DemoCell>
                  <DemoCell>乙</DemoCell>
                </Column>
              </Box>
            ))}
          </Section>
        </SampleRow>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>
          分栏本身不设色；表面交给子级
          {' '}
          <Text variant="code">Block</Text>
          {' '}
          的
          {' '}
          <Text variant="code">surface</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleRow label='gap="none" · divider="line"（与图鉴侧栏相同）' block>
          <Column variant="halves" gap="none" divider="line">
            <Block surface="panel" radius="none" padding="md">左栏</Block>
            <Block padding="md">右栏（中间竖线）</Block>
          </Column>
        </SampleRow>
        <SampleRow label="有间距时仍可加竖线（线贴在后列左侧）" block>
          <Column variant="halves" gap="md" divider="line">
            <DemoCell>甲</DemoCell>
            <DemoCell>乙</DemoCell>
          </Column>
        </SampleRow>
      </SampleDim>
    </Showcase>
  );
}

function BlockShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label={`surface：${SURFACE_TOKENS.join(' | ')}`} block>
          <Section gap="sm">
            {SURFACE_TOKENS.map((surface) => (
              <Block
                key={surface}
                surface={surface}
                bordered={surface === 'none'}
                radius="md"
                padding="md"
              >
                <Text variant="code">{`surface="${surface}"`}</Text>
                <p className="ntq-caption">{SURFACE_HINT[surface]}</p>
              </Block>
            ))}
          </Section>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          本组件无
          {' '}
          <Text variant="code">size</Text>
          ；用
          {' '}
          <Text variant="code">padding</Text>
          {' '}
          控制内边距。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleRow label='padding="md" · gap="sm"' block>
          <Block surface="soft" radius="md" padding="md" gap="sm">
            <p>第一行</p>
            <p className="ntq-muted">第二行（子项间距由 gap 控制）</p>
          </Block>
        </SampleRow>
        <SampleRow label='padding="sm" | "lg"' block>
          <Section gap="sm">
            <Block surface="soft" radius="md" padding="sm">内边距较小</Block>
            <Block surface="soft" radius="md" padding="lg">内边距较大</Block>
          </Section>
        </SampleRow>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleRow label="由 surface 预设控制（改全局表面变量 / 白叠色阶）" block>
          <Section gap="sm">
            <Block surface="soft" radius="md" padding="sm">浅底</Block>
            <Block surface="panel" radius="md" padding="sm">面板</Block>
            <Block surface="glass" radius="md" padding="sm" bordered>玻璃</Block>
          </Section>
        </SampleRow>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleRow label={`radius：${RADIUS_TOKENS.join(' | ')}`} block>
          <Section gap="sm">
            {RADIUS_TOKENS.map((radius) => (
              <Block
                key={radius}
                surface="soft"
                bordered
                radius={radius}
                padding="sm"
              >
                <Text variant="code">{`radius="${radius}"`}</Text>
              </Block>
            ))}
          </Section>
        </SampleRow>
        <SampleRow label="描边可与表面组合" block>
          <Block surface="gradient" radius="lg" bordered padding="md">
            渐变底 + 描边 + 大圆角
          </Block>
        </SampleRow>
      </SampleDim>
    </Showcase>
  );
}

function SectionShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleNA>
          纵向堆叠容器，无
          {' '}
          <Text variant="code">variant</Text>
          ；表面用内嵌
          {' '}
          <Text variant="code">Block</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          本组件无
          {' '}
          <Text variant="code">size</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleRow label='gap="md" · 内嵌分栏与块' block>
          <Section gap="md">
            <Block surface="soft" radius="md" bordered padding="sm">分区甲</Block>
            <Block surface="soft" radius="md" bordered padding="sm">分区乙</Block>
            <Column variant="halves" gap="sm">
              <Block surface="panel" radius="md" padding="sm">左</Block>
              <Block surface="panel" radius="md" padding="sm">右</Block>
            </Column>
          </Section>
        </SampleRow>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>无色调参数。</SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>无圆角 / 表面参数；需要时用内嵌块容器。</SampleNA>
      </SampleDim>
    </Showcase>
  );
}

const layoutShowcases = {
  column: ColumnShowcase,
  block: BlockShowcase,
  section: SectionShowcase,
};

export default layoutShowcases;
