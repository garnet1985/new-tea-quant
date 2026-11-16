import React from 'react';
import { Box } from '@mui/material';
import { Navigate, useParams } from 'react-router-dom';
import Section from 'ui/layout/section';
import Block from 'ui/layout/block';
import Text from 'ui/text/text';
import Heading from 'ui/text/heading';
import TextBlock from 'ui/text/textBlock';
import {
  UI_CATALOG_BASE,
  categoryPath,
  getCategory,
  originLabel,
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
      <TextBlock bar="cyan" surface="soft" className="ui-prototype__widget-summary">
        {doc.summary}
      </TextBlock>

      <Section className="ui-prototype__doc-section" gap="md">
        <Heading level="h5" variant="bar" tone="cyan" gap="none">参数</Heading>
        <Box className="ui-prototype__doc-table-wrap">
          <Box component="table" className="ui-prototype__doc-table">
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
          </Box>
        </Box>
      </Section>

      <Section className="ui-prototype__doc-section" gap="md">
        <Heading level="h5" variant="bar" tone="cyan" gap="none">使用场景</Heading>
        <ul className="ui-prototype__doc-list">
          {doc.scenarios.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </Section>

      <Section className="ui-prototype__doc-section" gap="md">
        <Heading level="h5" variant="bar" tone="warning" gap="none">反例</Heading>
        {/* 上方已有竖条标题，下方用普通 Block，避免双竖条 */}
        <Block surface="soft" radius="md" padding="md" bordered>
          <ul className="ui-prototype__doc-list">
            {doc.antiPatterns.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Block>
      </Section>

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
  const category = getCategory(categoryId);

  if (!category) {
    return <Navigate to={UI_CATALOG_BASE} replace />;
  }

  return (
    <Section className="ui-prototype__panel" gap="lg">
      <Block className="ui-prototype__panel-header" padding="none" gap="md">
        <Heading level="h1" gap="none" className="ui-prototype__title">
          {category.label}
        </Heading>
        <p className="ntq-muted ui-prototype__lead">{category.description}</p>
        <p className="ntq-caption ui-prototype__path-hint">
          路由
          {' '}
          <Text variant="code">{categoryPath(category.id)}</Text>
          {' · '}
          目录
          {' '}
          <Text variant="code">{`src/ui/`}</Text>
          （各组件见条目路径）
        </p>
      </Block>

      <Section className="ui-prototype__widget-list" gap="lg">
        {category.widgets.map((widget) => {
          const uiDir = widgetUiPath(category.id, widget);
          const readmePath = `src/ui/${uiDir}/README.md`;
          const doc = getWidgetDoc(category.id, widget.id);
          const Showcase = getWidgetShowcase(category.id, widget.id);
          const statusChipClass = widget.status === 'ready'
            ? 'ui-prototype__chip ui-prototype__chip--ready'
            : 'ui-prototype__chip ui-prototype__chip--stub';

          return (
            <Block
              key={widget.id}
              id={widget.id}
              className="ui-prototype__widget-item"
              bordered
              padding="md"
              gap="md"
            >
              <Box className="ui-prototype__widget-header">
                <Heading level="h3" gap="none" className="ui-prototype__widget-name">
                  {widget.label}
                </Heading>
                <Box className="ui-prototype__widget-meta">
                  <span className={statusChipClass}>
                    {statusLabel(widget.status)}
                  </span>
                  <span className="ui-prototype__chip">
                    {originLabel(widget.origin)}
                  </span>
                  {widget.source ? (
                    <span className="ui-prototype__chip">
                      来源
                      {' '}
                      <code>{widget.source}</code>
                    </span>
                  ) : null}
                </Box>
              </Box>

              <WidgetDocPanel doc={doc} readmePath={readmePath} />

              <Section gap="md">
                <Heading level="h5" variant="bar" tone="cyan" gap="none">样例</Heading>
                <Box
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
                </Box>
              </Section>
            </Block>
          );
        })}
      </Section>
    </Section>
  );
}

export default UiPrototypeCategoryPage;
