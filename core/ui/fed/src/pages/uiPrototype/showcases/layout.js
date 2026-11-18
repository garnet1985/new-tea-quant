import React, { useState } from 'react';
import Column from 'ui/layout/column';
import Block from 'ui/layout/block';
import Section from 'ui/layout/section';
import Tabs from 'ui/layout/tabs';
import SideNav from 'ui/layout/sideNav';
import ListToolbar from 'ui/layout/listToolbar';
import CategoryChipStrip from 'ui/layout/categoryChipStrip';
import Accordion from 'ui/layout/accordion';
import Button from 'ui/button/button';
import SearchField from 'ui/input/searchField';
import Text from 'ui/text/text';
import {
  COLUMN_VARIANTS,
  RADIUS_TOKENS,
  SPACE_TOKENS,
  SURFACE_TOKENS,
  TABS_VARIANTS,
} from 'ui/tokens';
import { Showcase, SampleDim, SampleRow, SampleNA } from './sample';

/** 图鉴内演示：阻止真实跳转 */
function DemoLink({ to, children, className, onClick, ...rest }) {
  return (
    <a
      {...rest}
      href={to || '#'}
      className={className}
      onClick={(e) => {
        e.preventDefault();
        if (typeof onClick === 'function') onClick(e);
      }}
    >
      {children}
    </a>
  );
}

function DemoCell({ children }) {
  return <div className="ui-prototype__column-demo">{children}</div>;
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
              <div key={gap}>
                <p className="ntq-caption">
                  <Text variant="code">{`gap="${gap}"`}</Text>
                </p>
                <Column variant="halves" gap={gap}>
                  <DemoCell>甲</DemoCell>
                  <DemoCell>乙</DemoCell>
                </Column>
              </div>
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
        <SampleRow label="表面仅三档：透光 / 毛玻璃 / 渐变毛玻璃" block>
          <Section gap="sm">
            <Block surface="glass" radius="md" padding="sm" bordered>glass · 透光玻璃</Block>
            <Block surface="frost" radius="md" padding="sm" bordered>frost · 毛玻璃</Block>
            <Block surface="frost-strong" radius="md" padding="sm" bordered>frost-strong · 渐变毛玻璃</Block>
          </Section>
        </SampleRow>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleRow label={`radius：${RADIUS_TOKENS.join(' | ')}`} block>
          <Section gap="sm">
            {RADIUS_TOKENS.map((radius) => (
              <Block
                key={radius}
                surface="glass"
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
          <Block surface="frost-strong" radius="lg" bordered padding="md">
            渐变毛玻璃 + 描边 + 大圆角
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

const DEMO_TAB_ITEMS = [
  {
    id: 'overview',
    label: '概览',
    content: <p>概览面板：说明、摘要放这里。</p>,
  },
  {
    id: 'detail',
    label: '详情',
    content: (
      <Section gap="sm">
        <p>详情面板。</p>
        <p className="ntq-muted">可用任意块级内容。</p>
      </Section>
    ),
  },
  {
    id: 'logs',
    label: '日志',
    content: <p className="ntq-caption">日志 / 次要信息。</p>,
  },
  {
    id: 'disabled',
    label: '禁用',
    disabled: true,
    content: <p>不可见。</p>,
  },
];

function TabsShowcase() {
  const [sideValue, setSideValue] = useState('overview');

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label={`variant="top"（默认）· 上方切换`} block>
          <Tabs variant="top" items={DEMO_TAB_ITEMS.filter((i) => !i.disabled)} />
        </SampleRow>
        <SampleRow label={`variant="side" · 左右布局（左导航右内容）`} block>
          <Tabs
            variant="side"
            value={sideValue}
            onChange={setSideValue}
            items={DEMO_TAB_ITEMS}
          />
        </SampleRow>
        <SampleRow label={`variant 全集：${TABS_VARIANTS.join(' | ')}`} block>
          <SampleNA>仅 top / side 两种；不要再叠手写 tab 按钮。</SampleNA>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          无
          {' '}
          <Text variant="code">size</Text>
          ；侧栏宽跟
          {' '}
          <Text variant="code">--ntq-layout-sidebar-width</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleRow label='gap：列表与面板之间（默认 md = 1rem）' block>
          <Section gap="md">
            <Tabs
              variant="top"
              gap="sm"
              items={[
                { id: 'a', label: 'gap sm', content: <p>较紧</p> },
                { id: 'b', label: '另一页', content: <p>B</p> },
              ]}
            />
            <Tabs
              variant="top"
              gap="lg"
              items={[
                { id: 'a', label: 'gap lg', content: <p>较疏</p> },
                { id: 'b', label: '另一页', content: <p>B</p> },
              ]}
            />
          </Section>
        </SampleRow>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>激活态用青色指示条；无独立 tone 参数。</SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>
          top：底边指示条；side：左边指示条 + 浅底导航。窄屏 side 自动改横排。
        </SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function SideNavShowcase() {
  const [activeId, setActiveId] = useState('layout');
  const items = [
    { id: 'layout', label: '布局', to: '#layout', meta: 5 },
    { id: 'button', label: '按钮', to: '#button', meta: 2 },
    { id: 'input', label: '输入', to: '#input', meta: 12 },
    { id: 'disabled', label: '禁用项', to: '#x', meta: 0, disabled: true },
  ];

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label='variant="line"（图鉴侧栏）' block>
          <div style={{ maxWidth: '14rem' }}>
            <SideNav
              variant="line"
              activeId={activeId}
              items={items}
              linkComponent={DemoLink}
              onItemClick={setActiveId}
            />
          </div>
        </SampleRow>
        <SampleRow label='variant="rail"（设置风）' block>
          <div style={{ maxWidth: '14rem' }}>
            <SideNav
              variant="rail"
              activeId={activeId}
              items={items}
              linkComponent={DemoLink}
              onItemClick={setActiveId}
            />
          </div>
        </SampleRow>
        <SampleRow label="Column sidebar + SideNav 组合" block>
          <Column variant="sidebar" gap="none" divider="line">
            <Block surface="panel" radius="none" padding="sm" gap="sm">
              <SideNav
                variant="line"
                activeId={activeId}
                items={items.slice(0, 3)}
                linkComponent={DemoLink}
                onItemClick={setActiveId}
              />
            </Block>
            <Block surface="soft" padding="md" gap="none">
              <p className="ntq-muted" style={{ margin: 0 }}>
                右栏内容区（当前
                {' '}
                <Text variant="code">{activeId}</Text>
                ）
              </p>
            </Block>
          </Column>
        </SampleRow>
        <SampleRow label="sticky 贴顶" block>
          <Section gap="sm">
            <p className="ntq-caption" style={{ margin: 0 }}>
              仅菜单：
              {' '}
              <Text variant="code">SideNav sticky</Text>
              。整栏（标题+菜单）：
              {' '}
              <Text variant="code">Block sticky</Text>
              ，SideNav 不再开 sticky。
            </p>
            <div style={{ maxWidth: '14rem' }}>
              <SideNav
                sticky
                variant="line"
                activeId={activeId}
                items={items.slice(0, 3)}
                linkComponent={DemoLink}
                onItemClick={setActiveId}
              />
            </div>
          </Section>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          无独立 size；栏宽交给
          {' '}
          <Text variant="code">Column variant=&quot;sidebar&quot;</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>项间距 2px；内边距随 variant。</SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>
          选中
          {' '}
          <Text variant="code">--ntq-cyan</Text>
          ；meta 默认可选中同色。
        </SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>
          line=底边条；rail=左边条。同页绑内容用
          {' '}
          <Text variant="code">Tabs side</Text>
          ；全站顶栏用
          {' '}
          <Text variant="code">AppNav</Text>
          。
        </SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function ListToolbarShowcase() {
  const [q, setQ] = useState('');
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="search + actions + hint" block>
          <ListToolbar
            search={(
              <SearchField
                fluid
                surface="glass"
                label="搜索"
                placeholder="输入关键字"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            )}
            actions={(
              <>
                <Button variant="glass" icon="refresh">刷新</Button>
                <Button variant="primary" icon="add">新建</Button>
              </>
            )}
            hint="提示文案靠右"
          />
        </SampleRow>
      </SampleDim>
    </Showcase>
  );
}

function CategoryChipStripShowcase() {
  const [query, setQuery] = useState('');
  const groups = [
    { key: '动量', label: '动量', count: 3 },
    { key: '价值', label: '价值', count: 5 },
    { key: '事件', label: '事件', count: 2 },
  ];
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="全部 + 归类 chips" block>
          <CategoryChipStrip
            all={{
              label: '全部',
              count: 10,
              selected: !query,
              onClick: () => setQuery(''),
            }}
            items={groups.map((g) => ({
              key: g.key,
              label: g.label,
              count: g.count,
              selected: query === g.key,
              onClick: () => setQuery(query === g.key ? '' : g.key),
            }))}
          />
        </SampleRow>
      </SampleDim>
    </Showcase>
  );
}

function AccordionShowcase() {
  const [open, setOpen] = useState(true);
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label='variant="panel"' block>
          <Accordion
            title="全局设置"
            tooltip="顶层拼缝；收起仍挂载子树"
            defaultExpanded
          >
            <p className="ntq-muted" style={{ margin: 0 }}>panel 内容</p>
          </Accordion>
        </SampleRow>
        <SampleRow label='variant="nested"' block>
          <Accordion title="市场规则" variant="nested" defaultExpanded={false}>
            <p className="ntq-muted" style={{ margin: 0 }}>nested 内容</p>
          </Accordion>
        </SampleRow>
        <SampleRow label="受控 expanded" block>
          <Accordion title="受控示例" expanded={open} onExpandedChange={setOpen}>
            <p className="ntq-muted" style={{ margin: 0 }}>当前：{open ? '展开' : '收起'}</p>
          </Accordion>
        </SampleRow>
      </SampleDim>
      <SampleDim title="2. 大小"><SampleNA>无独立 size；标题字号固定。</SampleNA></SampleDim>
      <SampleDim title="3. 间距"><SampleNA>summary / details 内边距随 variant。</SampleNA></SampleDim>
      <SampleDim title="4. 颜色"><SampleNA>边框 / 表面走 --ntq-*。</SampleNA></SampleDim>
      <SampleDim title="5. 外观">
        <SampleNA>收起不卸载 children。设置页标题行可再包 SettingsAccordionTitle。</SampleNA>
      </SampleDim>
    </Showcase>
  );
}

const layoutShowcases = {
  column: ColumnShowcase,
  block: BlockShowcase,
  section: SectionShowcase,
  tabs: TabsShowcase,
  sideNav: SideNavShowcase,
  listToolbar: ListToolbarShowcase,
  categoryChipStrip: CategoryChipStripShowcase,
  accordion: AccordionShowcase,
};

export default layoutShowcases;
