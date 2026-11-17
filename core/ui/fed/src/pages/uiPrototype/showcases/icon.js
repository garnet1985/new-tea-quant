import React from 'react';
import NtqIcon, { NTQ_ICON_NAMES } from 'ui/icon/ntqIcon';
import { ICON_SIZE_TOKENS, ICON_TONE_TOKENS } from 'ui/tokens';
import Text from 'ui/text/text';
import { Showcase, SampleDim, SampleRow, SampleNA } from './sample';

function IconTile({ name }) {
  return (
    <div className="ui-prototype__icon-tile">
      <NtqIcon name={name} size="lg" title={name} />
      <Text variant="code" className="ui-prototype__icon-tile-name">{name}</Text>
    </div>
  );
}

function NtqIconShowcase() {
  const tones = ICON_TONE_TOKENS.filter(Boolean);

  return (
    <Showcase>
      <SampleDim title={`1. 形态（全部图标，共 ${NTQ_ICON_NAMES.length} 个）`}>
        <SampleRow block>
          <div className="ui-prototype__icon-grid">
            {NTQ_ICON_NAMES.map((name) => (
              <IconTile key={name} name={name} />
            ))}
          </div>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleRow label={`size：${ICON_SIZE_TOKENS.join(' | ')}`}>
          {ICON_SIZE_TOKENS.map((size) => (
            <div key={size} className="ui-prototype__icon-size-cell">
              <NtqIcon name="settings" size={size} />
              <Text variant="code">{size}</Text>
            </div>
          ))}
        </SampleRow>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          本组件无
          {' '}
          <Text variant="code">gap</Text>
          ；图标间距由外层布局负责。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleRow label="默认（空）继承当前字色；其余为语义色">
          <div className="ui-prototype__icon-size-cell">
            <NtqIcon name="settings" size="lg" />
            <Text variant="code">默认</Text>
          </div>
          {tones.map((tone) => (
            <div key={tone} className="ui-prototype__icon-size-cell">
              <NtqIcon name="settings" size="lg" tone={tone} />
              <Text variant="code">{tone}</Text>
            </div>
          ))}
        </SampleRow>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleRow label="旋转动画；无圆角 / 外形参数">
          <div className="ui-prototype__icon-size-cell">
            <NtqIcon name="refresh" size="lg" spin />
            <Text variant="code">spin</Text>
          </div>
        </SampleRow>
      </SampleDim>
    </Showcase>
  );
}

const iconShowcases = {
  ntqIcon: NtqIconShowcase,
};

export default iconShowcases;
