import React from 'react';
import Text from 'ui/text/text';
import Heading from 'ui/text/heading';
import Section from 'ui/layout/section';
import Block from 'ui/layout/block';
import {
  HEADING_BAR_TOKENS,
  HEADING_GAP_TOKENS,
  HEADING_LEVELS,
  HEADING_VARIANTS,
} from 'ui/tokens';
import { Showcase, SampleDim, SampleRow, SampleNA } from './sample';

const HEADING_LEVEL_LABEL = {
  h1: '页面主标题',
  h2: '大区块标题',
  h3: '子区块标题',
  h4: '更小标题',
  h5: '最弱层级',
};

function HeadingShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label={`level：${HEADING_LEVELS.join(' | ')}`} block>
          <Block bordered padding="md" gap="none" surface="soft">
            {HEADING_LEVELS.map((level) => (
              <Heading key={level} level={level} gap="sm">
                {`${level.toUpperCase()} · ${HEADING_LEVEL_LABEL[level]}`}
              </Heading>
            ))}
          </Block>
        </SampleRow>
        <SampleRow label={`variant：${HEADING_VARIANTS.join(' | ')}`} block>
          <Section gap="md">
            <Heading level="h2" variant="plain" gap="none">无竖条（默认）</Heading>
            <Heading level="h2" variant="bar" tone="cyan" gap="none">带竖条</Heading>
            <Heading level="h3" variant="bar" tone="warning" gap="none">小节竖条（官网黄条感）</Heading>
          </Section>
        </SampleRow>
        <SampleRow label="副标题 below / inline" block>
          <Section gap="md">
            <Heading
              level="h2"
              gap="none"
              subtitle="副标题在下方，更小且 muted"
              subtitlePlacement="below"
            >
              下方副标题
            </Heading>
            <Heading
              level="h2"
              gap="none"
              subtitle="行内副题"
              subtitlePlacement="inline"
            >
              行内副标题
            </Heading>
          </Section>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          字号只跟
          {' '}
          <Text variant="code">level</Text>
          {' '}
          走（h1→h5 递减），组件不提供
          {' '}
          <Text variant="code">size</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleRow label={`gap：${HEADING_GAP_TOKENS.join(' | ')}（上 > 下 > 段落间距）`} block>
          <Block bordered padding="md" gap="none" surface="soft">
            <p className="ntq-muted">上文段落</p>
            <Heading level="h2" gap="md">二级标题 gap=md</Heading>
            <p className="ntq-muted">标题下的正文</p>
            <Heading level="h3" gap="sm">三级标题 gap=sm</Heading>
            <p className="ntq-muted">再一段正文</p>
          </Block>
        </SampleRow>
        <SampleRow label='gap="none"：侧栏等紧凑场景' block>
          <Heading level="h3" gap="none">紧凑标题</Heading>
        </SampleRow>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleRow label={`variant="bar" · tone：${HEADING_BAR_TOKENS.join(' | ')}`} block>
          <Section gap="md">
            {HEADING_BAR_TOKENS.map((tone) => (
              <Heading
                key={tone}
                level="h3"
                variant="bar"
                tone={tone}
                gap="none"
                subtitle={`tone="${tone}"`}
              >
                带竖条的标题
              </Heading>
            ))}
          </Section>
        </SampleRow>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleRow label="bar：左竖条 + 左/上下 padding，无背景（对齐官网）" block>
          <Heading
            level="h2"
            variant="bar"
            tone="cyan"
            gap="none"
            subtitle="可与副标题组合"
          >
            强调型标题
          </Heading>
        </SampleRow>
      </SampleDim>
    </Showcase>
  );
}

const headingShowcases = {
  heading: HeadingShowcase,
};

export default headingShowcases;
