import React, { useState } from 'react';
import PythonDictEditor from 'ntq-ui/pythonDictEditor';
import AppNav from 'ntq-ui/appNav';
import AppBrand from 'ntq-ui/appBrand';
import AppVersionMark from 'ntq-ui/appVersion';
import PageBanner from 'ntq-ui/pageBanner';
import AppBreadcrumbs from 'ntq-ui/appBreadcrumbs';
import ReportBlock from 'ntq-ui/reportBlock';
import PageLayout from 'ntq-ui/pageLayout';
import MemberStrip from 'ntq-ui/memberStrip';
import ProBadge from 'ntq-ui/proBadge';
import BecomeMemberLink from 'ntq-ui/becomeMemberLink';
import DescriptionText from 'ntq-ui/descriptionText';
import PageBackground from 'ntq-ui/pageBackground';
import UpdateStatusChip from 'ntq-ui/updateStatusChip';
import { GlobalHelperOverlay } from 'ntq-ui/globalHelper';
import RainbowButton from 'ntq-ui/rainbowButton';
import MetricCard from 'ui/metric/metricCard';
import MetricGrid from 'ui/metric/metricGrid';
import Button from 'ui/button/button';
import Text from 'ui/text/text';
import { Showcase, SampleDim, SampleRow, SampleNA } from './sample';

/**
 * 图鉴演示链：普通 <a>，阻止跳转。
 * 外层已有 BrowserRouter，禁止再包 MemoryRouter。
 */
function DemoLink({ to, children, className, onClick }) {
  const href = typeof to === 'string' && to ? to : '/';
  return (
    <a
      href={href}
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
      { label: '数据源接入', to: '/advanced/data-sources' },
      { label: '走势关联', to: '/advanced/series-relation' },
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
          <Text variant="code">--ntq-header-height</Text>
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

function AppVersionShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="版本号">
          <AppVersionMark label="v0.3.0" />
        </SampleRow>
      </SampleDim>
      <SampleDim title="2. 大小">
        <SampleNA>
          字号
          {' '}
          <Text variant="code">font-xs</Text>
          。
        </SampleNA>
      </SampleDim>
      <SampleDim title="3. 间距">
        <SampleNA>由 AppBrand meta 行排布。</SampleNA>
      </SampleDim>
      <SampleDim title="4. 颜色">
        <SampleNA>muted 字色。</SampleNA>
      </SampleDim>
      <SampleDim title="5. 外观">
        <SampleNA>纯 span；无边框。</SampleNA>
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
            version={<AppVersionMark label="v0.3.0" />}
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
            title="数据源接入"
            description="查看同步状态与运行入口。"
            rightSlot={(
              <Button variant="glass" icon="refresh" size="small">
                刷新
              </Button>
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
              <Button variant="ghost" size="small" icon="refresh">
                刷新
              </Button>
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
          <Text variant="code">ntq-ui/reportBlock</Text>
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

function PageLayoutShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="面包屑 + Banner + 正文" block>
          <PageLayout
            breadcrumbsItems={[{ label: '制定策略', to: '#' }]}
            breadcrumbsCurrent="设置"
            bannerTitle="设置"
            bannerDescription="系统安装与会员等。"
          >
            <p className="ntq-muted" style={{ margin: 0 }}>正文区域</p>
          </PageLayout>
        </SampleRow>
      </SampleDim>
      <SampleDim title="2. 大小"><SampleNA>跟 Banner / 面包屑。</SampleNA></SampleDim>
      <SampleDim title="3. 间距"><SampleNA>页 padding md；正文上边距 0.75rem。</SampleNA></SampleDim>
      <SampleDim title="4. 颜色"><SampleNA>无额外表面。</SampleNA></SampleDim>
      <SampleDim title="5. 外观"><SampleNA>loading 时用 Loading page。</SampleNA></SampleDim>
    </Showcase>
  );
}

function MemberStripShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="已登录 + Pro + 猫粮（相对定位示意）" block>
          <div style={{ position: 'relative', height: '3rem', borderBottom: '1px solid var(--ntq-white-12)' }}>
            <MemberStrip
              signedIn
              name="茶茶"
              isPro
              catfoodText="12.50"
              chipTitle="示意"
              linkComponent={DemoLink}
            />
          </div>
        </SampleRow>
        <SampleRow label="未登录" block>
          <div style={{ position: 'relative', height: '3rem', borderBottom: '1px solid var(--ntq-white-12)' }}>
            <MemberStrip guestReason="missing" registerUrl="https://example.com" />
          </div>
        </SampleRow>
      </SampleDim>
      <SampleDim title="2. 大小"><SampleNA>挂角高 36px；头像 24px。</SampleNA></SampleDim>
      <SampleDim title="3. 间距"><SampleNA>chip 内 gap sm。</SampleNA></SampleDim>
      <SampleDim title="4. 颜色"><SampleNA>Pro 用 ProBadge；猫粮值青色。</SampleNA></SampleDim>
      <SampleDim title="5. 外观"><SampleNA>绝对定位挂在顶栏右下；container 负责 fetch。</SampleNA></SampleDim>
    </Showcase>
  );
}

function ProBadgeShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="默认">
          <ProBadge />
        </SampleRow>
      </SampleDim>
      <SampleDim title="2. 大小"><SampleNA>约 10px 字 + pill。</SampleNA></SampleDim>
      <SampleDim title="3. 间距"><SampleNA>不适用。</SampleNA></SampleDim>
      <SampleDim title="4. 颜色"><SampleNA>品牌彩虹字 + 描边。</SampleNA></SampleDim>
      <SampleDim title="5. 外观"><SampleNA>勿在业务复制 SCSS。</SampleNA></SampleDim>
    </Showcase>
  );
}

function BecomeMemberLinkShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label='variant="button" | "link"'>
          <BecomeMemberLink href="https://example.com/register" />
          <BecomeMemberLink href="https://example.com/register" variant="link" />
        </SampleRow>
        <SampleRow label="href 为空：不渲染">
          <BecomeMemberLink href="" />
          <span className="ntq-muted">（左侧应为空）</span>
        </SampleRow>
      </SampleDim>
      <SampleDim title="2. 大小"><SampleNA>跟随 Button / 行内链。</SampleNA></SampleDim>
      <SampleDim title="3. 间距"><SampleNA>不适用。</SampleNA></SampleDim>
      <SampleDim title="4. 颜色"><SampleNA>button=glass；link=.ntq-link。</SampleNA></SampleDim>
      <SampleDim title="5. 外观">
        <SampleNA>
          外链示意：button 自动后置 chevronRight；link 显式后置图标。href 由应用传入，组件不 fetch。
        </SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function DescriptionTextShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="多行" block>
          <DescriptionText
            className="ntq-muted"
            text={'第一行说明。\n第二行补充。\n第三行细节。'}
          />
        </SampleRow>
        <SampleRow label="maxLines={2}" block>
          <DescriptionText
            className="ntq-muted"
            maxLines={2}
            text={'很长的说明会被截断到两行。\n第二行。\n第三行看不到。'}
          />
        </SampleRow>
        <SampleRow label="empty">
          <DescriptionText text="" />
        </SampleRow>
      </SampleDim>
      <SampleDim title="2. 大小"><SampleNA>字号跟随 className / 父级。</SampleNA></SampleDim>
      <SampleDim title="3. 间距"><SampleNA>多行时行间距由 .ntq-description__line 控制。</SampleNA></SampleDim>
      <SampleDim title="4. 颜色"><SampleNA>调用方 className（如 ntq-muted）。</SampleNA></SampleDim>
      <SampleDim title="5. 外观">
        <SampleNA>拆行规则与策略描述一致；非 Markdown。</SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function PageBackgroundShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleNA>
          壳层装饰组件（fixed + 100vw full-bleed，滚动不跟着走），图鉴内不宜实嵌以免撑破布局。
          见应用主内容区背后的模糊背景图。
        </SampleNA>
        {/* 保留 import 校验：组件可挂载；视觉在壳层 */}
        <div hidden aria-hidden>
          <PageBackground />
        </div>
      </SampleDim>
      <SampleDim title="2. 大小"><SampleNA>宽 100vw；高 --ntq-page-bg-height。</SampleNA></SampleDim>
      <SampleDim title="3. 间距"><SampleNA>不适用。</SampleNA></SampleDim>
      <SampleDim title="4. 颜色"><SampleNA>照片 + veil 渐变遮罩。</SampleNA></SampleDim>
      <SampleDim title="5. 外观">
        <SampleNA>图库随机；无图返回 null。业务页勿重复挂载。</SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function UpdateStatusChipShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="status 映射">
          <UpdateStatusChip status="up_to_date" label="最新" />
          <UpdateStatusChip status="needs_update" label="需更新" hint="源数据有变更" />
          <UpdateStatusChip status="needs_recompute" label="需重算" hint="依赖已变" />
          <UpdateStatusChip status="unknown" label="未知" />
        </SampleRow>
        <SampleRow label="pending">
          <UpdateStatusChip pending label="检查中…" />
        </SampleRow>
      </SampleDim>
      <SampleDim title="2. 大小"><SampleNA>跟随 Tag / Loading。</SampleNA></SampleDim>
      <SampleDim title="3. 间距"><SampleNA>hint 与 Tag 间距由组件 SCSS 控制。</SampleNA></SampleDim>
      <SampleDim title="4. 颜色">
        <SampleNA>up_to_date=success solid；needs_*=warning outline；其它=neutral outline。</SampleNA>
      </SampleDim>
      <SampleDim title="5. 外观">
        <SampleNA>文案由 label 传入；映射规则集中在本组件。</SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function GlobalHelperShowcase() {
  const [demo, setDemo] = useState(null);

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="无洞全屏 dim（单页 → 仅「我知道了」）" block>
          <Button variant="glass" onClick={() => setDemo('plain')}>
            打开单页引导
          </Button>
        </SampleRow>
        <SampleRow label="挖洞聚焦 + 多页（有「下一页」）" block>
          <Button variant="glass" onClick={() => setDemo('spot')}>
            打开挖洞引导
          </Button>
          <div
            data-ntq-help-demo="spot-target"
            style={{
              marginTop: 'var(--ntq-space-md)',
              padding: 'var(--ntq-space-md)',
              border: '1px solid var(--ntq-white-12)',
              borderRadius: 'var(--ntq-radius-md)',
              color: 'var(--ntq-text)',
            }}
          >
            示意目标区域（挖洞会罩在这块上）
          </div>
        </SampleRow>
        <SampleRow label="问号 FAB（产品里 fixed 挂右上）" block>
          <RainbowButton
            size="lg"
            ring="still"
            mark="help"
            onClick={() => setDemo('plain')}
            aria-label="打开页面引导"
          />
          <SampleNA>
            产品由
            {' '}
            <Text variant="code">containers/globalHelper</Text>
            Host 按路由挂载
            {' '}
            <Text variant="code">GlobalHelperButton</Text>
            ；图鉴只演示壳。
          </SampleNA>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 按钮">
        <SampleNA>
          有后续 →「下一页」；末页 / 单页 → 只留「我知道了」。不放「跳过」（与下一页语义重复）。角标 X 关闭。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 颜色">
        <SampleNA>
          遮罩 / 描边 / 卡片走
          {' '}
          <Text variant="code">--ntq-ink</Text>
          、
          <Text variant="code">--ntq-cyan</Text>
          、
          <Text variant="code">--ui-surface-panel</Text>
          等基础变量，不用硬编码色。
        </SampleNA>
      </SampleDim>

      {demo === 'plain' ? (
        <GlobalHelperOverlay
          hole={null}
          title="欢迎使用 NTQ"
          body="单页说明示例：不聚焦任何元素。点「我知道了」或右上角关闭。"
          isFirst
          isLast
          onNext={() => setDemo(null)}
          onClose={() => setDemo(null)}
        />
      ) : null}

      {demo === 'spot' ? (
        <GlobalHelperOverlay
          hole={{ left: 48, top: 180, width: 280, height: 72 }}
          title="挖洞步骤"
          body="多页时会出现「下一页」。本示意洞位置固定，真实产品按 data-ntq-help 测量。"
          stepLabel="1 / 2"
          isFirst
          isLast={false}
          onNext={() => setDemo('spot-last')}
          onClose={() => setDemo(null)}
        />
      ) : null}

      {demo === 'spot-last' ? (
        <GlobalHelperOverlay
          hole={{ left: 48, top: 180, width: 280, height: 72 }}
          title="最后一页"
          body="末页没有「下一页」，只剩「我知道了」。"
          stepLabel="2 / 2"
          isFirst={false}
          isLast
          onPrev={() => setDemo('spot')}
          onNext={() => setDemo(null)}
          onClose={() => setDemo(null)}
        />
      ) : null}
    </Showcase>
  );
}

const ntqShowcases = {
  appNav: AppNavShowcase,
  appBrand: AppBrandShowcase,
  appVersion: AppVersionShowcase,
  pageBanner: PageBannerShowcase,
  appBreadcrumbs: AppBreadcrumbsShowcase,
  pageLayout: PageLayoutShowcase,
  memberStrip: MemberStripShowcase,
  proBadge: ProBadgeShowcase,
  becomeMemberLink: BecomeMemberLinkShowcase,
  reportBlock: ReportBlockShowcase,
  pythonDictEditor: PythonDictEditorShowcase,
  descriptionText: DescriptionTextShowcase,
  pageBackground: PageBackgroundShowcase,
  updateStatusChip: UpdateStatusChipShowcase,
  globalHelper: GlobalHelperShowcase,
};

export default ntqShowcases;
