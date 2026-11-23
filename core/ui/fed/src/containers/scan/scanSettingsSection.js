import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Button,
  Heading,
  RadioGroup,
  Section,
  Switch,
  Tag,
} from 'ui';

/** 扫描模式 + 后处理偏好。 */
export default function ScanSettingsSection({
  mode,
  running,
  demoDesc,
  runPostProcess,
  enabledPostProcessors,
  onModeChange,
  onRunPostProcessChange,
}) {
  return (
    <Section className="scan-section scan-section--settings" gap="none">
      <div className="scan-settings">
        <div className="scan-settings__modes" data-ntq-help="scan-mode">
          <RadioGroup
            label="扫描模式"
            variant="button"
            direction="row"
            value={mode}
            disabled={running}
            className="scan-mode-options"
            onChange={onModeChange}
            options={[
              {
                value: 'strict',
                label: '严格模式',
                description: '您的数据必须最新才能进行扫描。',
              },
              {
                value: 'demo',
                label: '扫描演示',
                description: demoDesc,
              },
            ]}
          />
        </div>

        <div className="scan-settings__divider" aria-hidden />

        <div className="scan-settings__post" data-ntq-help="scan-post-process">
          <div className="scan-settings__post-head">
            <Heading level="h4" gap="none" className="scan-settings__label">
              扫描后处理
            </Heading>
            <Switch
              label="是否开启？"
              checked={runPostProcess && enabledPostProcessors.length > 0}
              disabled={running || enabledPostProcessors.length === 0}
              onChange={onRunPostProcessChange}
              aria-label="是否开启扫描后的机会处理"
            />
          </div>
          <p className="ntq-muted scan-settings__post-hint">
            当您使用策略扫描到机会后的处理方案。
          </p>
          {enabledPostProcessors.length ? (
            <div
              className={[
                'scan-settings__plans',
                !runPostProcess ? 'scan-settings__plans--muted' : '',
              ].filter(Boolean).join(' ')}
            >
              {enabledPostProcessors.map((row) => {
                const byName = {};
                (row.adapters || []).forEach((step) => {
                  if (step?.name) byName[step.name] = step;
                });
                const order = (row.execution_order || []).length
                  ? row.execution_order
                  : (row.adapters || []).map((step) => step.name).filter(Boolean);
                const stepLabels = order.map((name) => {
                  const hit = byName[name];
                  return String(hit?.display_name || name).trim() || name;
                });
                return (
                  <div key={row.key} className="scan-settings__plan">
                    <Tag status="neutral" variant="solid">
                      {row.name || row.key}
                    </Tag>
                    {stepLabels.length ? (
                      <span className="scan-settings__plan-steps ntq-muted">
                        {stepLabels.join(' → ')}
                      </span>
                    ) : null}
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="ntq-muted">当前未启用任何扫描到机会后的处理方案。</p>
          )}
          <div className="scan-settings__post-actions">
            <Button
              variant="glass"
              icon="chevronRight"
              iconPlacement="end"
              iconSize="sm"
              component={RouterLink}
              to="/advanced/post-process"
              className="scan-design-btn"
            >
              管理扫描后处理
            </Button>
          </div>
        </div>
      </div>
    </Section>
  );
}
