import React, { useEffect } from 'react';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import {
  Heading,
  Loading,
  Message,
  Button,
  Section,
  TextField as UiTextField,
} from 'ui';

export function SettingsDataPanel({
  loading,
  loadError,
  saveError,
  saveOk,
  saving,
  defaultStartDate,
  assumedLatestCompletedDate,
  simulationResultsMaxStaleEnvs,
  onDefaultStartDateChange,
  onAssumedLatestCompletedDateChange,
  onSimulationResultsMaxStaleEnvsChange,
  onSave,
  onReload,
}) {
  const location = useLocation();

  useEffect(() => {
    if (loading) return undefined;
    if (location.hash !== '#retention') return undefined;
    const el = document.getElementById('settings-retention');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    return undefined;
  }, [loading, location.hash]);

  if (loading) {
    return <Loading variant="inline" message="正在加载数据配置…" />;
  }

  return (
    <Section className="settings-data" gap="lg">
      <Section className="settings-data__intro" gap="md">
        <Heading level="h3" gap="none">数据范围</Heading>
        <p className="ntq-muted">
          数据范围会定义您的数据默认起点和终点。可以包含和切断您的实际数据范围。所有功能（除去数据更新）都会给予当前数据范围进行操作。
        </p>
        {loadError ? <Message status="error">{loadError}</Message> : null}
        {saveError ? <Message status="error">{saveError}</Message> : null}
        {saveOk ? <Message status="success">{saveOk}</Message> : null}
        <Message status="warning">
          <div className="settings-data__guide">
            建议将您的数据区间配置成和数据库一致的区间。如果您是使用演示数据，那么默认起点是2023年1月1日，截止日期（假定最新已经完结的交易日）是2025年12月31日。
          </div>
        </Message>
      </Section>

      <Section className="settings-data__fields" gap="md">
        <Heading level="h3" gap="none">范围与保留</Heading>
        <UiTextField
          label="默认起始日期"
          value={defaultStartDate}
          onChange={(e) => onDefaultStartDateChange(e.target.value)}
          placeholder="20080101"
          hint="时间格式是：YYYYMMDD"
        />
        <UiTextField
          label="假定最新已经完结的交易日"
          value={assumedLatestCompletedDate}
          onChange={(e) => onAssumedLatestCompletedDateChange(e.target.value)}
          placeholder="留空表示跟真实日历"
          hint="时间格式是：YYYYMMDD。"
        />
        <div id="settings-retention">
          <UiTextField
            label="过期回测结果最多保留组数"
            value={simulationResultsMaxStaleEnvs}
            onChange={(e) => onSimulationResultsMaxStaleEnvsChange(e.target.value)}
            placeholder="5"
            hint="策略或系统更新后，旧回测不能再跑，只作存档。这里限制这类存档最多留几组；超出会自动删最旧的一组。当前版本的新结果不受限。"
          />
        </div>
      </Section>

      <Section className="settings-data__form-actions" gap="md">
        <div className="settings-data__actions">
          <Button variant="primary" onClick={onSave} disabled={saving}>
            {saving ? '保存中…' : '保存数据设置'}
          </Button>
          <Button
            variant="glass"
            icon="refresh"
            iconSize="sm"
            onClick={onReload}
            disabled={saving}
          >
            重新读取
          </Button>
        </div>
      </Section>
    </Section>
  );
}
