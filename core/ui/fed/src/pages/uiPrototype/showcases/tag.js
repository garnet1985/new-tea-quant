import React, { useState } from 'react';
import Tag from 'ui/tag/tag';
import Text from 'ui/text/text';
import { Showcase, SampleDim, SampleRow, SampleNA } from './sample';

function TagShowcase() {
  const [visible, setVisible] = useState(true);

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label='variant="soft"：描边 + 半透明底（默认）' block>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            <Tag status="success" variant="soft">success</Tag>
            <Tag status="warning" variant="soft">warning</Tag>
            <Tag status="info" variant="soft">info</Tag>
            <Tag color="violet" variant="soft">violet</Tag>
          </div>
        </SampleRow>
        <SampleRow label='variant="solid"：border 与背景同色实心' block>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            <Tag status="success" variant="solid">success</Tag>
            <Tag status="error" variant="solid">error</Tag>
            <Tag status="warning" variant="solid">warning</Tag>
            <Tag status="info" variant="solid">info</Tag>
            <Tag status="neutral" variant="solid">neutral</Tag>
            <Tag color="violet" variant="solid">violet</Tag>
          </div>
        </SampleRow>
        <SampleRow label='variant="outline"：仅描边' block>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            <Tag status="success" variant="outline">success</Tag>
            <Tag status="warning" variant="outline">warning</Tag>
            <Tag color="cyan" variant="outline">cyan</Tag>
          </div>
        </SampleRow>
        <SampleRow label="可关闭（onDelete）" block>
          {visible ? (
            <Tag status="info" onDelete={() => setVisible(false)}>筛选：近一周</Tag>
          ) : (
            <button
              type="button"
              className="ntq-link"
              style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer' }}
              onClick={() => setVisible(true)}
            >
              重新显示
            </button>
          )}
        </SampleRow>
        <SampleRow label="带图标" block>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            <Tag status="success" icon="success">已启用</Tag>
            <Tag color="violet" icon="tactic">策略</Tag>
            <Tag status="warning" icon="warning">待更新</Tag>
          </div>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleRow label='size="sm" / "md"' block>
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.5rem' }}>
            <Tag status="info" size="sm">sm</Tag>
            <Tag status="info" size="md">md</Tag>
          </div>
        </SampleRow>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          标签为行内元素；多个 Tag 的间距交给父级
          {' '}
          <Text variant="code">gap</Text>
          （如
          {' '}
          <Text variant="code">0.5rem</Text>
          ）。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleRow label="状态 status" block>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            <Tag status="success">success</Tag>
            <Tag status="error">error</Tag>
            <Tag status="warning">warning</Tag>
            <Tag status="info">info</Tag>
            <Tag status="neutral">neutral</Tag>
          </div>
        </SampleRow>
        <SampleRow label="颜色 color" block>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            <Tag color="green">green</Tag>
            <Tag color="error">error</Tag>
            <Tag color="warning">warning</Tag>
            <Tag color="muted">muted</Tag>
            <Tag color="cyan">cyan</Tag>
            <Tag color="violet">violet</Tag>
          </div>
        </SampleRow>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>
          圆角固定
          {' '}
          <Text variant="code">radius-sm</Text>
          ；形态由
          {' '}
          <Text variant="code">variant</Text>
          控制，无独立
          {' '}
          <Text variant="code">radius</Text>
          参数。
        </SampleNA>
      </SampleDim>
    </Showcase>
  );
}

const showcases = {
  tag: TagShowcase,
};

export default showcases;
