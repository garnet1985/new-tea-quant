import React from 'react';
import { Navigate, useLocation, useParams } from 'react-router-dom';
import Section from 'ui/layout/section';
import Block from 'ui/layout/block';
import Text from 'ui/text/text';
import Heading from 'ui/text/heading';
import PageBanner from 'ui/ntq/pageBanner';
import Tag from 'ui/tag/tag';
import {
  UI_CATALOG_BASE,
  categoryPath,
  getCategory,
  originLabel,
  resolveCategoryId,
  statusLabel,
  widgetUiPath,
} from './catalog';
import { getWidgetDoc } from './widgetDocs';
import { getWidgetShowcase } from './showcases';

function WidgetDocPanel({ doc, readmePath }) {
  if (!doc) {
    return (
      <p className="ntq-muted">
        参数与使用场景文档见
        {' '}
        <Text variant="code">{readmePath}</Text>
        。实现后会在此展示样例与规范摘要。
      </p>
    );
  }

  return (
    <Section className="ui-prototype__widget-doc-panel" gap="md">
      <p className="ntq-muted ui-prototype__widget-summary">{doc.summary}</p>

      <Section className="ui-prototype__doc-section" gap="md">
        <Heading level="h5" variant="bar" tone="cyan" gap="none">参数</Heading>
        <div className="ui-prototype__doc-table-wrap">
          <table className="ui-prototype__doc-table">
            <thead>
              <tr>
                <th>参数</th>
                <th>类型</th>
                <th>默认</th>
                <th>说明</th>
              </tr>
            </thead>
            <tbody>
              {doc.params.map((param) => (
                <tr key={param.name}>
                  <td><code>{param.name}</code></td>
                  <td><code>{param.type}</code></td>
                  <td><code>{param.defaultValue}</code></td>
                  <td>{param.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section className="ui-prototype__doc-section" gap="md">
        <Heading level="h5" variant="bar" tone="cyan" gap="none">使用场景</Heading>
        <ul className="ui-prototype__doc-list">
          {doc.scenarios.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </Section>

      {doc.antiPatterns?.length ? (
        <Section className="ui-prototype__doc-section" gap="md">
          <Heading level="h5" variant="bar" tone="error" gap="none">反例</Heading>
          <Block surface="soft" radius="md" padding="md" bordered>
            <ul className="ui-prototype__doc-list">
              {doc.antiPatterns.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </Block>
        </Section>
      ) : null}

      <p className="ntq-caption ui-prototype__doc-readme">
        完整文档：
        {' '}
        <Text variant="code">{readmePath}</Text>
      </p>
    </Section>
  );
}

function UiPrototypeCategoryPage() {
  const { categoryId } = useParams();
  const location = useLocation();
  const resolvedId = resolveCategoryId(categoryId);
  const category = getCategory(resolvedId);

  if (!category) {
    return <Navigate to={UI_CATALOG_BASE} replace />;
  }

  if (categoryId && resolvedId !== categoryId) {
    return (
      <Navigate
        to={`${categoryPath(resolvedId)}${location.hash || ''}`}
        replace
      />
    );
  }

  return (
    <Section className="ui-prototype__panel" gap="lg">
      <PageBanner
        className="ui-prototype__panel-banner"
        title={category.label}
        description={(
          <>
            {category.description}
            {' '}
            <span className="ui-prototype__path-hint-inline">
              路由
              {' '}
              <Text variant="code">{categoryPath(category.id)}</Text>
              {' · '}
              目录
              {' '}
              <Text variant="code">src/ui/</Text>
            </span>
          </>
        )}
      />

      <Section className="ui-prototype__widget-list" gap="lg">
        {category.widgets.length === 0 ? (
          <Block
            className="ui-prototype__widget-item ui-prototype__guidelines-empty"
            bordered
            padding="md"
            gap="md"
          >
            <Heading level="h2" gap="none">占位 · 待补充</Heading>
            <p className="ntq-muted" style={{ margin: 0, maxWidth: '40rem' }}>
              这里将沉淀 NTQ 产品页的布局与组合准则（例如：设置类用 Tabs side / SideNav；
              报告小节用 ReportBlock；同页切 panel 用 Tabs；目录站用 Column sidebar + SideNav 等）。
              迁 legacy 时按场景补条目，避免各页自造版式。
            </p>
            <p className="ntq-caption" style={{ margin: 0 }}>
              条目形态后续再定（纯文案 / 对照表 / 链到组件锚点均可）。
            </p>
          </Block>
        ) : category.widgets.map((widget) => {
          const uiDir = widgetUiPath(category.id, widget);
          const readmePath = `src/ui/${uiDir}/README.md`;
          const doc = getWidgetDoc(category.id, widget.id);
          const Showcase = getWidgetShowcase(category.id, widget.id);

          return (
            <Block
              key={widget.id}
              id={widget.id}
              className="ui-prototype__widget-item"
              bordered
              padding="md"
              gap="md"
            >
              <div className="ui-prototype__widget-header">
                <Heading level="h2" gap="none" className="ui-prototype__widget-name">
                  {widget.label}
                </Heading>
                <div className="ui-prototype__widget-meta">
                  <Tag
                    status={widget.status === 'ready' ? 'success' : 'neutral'}
                    variant={widget.status === 'ready' ? 'soft' : 'outline'}
                    size="sm"
                  >
                    {statusLabel(widget.status)}
                  </Tag>
                  <Tag status="neutral" variant="outline" size="sm">
                    {originLabel(widget.origin)}
                  </Tag>
                  {widget.source ? (
                    <Tag status="info" variant="outline" size="sm">
                      来源
                      {' '}
                      {widget.source}
                    </Tag>
                  ) : null}
                </div>
              </div>

              <WidgetDocPanel doc={doc} readmePath={readmePath} />

              <Section gap="md">
                <Heading level="h5" variant="bar" tone="cyan" gap="none">样例</Heading>
                <div
                  className={[
                    'ui-prototype__widget-sample',
                    Showcase ? '' : 'is-empty',
                  ].filter(Boolean).join(' ')}
                >
                  {Showcase ? (
                    <Showcase />
                  ) : (
                    <p className="ntq-caption">样例占位（尚未实现）</p>
                  )}
                </div>
              </Section>
            </Block>
          );
        })}
      </Section>
    </Section>
  );
}

export default UiPrototypeCategoryPage;
