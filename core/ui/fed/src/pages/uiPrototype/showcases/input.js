import React, { useState } from 'react';
import Field from 'ui/input/field';
import TextField from 'ui/input/textField';
import TextArea from 'ui/input/textArea';
import Checkbox from 'ui/input/checkbox';
import RadioGroup from 'ui/input/radio';
import Select from 'ui/input/select';
import SearchSelect from 'ui/input/searchSelect';
import Text from 'ui/text/text';
import Section from 'ui/layout/section';
import { Showcase, SampleDim, SampleRow, SampleNA } from './sample';

function FieldShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label='labelPlacement="above"' block>
          <Field label="策略名称" tip="用于列表展示" hint="可稍后修改">
            <TextField labelPlacement="none" placeholder="例如动量增强" />
          </Field>
        </SampleRow>
        <SampleRow label='labelPlacement="inline"' block>
          <Field label="代码" labelPlacement="inline" tip="唯一标识">
            <TextField labelPlacement="none" placeholder="alpha_01" />
          </Field>
        </SampleRow>
        <SampleRow label='labelPlacement="none"' block>
          <Field labelPlacement="none" error="请填写必填项">
            <TextField labelPlacement="none" placeholder="无标签，仅错误" aria-label="必填" />
          </Field>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>Field 无独立 size；控件高度跟随 MUI small + 主题。</SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          标签 / 控件 / error 纵向间距
          {' '}
          <Text variant="code">sm</Text>
          ；inline 水平
          {' '}
          <Text variant="code">md</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>错误文案用 error 色；hint 为 muted。</SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>无圆角参数；布局由 labelPlacement 决定。</SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function TextFieldShowcase() {
  const [name, setName] = useState('动量增强');
  const [code, setCode] = useState('');

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="默认 above + tip" block>
          <TextField
            label="策略名称"
            tip="列表与报告中的显示名"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </SampleRow>
        <SampleRow label='labelPlacement="inline"' block>
          <TextField
            label="代码"
            labelPlacement="inline"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="alpha_01"
          />
        </SampleRow>
        <SampleRow label="error" block>
          <TextField
            label="邮箱"
            value=""
            onChange={() => {}}
            error="格式不正确"
            placeholder="you@example.com"
          />
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleRow label="默认 maxWidth ≈ 280px" block>
          <TextField label="默认宽度" value={name} onChange={(e) => setName(e.target.value)} />
        </SampleRow>
        <SampleRow label="maxWidth={false}" block>
          <TextField
            label="拉满父级"
            maxWidth={false}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </SampleRow>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>由 Field 控制（sm）；与兄弟块上下距交给父级 gap。</SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>玻璃底 + 白描边（主题）；error 时描边/文案变红。</SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleRow label='type="password"' block>
          <TextField label="密码" type="password" value="secret" onChange={() => {}} />
        </SampleRow>
      </SampleDim>
    </Showcase>
  );
}

function TextAreaShowcase() {
  const [note, setNote] = useState('回测说明…');

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="多行 + hint" block>
          <TextArea
            label="备注"
            hint="支持换行"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleRow label="默认 rows={3} | rows={5}" block>
          <Section gap="md">
            <TextArea label="短" rows={3} value="三行" onChange={() => {}} />
            <TextArea label="长" rows={5} value="五行起" onChange={() => {}} />
          </Section>
        </SampleRow>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>同 TextField / Field。</SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>同 TextField。</SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>无独立 radius；多行不强制 40px 高。</SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function CheckboxShowcase() {
  const [on, setOn] = useState(true);
  const [agree, setAgree] = useState(false);

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="右侧 label">
          <Checkbox
            label="启用该策略"
            checked={on}
            onChange={(e) => setOn(e.target.checked)}
          />
        </SampleRow>
        <SampleRow label="fieldLabel + tip" block>
          <Checkbox
            fieldLabel="协议"
            labelPlacement="above"
            tip="打开全文"
            label="我已阅读并同意"
            checked={agree}
            onChange={(e) => setAgree(e.target.checked)}
          />
        </SampleRow>
        <SampleRow label="disabled">
          <Checkbox label="不可用" checked disabled />
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>MUI size="small"，无独立 size 参数。</SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>勾选与文案间距 xs。</SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>跟随主题主色。</SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>无额外外形参数。</SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function RadioShowcase() {
  const [freq, setFreq] = useState('d');
  const [mode, setMode] = useState('live');
  const [scanMode, setScanMode] = useState('strict');

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label='variant="plain"（默认圆点）' block>
          <RadioGroup
            label="频率"
            tip="采样周期"
            name="freq"
            value={freq}
            onChange={(e) => setFreq(e.target.value)}
            options={[
              { value: 'd', label: '日' },
              { value: 'w', label: '周' },
              { value: 'm', label: '月' },
            ]}
          />
        </SampleRow>
        <SampleRow label='plain + direction="row"' block>
          <RadioGroup
            label="模式"
            name="mode"
            direction="row"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            options={[
              { value: 'live', label: '实盘' },
              { value: 'sim', label: '模拟' },
            ]}
          />
        </SampleRow>
        <SampleRow label='variant="button"（扫描页大按钮卡片）' block>
          <RadioGroup
            label="扫描模式"
            variant="button"
            name="scanMode"
            value={scanMode}
            onChange={(e) => setScanMode(e.target.value)}
            options={[
              {
                value: 'strict',
                label: '严格模式',
                description: (
                  <>
                    依赖数据须更新至
                    <strong>最新交易日</strong>
                    ，否则中断并提示缺口。
                  </>
                ),
              },
              {
                value: 'demo',
                label: '扫描演示',
                description: '演示用，非实时市场。',
              },
            ]}
          />
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>Radio small；button 卡片无独立 size，内边距固定。</SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          图与文字用
          {' '}
          <Text variant="code">xxs</Text>
          ；选项间距 column
          {' '}
          <Text variant="code">xs</Text>
          ，row
          {' '}
          <Text variant="code">sm</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>
          plain 跟随主题；button 选中为青色描边/浅底（对齐扫描页）。
        </SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleRow label="disabled 整组" block>
          <RadioGroup
            label="冻结"
            name="frozen"
            disabled
            value="a"
            onChange={() => {}}
            options={[
              { value: 'a', label: 'A' },
              { value: 'b', label: 'B' },
            ]}
          />
        </SampleRow>
      </SampleDim>
    </Showcase>
  );
}

const PERIOD_OPTIONS = [
  { value: 'd', label: '日' },
  { value: 'w', label: '周' },
  { value: 'm', label: '月' },
];

const STRATEGY_OPTIONS = [
  { value: 'mom', label: '动量增强' },
  { value: 'mean', label: '均值回归' },
  { value: 'factor', label: '多因子' },
  { value: 'arb', label: '统计套利' },
  { value: 'trend', label: '趋势跟踪' },
];

function SelectShowcase() {
  const [period, setPeriod] = useState('d');
  const [empty, setEmpty] = useState('');

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="基础单选" block>
          <Select
            label="周期"
            tip="采样周期"
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            options={PERIOD_OPTIONS}
          />
        </SampleRow>
        <SampleRow label='labelPlacement="inline"' block>
          <Select
            label="周期"
            labelPlacement="inline"
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            options={PERIOD_OPTIONS}
          />
        </SampleRow>
        <SampleRow label="空值 placeholder" block>
          <Select
            label="未选"
            value={empty}
            onChange={(e) => setEmpty(e.target.value)}
            options={PERIOD_OPTIONS}
            placeholder="请选择周期"
          />
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>固定 small；无独立 size。</SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>标签间距同 Field。</SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>玻璃底；error 时描边/文案变红。</SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleRow label="disabled" block>
          <Select label="禁用" value="d" disabled options={PERIOD_OPTIONS} onChange={() => {}} />
        </SampleRow>
      </SampleDim>
    </Showcase>
  );
}

function SearchSelectShowcase() {
  const [strategy, setStrategy] = useState('mom');

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="展开后顶部搜索框过滤长列表" block>
          <SearchSelect
            label="策略"
            tip="点开后在面板内搜索"
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            options={STRATEGY_OPTIONS}
            placeholder="搜索策略…"
            emptyLabel="请选择策略"
          />
        </SampleRow>
        <SampleRow label="可清除" block>
          <SearchSelect
            label="策略"
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            options={STRATEGY_OPTIONS}
            clearable
          />
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>触发器高度对齐 small 输入；无独立 size。</SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>同 Field；面板内搜索区与列表有分隔。</SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>不透明面板；不模糊整页背景。</SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleRow label="clearable={false}" block>
          <SearchSelect
            label="不可清空"
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            options={STRATEGY_OPTIONS}
            clearable={false}
          />
        </SampleRow>
      </SampleDim>
    </Showcase>
  );
}

const inputShowcases = {
  field: FieldShowcase,
  textField: TextFieldShowcase,
  textArea: TextAreaShowcase,
  checkbox: CheckboxShowcase,
  radio: RadioShowcase,
  select: SelectShowcase,
  searchSelect: SearchSelectShowcase,
};

export default inputShowcases;
