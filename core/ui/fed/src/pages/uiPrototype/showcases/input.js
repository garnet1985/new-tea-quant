import React, { useState } from 'react';
import Field from 'ui/input/field';
import TextField from 'ui/input/textField';
import TextArea from 'ui/input/textArea';
import Checkbox from 'ui/input/checkbox';
import RadioGroup from 'ui/input/radio';
import Select from 'ui/input/select';
import SearchSelect from 'ui/input/searchSelect';
import SearchField from 'ui/input/searchField';
import Autocomplete from 'ui/input/autocomplete';
import Switch from 'ui/input/switch';
import Date from 'ui/input/date';
import DateRange from 'ui/input/dateRange';
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
        <SampleRow label="默认 maxWidth ≈ 320px" block>
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

function SearchFieldShowcase() {
  const [q, setQ] = useState('动量');

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="默认（工具栏，无标签）" block>
          <SearchField
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="搜索策略"
          />
        </SampleRow>
        <SampleRow label="labelPlacement above + tip" block>
          <SearchField
            label="关键词"
            labelPlacement="above"
            tip="匹配显示名"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleRow label="默认 maxWidth ≈ 360px | fluid" block>
          <Section gap="md">
            <SearchField value={q} onChange={(e) => setQ(e.target.value)} />
            <SearchField
              fluid
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="弹性宽"
            />
          </Section>
        </SampleRow>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>图标与文字间距 xxs；有 Field 时同 sm。</SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>同 TextField 实底输入。</SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleRow label="clearable={false}" block>
          <SearchField
            value={q}
            onChange={(e) => setQ(e.target.value)}
            clearable={false}
          />
        </SampleRow>
      </SampleDim>
    </Showcase>
  );
}

const UNIT_OPTIONS = [
  { value: 'alpha', label: 'Alpha 单元' },
  { value: 'risk', label: '风控单元' },
  { value: 'exec', label: '执行单元' },
  { value: 'post', label: '后处理' },
];

function AutocompleteShowcase() {
  const [unit, setUnit] = useState('alpha');
  const [deps, setDeps] = useState(['risk']);

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="单选 + tip" block>
          <Autocomplete
            label="执行单元"
            tip="可输入过滤"
            options={UNIT_OPTIONS}
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
            placeholder="输入或选择"
          />
        </SampleRow>
        <SampleRow label="multiple" block>
          <Autocomplete
            label="依赖"
            multiple
            options={UNIT_OPTIONS}
            value={deps}
            onChange={(e) => setDeps(e.target.value)}
            placeholder="添加依赖"
          />
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>默认 maxWidth ≈ 320px；高度同 small 输入。</SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>同 Field；多选芯片间距跟 MUI。</SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>不透明建议面板；不模糊整页。</SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleRow label="clearable={false}" block>
          <Autocomplete
            label="不可清空"
            options={UNIT_OPTIONS}
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
            clearable={false}
          />
        </SampleRow>
      </SampleDim>
    </Showcase>
  );
}

function SwitchShowcase() {
  const [live, setLive] = useState(true);
  const [mail, setMail] = useState(false);

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="标签左 + 开关右" block>
          <Switch
            label="启用实时扫描"
            tip="占用队列时会排队"
            checked={live}
            onChange={(e) => setLive(e.target.checked)}
          />
        </SampleRow>
        <SampleRow label="fieldLabel above" block>
          <Switch
            fieldLabel="邮件通知"
            labelPlacement="above"
            tip="重要告警"
            checked={mail}
            onChange={(e) => setMail(e.target.checked)}
          />
        </SampleRow>
        <SampleRow label="disabled" block>
          <Switch label="不可用" checked disabled />
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>MUI size="small"；主题内已定制轨道。</SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>标签与开关水平 gap md。</SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>跟随主题 primary。</SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>无额外外形参数。</SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function DateShowcase() {
  const [day, setDay] = useState('2024-01-15');

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="默认 above" block>
          <Date
            label="交易日"
            tip="自然日"
            value={day}
            onChange={(e) => setDay(e.target.value)}
          />
        </SampleRow>
        <SampleRow label="error" block>
          <Date
            label="生效日"
            value=""
            onChange={() => {}}
            error="必填"
          />
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>默认 maxWidth ≈ 320px；高度同 small。</SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>同 Field。</SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>同 TextField。</SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>原生 date；样式随浏览器。</SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function DateRangeShowcase() {
  const [range, setRange] = useState({ start: '2024-01-01', end: '2024-03-31' });

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="外层 label" block>
          <DateRange
            label="回测区间"
            tip="含起止日"
            value={range}
            onChange={(e) => setRange(e.target.value)}
          />
        </SampleRow>
        <SampleRow label="无外层 label（各自标签）" block>
          <DateRange
            labelPlacement="none"
            value={range}
            onChange={(e) => setRange(e.target.value)}
          />
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>两侧 Date 各自默认 capped。</SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>两控件水平 gap sm。</SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>同 Date。</SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleRow label="单侧 error" block>
          <DateRange
            label="区间"
            value={range}
            onChange={(e) => setRange(e.target.value)}
            endError="结束日不能早于开始日"
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
  searchField: SearchFieldShowcase,
  autocomplete: AutocompleteShowcase,
  switch: SwitchShowcase,
  date: DateShowcase,
  dateRange: DateRangeShowcase,
};

export default inputShowcases;
