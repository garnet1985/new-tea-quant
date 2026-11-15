import React from 'react';
import Separator from 'ui/text/separator';
import Section from 'ui/layout/section';
import { Showcase, SampleDim, SampleRow, SampleNA } from './sample';

function SeparatorShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="默认" block>
          <Separator>行内特殊字形</Separator>
        </SampleRow>
        <SampleRow label='tone="muted"' block>
          <Separator tone="muted">弱化分隔</Separator>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>无 size；文案为 sm，线高 1px。</SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>自身无 gap；与上下内容的间距由外层负责。</SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleRow label="default / muted" block>
          <Section gap="sm">
            <Separator>默认</Separator>
            <Separator tone="muted">弱化</Separator>
          </Section>
        </SampleRow>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>左文右线；编号大节（如「1. 形态」）请用 Heading，不要加竖条。</SampleNA>
      </SampleDim>
    </Showcase>
  );
}

const separatorShowcases = {
  separator: SeparatorShowcase,
};

export default separatorShowcases;
