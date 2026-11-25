import React, { useState } from 'react';
import MonthCalendar from 'ui/calendar/monthCalendar';
import Tag from 'ui/tag/tag';
import Text from 'ui/text/text';
import { Showcase, SampleDim, SampleRow, SampleNA } from './sample';

function MonthCalendarShowcase() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [selected, setSelected] = useState('');

  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="紧凑选日 density=sm" block>
          <MonthCalendar
            year={year}
            month={month}
            today={today}
            selected={selected}
            density="sm"
            onMonthChange={({ year: y, month: m }) => {
              setYear(y);
              setMonth(m);
            }}
            onDayClick={setSelected}
          />
          <p className="ntq-caption" style={{ margin: '0.75rem 0 0' }}>
            选中：
            {' '}
            <Text variant="code">{selected || '（无）'}</Text>
          </p>
        </SampleRow>
        <SampleRow label="可塞内容 density=md + renderDay" block>
          <MonthCalendar
            year={year}
            month={month}
            today={today}
            selected={selected}
            density="md"
            showNav={false}
            renderDay={(date) => {
              if (!date.endsWith('-01') && !date.endsWith('-15')) return null;
              return (
                <Tag status="info" size="sm">
                  示意
                </Tag>
              );
            }}
          />
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          <Text variant="code">density</Text>
          ：sm 紧凑 / md 高格。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>导航与网格 gap=sm；格内 padding=xs。</SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>
          今日浅青底；选中青描边。事件色由
          {' '}
          <Text variant="code">renderDay</Text>
          决定。
        </SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>
          周一开始；交易回测买卖标记属 L2，不要写进本组件。
        </SampleNA>
      </SampleDim>
    </Showcase>
  );
}

const showcases = { monthCalendar: MonthCalendarShowcase };
export default showcases;
