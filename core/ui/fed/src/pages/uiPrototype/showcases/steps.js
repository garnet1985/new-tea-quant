import React, { useState } from 'react';
import Stepper from 'ui/steps/stepper';
import Section from 'ui/layout/section';
import Text from 'ui/text/text';
import { Showcase, SampleDim, SampleRow, SampleNA } from './sample';

const BASE_ITEMS = [
  { id: 'enum', label: '机会盘点', no: 1 },
  { id: 'price', label: '价格回测', no: 2 },
  { id: 'portfolio', label: '投资模拟', no: 3 },
  { id: 'decision', label: '决策模拟', no: 4 },
];

function StepperShowcase() {
  const [activeId, setActiveId] = useState('price');

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="普通 / 激活（靠 activeId）" block>
          <Stepper
            activeId="enum"
            showProgress={false}
            items={BASE_ITEMS.map((item) => ({ ...item, status: 'idle' }))}
          />
        </SampleRow>
        <SampleRow label="执行态：done / running / failed / idle" block>
          <Stepper
            activeId="price"
            items={[
              { ...BASE_ITEMS[0], status: 'done' },
              { ...BASE_ITEMS[1], status: 'running', progress: 55 },
              { ...BASE_ITEMS[2], status: 'idle' },
              { ...BASE_ITEMS[3], status: 'failed' },
            ]}
          />
        </SampleRow>
        <SampleRow label="done + 当前选中 → done-active" block>
          <Stepper
            activeId="enum"
            items={BASE_ITEMS.map((item, idx) => ({
              ...item,
              status: idx === 0 ? 'done' : 'idle',
            }))}
          />
        </SampleRow>
        <SampleRow label="pending（不确定环）" block>
          <Stepper
            activeId="price"
            items={[
              { ...BASE_ITEMS[0], status: 'done' },
              { ...BASE_ITEMS[1], status: 'pending' },
              { ...BASE_ITEMS[2], status: 'idle' },
              { ...BASE_ITEMS[3], status: 'idle' },
            ]}
          />
        </SampleRow>
        <SampleRow label="showProgress={false}（去掉进度环）" block>
          <Stepper
            activeId="price"
            showProgress={false}
            items={[
              { ...BASE_ITEMS[0], status: 'done' },
              { ...BASE_ITEMS[1], status: 'running', progress: 55 },
              { ...BASE_ITEMS[2], status: 'pending' },
              { ...BASE_ITEMS[3], status: 'idle' },
            ]}
          />
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          无独立
          {' '}
          <Text variant="code">size</Text>
          ；圆与间距固定对齐回测（环
          {' '}
          <Text variant="code">md</Text>
          = 3.5rem）。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          步距固定
          {' '}
          <Text variant="code">2.75rem</Text>
          ；与兄弟块上下距交给父级
          {' '}
          <Text variant="code">gap</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>
          由状态决定：激活青、完成绿、失败红、运行青环。无独立 tone 参数。
        </SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleRow label="可点击（onItemClick / href）" block>
          <Section gap="sm">
            <p className="ntq-muted" style={{ margin: 0 }}>
              当前选中：
              {' '}
              <Text variant="code">{activeId}</Text>
              （点击切换；也可用
              {' '}
              <Text variant="code">href</Text>
              {' '}
              /
              {' '}
              <Text variant="code">to+component</Text>
              做页跳转或锚点）
            </p>
            <Stepper
              activeId={activeId}
              items={[
                { ...BASE_ITEMS[0], status: 'done', href: '#step-enum' },
                { ...BASE_ITEMS[1], status: 'running', progress: 30 },
                { ...BASE_ITEMS[2], status: 'idle' },
                { ...BASE_ITEMS[3], status: 'idle' },
              ]}
              onItemClick={(item) => setActiveId(item.id)}
            />
          </Section>
        </SampleRow>
      </SampleDim>
    </Showcase>
  );
}

const stepsShowcases = {
  stepper: StepperShowcase,
};

export default stepsShowcases;
