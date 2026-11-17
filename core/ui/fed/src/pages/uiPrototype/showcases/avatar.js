import React from 'react';
import Avatar from 'ui/avatar/avatar';
import Text from 'ui/text/text';
import { Showcase, SampleDim, SampleRow, SampleNA } from './sample';

function AvatarShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="图片 / 首字母回退" block>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Avatar src="/logo.png" name="NTQ" alt="徽标头像" />
            <Avatar name="茶" />
            <Avatar name="Alice" />
            <Avatar src="/definitely-missing.png" name="回退" />
          </div>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleRow label='size="sm" / "md" / "lg"' block>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Avatar name="S" size="sm" />
            <Avatar name="M" size="md" />
            <Avatar name="L" size="lg" />
          </div>
        </SampleRow>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>行内间距交给父级 gap。</SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>
          字母底
          {' '}
          <Text variant="code">white-12</Text>
          ；无业务色档。
        </SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>
          正圆
          {' '}
          <Text variant="code">radius-pill</Text>
          。
        </SampleNA>
      </SampleDim>
    </Showcase>
  );
}

const showcases = { avatar: AvatarShowcase };
export default showcases;
