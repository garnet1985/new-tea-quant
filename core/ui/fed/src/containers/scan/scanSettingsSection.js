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
        <div className="scan-settings__modes">
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
                description: '依赖数据须更新至最新交易日，否则中断并提示缺口。',
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

        <div className="scan-settings__post">
          <div className="scan-settings__post-head">
            <Heading level="h4" gap="none" className="scan-settings__label">
              扫描后处理
            </Heading>
            <Switch
              label="执行扫描后处理"
              checked={runPostProcess && enabledPostProcessors.length > 0}
              disabled={running || enabledPostProcessors.length === 0}
              onChange={onRunPostProcessChange}
              aria-label="执行扫描后处理"
            />
          </div>
          <p className="ntq-muted scan-settings__post-hint">
            默认开启；关闭会写入工作区偏好并跳过扫描后处理（可能产生费用），不改全局方案启用。
          </p>
          {enabledPostProcessors.length ? (
            <div
              className={[
                'scan-settings__chips',
                !runPostProcess ? 'scan-settings__chips--muted' : '',
              ].filter(Boolean).join(' ')}
            >
              {enabledPostProcessors.map((row) => (
                <Tag key={row.key} status="neutral" variant="solid">
                  {row.name || row.key}
                </Tag>
              ))}
            </div>
          ) : (
            <p className="ntq-muted">当前未启用任何扫描后处理方案。</p>
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
