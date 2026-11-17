import React, { useState } from 'react';
import PythonDictEditor from 'ui/ntq/pythonDictEditor';
import AppNav from 'ui/ntq/appNav';
import AppBrand from 'ui/ntq/appBrand';
import PageBanner from 'ui/ntq/pageBanner';
import AppBreadcrumbs from 'ui/ntq/appBreadcrumbs';
import ReportBlock from 'ui/ntq/reportBlock';
import MetricCard from 'ui/metric/metricCard';
import MetricGrid from 'ui/metric/metricGrid';
import NtqButton from 'ui/button/ntqButton';
import Text from 'ui/text/text';
import { Showcase, SampleDim, SampleRow, SampleNA } from './sample';

/**
 * 图鉴演示链：普通 <a>，阻止跳转。
 * 外层已有 BrowserRouter，禁止再包 MemoryRouter。
 */
function DemoLink({ to, children, className, onClick }) {
  return (
    <a
      href={typeof to === 'string' ? to : '#'}
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

const DEMO_NAV_ITEMS = [
  { label: '制定策略', to: '/strategy-design', icon: 'tactic' },
  { label: '策略选股', to: '/scan', icon: 'monitoring' },
  {
    label: '高级功能',
    icon: 'dataObject',
    match: '/advanced',
    children: [
      { label: '特征标签', to: '/advanced/tags' },
      { label: '数据源', to: '/advanced/data-sources' },
      { label: '序列关系', to: '/advanced/series-relation' },
    ],
  },
  { label: '文档', href: 'https://example.com/docs', icon: 'help' },
  { label: '设置', to: '/settings/membership', icon: 'settings', match: '/settings' },
];

function AppNavShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label='顶栏（pathname="/scan" 示意激活）' block>
          <div
            style={{
              display: 'flex',
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid var(--ntq-white-12)',
              borderRadius: 'var(--ntq-radius-sm)',
              overflow: 'auto',
            }}
          >
            <AppNav
              items={DEMO_NAV_ITEMS}
              pathname="/scan"
              linkComponent={DemoLink}
            />
          </div>
        </SampleRow>
        <SampleRow label="高级下拉展开态示意（悬停「高级功能」）" block>
          <p className="ntq-caption" style={{ margin: 0 }}>
            items 含
            {' '}
            <Text variant="code">children</Text>
            {' '}
            时渲染 Popper 菜单；路由表由应用传入。
          </p>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          高度对齐顶栏
          {' '}
          <Text variant="code">$ntq-header-height</Text>
          ；图标
          {' '}
          <Text variant="code">md</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>项间无 gap，靠按钮自身水平 padding。</SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>
          激活项青色
          {' '}
          <Text variant="code">--ntq-cyan</Text>
          ；下拉选中同色浅底。
        </SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>
          直角贴顶栏；下拉面板暗色描边。不内置
          {' '}
          <Text variant="code">fetchSiteUrls</Text>
          。
        </SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function AppBrandShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="徽标 + 彩虹字（DemoLink 不跳转）" block>
          <AppBrand
            linkComponent={DemoLink}
            version={<span className="ntq-caption">v0.3.0</span>}
          />
        </SampleRow>
      </SampleDim>
      <SampleDim title="2. 大小">
        <SampleNA>
          Logo 高 3.125rem；字号约 1.3rem。
        </SampleNA>
      </SampleDim>
      <SampleDim title="3. 间距">
        <SampleNA>徽标与文案 gap 0.625rem。</SampleNA>
      </SampleDim>
      <SampleDim title="4. 颜色">
        <SampleNA>
          名称用
          {' '}
          <Text variant="code">--ntq-brand-text-gradient</Text>
          。
        </SampleNA>
      </SampleDim>
      <SampleDim title="5. 外观">
        <SampleNA>图加载失败回退 tactic 图标。</SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function PageBannerShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="标题 + 说明" block>
          <PageBanner
            title="策略列表"
            description={(
              <>
                管理已导入的策略包。路径约定
                {' '}
                <code>strategies/*.json</code>
                。
              </>
            )}
          />
        </SampleRow>
        <SampleRow label="带 rightSlot" block>
          <PageBanner
            title="数据源"
            description="查看同步状态与运行入口。"
            rightSlot={(
              <NtqButton variant="glass" icon="refresh" size="small">
                刷新
              </NtqButton>
            )}
          />
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          标题
          {' '}
          <Text variant="code">font-xl</Text>
          ；最小高度约 7.25rem。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          内边距
          {' '}
          <Text variant="code">space-lg</Text>
          ；标题下
          {' '}
          <Text variant="code">space-md</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>
          说明用 muted；
          {' '}
          <Text variant="code">code</Text>
          浅底描边。
        </SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>
          无强制背景图；列宽由外层 content 约束。
        </SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function AppBreadcrumbsShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="祖先链 + 当前页" block>
          <AppBreadcrumbs
            items={[
              { label: '策略', to: '/strategies' },
            ]}
            current="动量策略"
            linkComponent={DemoLink}
          />
        </SampleRow>
        <SampleRow label="多层" block>
          <AppBreadcrumbs
            items={[
              { label: '设置', to: '/settings' },
              { label: '账户', to: '/settings/account' },
            ]}
            current="会员"
            linkComponent={DemoLink}
          />
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          字号
          {' '}
          <Text variant="code">font-xs</Text>
          ；分隔图标
          {' '}
          <Text variant="code">sm</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>分隔两侧 0.375rem；与 Banner 间距交给父级 gap。</SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>
          祖先 muted；当前
          {' '}
          <Text variant="code">--ntq-text</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>chevronRight 分隔；需在 Router 树内。</SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function ReportBlockShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="标题 + tip + MetricGrid" block>
          <ReportBlock title="机会盘点" tip="统计窗口内触发次数">
            <MetricGrid columns={2}>
              <MetricCard title="机会总数" value="128" />
              <MetricCard title="完整度" value="96%" />
            </MetricGrid>
          </ReportBlock>
        </SampleRow>
        <SampleRow label="带 action" block>
          <ReportBlock
            title="涨跌停"
            action={(
              <NtqButton variant="ghost" size="small" icon="refresh">
                刷新
              </NtqButton>
            )}
          >
            <p className="ntq-muted" style={{ margin: 0 }}>
              内容区放 MetricGrid / ChartPanel / 文案均可。
            </p>
          </ReportBlock>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          标题
          {' '}
          <Text variant="code">font-sm</Text>
          ；内边距 0.625rem。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          头与内容
          {' '}
          <Text variant="code">space-sm</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>
          描边
          {' '}
          <Text variant="code">white-12</Text>
          ；浅底
          {' '}
          <Text variant="code">white-06</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>
          固定报告壳；不要再复制
          {' '}
          <Text variant="code">views/sectionBlock</Text>
          。
        </SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function PythonDictEditorShowcase() {
  const [text, setText] = useState('{\n  "alpha": 1,\n  "enabled": true\n}\n');
  const [parseError, setParseError] = useState('');
  const [errorContext, setErrorContext] = useState([]);

  const validate = () => {
    try {
      JSON.parse(text);
      setParseError('');
      setErrorContext([]);
    } catch (err) {
      const msg = err?.message || 'JSON 解析失败';
      setParseError(msg);
      const lines = String(text || '').split('\n');
      setErrorContext(
        lines.slice(0, 5).map((line, i) => ({
          lineNo: i + 1,
          text: line,
          isError: i === 0,
        })),
      );
    }
  };

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="验证 + 错误上下文" block>
          <PythonDictEditor
            title="样例输入"
            value={text}
            onChange={setText}
            onApply={validate}
            onLoadDefault={() => {
              setText('{\n  "alpha": 1\n}\n');
              setParseError('');
              setErrorContext([]);
            }}
            parseError={parseError}
            errorLine={parseError ? 1 : 0}
            errorColumn={parseError ? 1 : 0}
            errorContext={errorContext}
          />
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>编辑区默认约 18 行；面板拉满父级宽度。</SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>Block gap md；工具栏按钮 gap sm。</SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>错误用 Message status=error；上下文行 is-error 高亮。</SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>surface soft + bordered；业务页可换 title / 回调。</SampleNA>
      </SampleDim>
    </Showcase>
  );
}

const ntqShowcases = {
  appNav: AppNavShowcase,
  appBrand: AppBrandShowcase,
  pageBanner: PageBannerShowcase,
  appBreadcrumbs: AppBreadcrumbsShowcase,
  reportBlock: ReportBlockShowcase,
  pythonDictEditor: PythonDictEditorShowcase,
};

export default ntqShowcases;
