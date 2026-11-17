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
          只约束「已入库数据怎么用」：起始日与截至日等，不会凭空补行情。
        </p>
        {loadError ? <Message status="error">{loadError}</Message> : null}
        {saveError ? <Message status="error">{saveError}</Message> : null}
        {saveOk ? <Message status="success">{saveOk}</Message> : null}
        <Message status="warning">
          <div className="settings-data__guide">
            <p>
              库里没有的区间或标的，把截至日拉长或起始日提前都不会生效——系统仍只能用已下载/导入的数据。
            </p>
            <p>
              自带演示数据大约是
              {' '}
              <strong>300 只股票、约 3 年</strong>
              （约 2023–2025 年底）。需要更长历史或全市场时，请先补数据，而不是只改本页：
            </p>
            <ul>
              <li>
                在
                {' '}
                <RouterLink className="ntq-link" to="/settings/membership">
                  设置 → 会员
                </RouterLink>
                {' '}
                装载凭证后，可到
                {' '}
                <RouterLink className="ntq-link" to="/settings/system">
                  设置 → 安装与维护
                </RouterLink>
                {' '}
                一键导入约 3 年全市场数据；也可在
                {' '}
                <RouterLink className="ntq-link" to="/advanced/data-sources">
                  高级功能 → 数据源
                </RouterLink>
                {' '}
                拉取。还没有账号时，请先到会员页注册。
              </li>
              <li>
                尚未导入数据时，可到
                {' '}
                <RouterLink className="ntq-link" to="/settings/system">
                  设置 → 安装与维护
                </RouterLink>
                ；会员凭证在
                {' '}
                <RouterLink className="ntq-link" to="/settings/membership">
                  设置 → 会员
                </RouterLink>
                。
              </li>
            </ul>
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
          hint="YYYYMMDD；空表 renew 与回测默认起点的全局地板。"
        />
        <UiTextField
          label="假定最新已完成交易日"
          value={assumedLatestCompletedDate}
          onChange={(e) => onAssumedLatestCompletedDateChange(e.target.value)}
          placeholder="留空表示跟真实日历"
          hint="扫描/回测假定的「今天」。留空则用实时最新已完成交易日。不裁剪日常数据续传截止。"
        />
        <div id="settings-retention">
          <UiTextField
            label="过时回测环境保留组数"
            value={simulationResultsMaxStaleEnvs}
            onChange={(e) => onSimulationResultsMaxStaleEnvsChange(e.target.value)}
            placeholder="5"
            hint="改代码或核心后旧环境不能再跑，最多留这么多组档案。超出则整组删除。当前环境不限份数。"
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
