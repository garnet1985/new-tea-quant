import React, { useCallback, useEffect, useMemo } from 'react';
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { Box, Paper, Tab, Tabs } from '@mui/material';
import {
  fetchDatabaseSettings,
  fetchDataSettings,
  saveDatabaseSettings,
  saveDataSettings,
} from '../../api/settingsApi';
import PageLayout from '../../views/pageLayout';
import {
  SettingsAgentPanel,
  SettingsAssistantPanel,
  SettingsCachePanel,
  SettingsDataPanel,
  SettingsDatabasePanel,
  SettingsFeedbackAndTracePanel,
  SettingsMembershipPanel,
  SettingsSystemPanel,
} from './settingsPanels';
import './settingsPage.scss';

const SETTINGS_TABS = [
  { id: 'membership', label: '会员', path: 'membership' },
  { id: 'system', label: '安装与维护', path: 'system' },
  { id: 'database', label: '数据库', path: 'database' },
  { id: 'ai', label: 'AI 配置', path: 'ai' },
  { id: 'agent', label: 'Agent 配置', path: 'agent' },
  { id: 'data', label: '数据范围', path: 'data' },
  { id: 'cache', label: '缓存管理', path: 'cache' },
  { id: 'feedback', label: '反馈与统计', path: 'feedback' },
];

function useSettingsSection() {
  const location = useLocation();
  return useMemo(() => {
    const tail = location.pathname.replace(/\/+$/, '').split('/').pop() || '';
    const found = SETTINGS_TABS.find((tab) => tab.path === tail);
    return found ? found.path : 'membership';
  }, [location.pathname]);
}

function SettingsPage() {
  const navigate = useNavigate();
  const section = useSettingsSection();

  const [loading, setLoading] = React.useState(true);
  const [loadError, setLoadError] = React.useState('');
  const [saveError, setSaveError] = React.useState('');
  const [saveOk, setSaveOk] = React.useState('');
  const [saving, setSaving] = React.useState(false);
  const [databaseType, setDatabaseType] = React.useState('duckdb');
  const [databaseName, setDatabaseName] = React.useState('');
  const [duckdbDomains, setDuckdbDomains] = React.useState({});

  const [dataLoading, setDataLoading] = React.useState(true);
  const [dataLoadError, setDataLoadError] = React.useState('');
  const [dataSaveError, setDataSaveError] = React.useState('');
  const [dataSaveOk, setDataSaveOk] = React.useState('');
  const [dataSaving, setDataSaving] = React.useState(false);
  const [defaultStartDate, setDefaultStartDate] = React.useState('');
  const [asOfLatestCompletedDate, setAsOfLatestCompletedDate] = React.useState('');
  const [simulationResultsMaxStaleEnvs, setSimulationResultsMaxStaleEnvs] = React.useState('');

  const loadDatabase = useCallback(() => {
    setLoading(true);
    setLoadError('');
    fetchDatabaseSettings()
      .then((r) => {
        setDatabaseType(r.database_type);
        setDatabaseName(r.database);
        setDuckdbDomains(r.duckdb_domains || {});
      })
      .catch((e) => {
        setLoadError(e?.message || '读取数据库配置失败');
      })
      .finally(() => setLoading(false));
  }, []);

  const loadDataSettings = useCallback(() => {
    setDataLoading(true);
    setDataLoadError('');
    fetchDataSettings()
      .then((r) => {
        setDefaultStartDate(r.default_start_date || '');
        setAsOfLatestCompletedDate(r.as_of_latest_completed_trading_date || '');
        setSimulationResultsMaxStaleEnvs(
          r.simulation_results_max_stale_envs != null
            ? String(r.simulation_results_max_stale_envs)
            : '',
        );
      })
      .catch((e) => {
        setDataLoadError(e?.message || '读取数据配置失败');
      })
      .finally(() => setDataLoading(false));
  }, []);

  useEffect(() => {
    loadDatabase();
    loadDataSettings();
  }, [loadDatabase, loadDataSettings]);

  const handleSaveDatabase = () => {
    setSaveError('');
    setSaveOk('');
    setSaving(true);
    saveDatabaseSettings({ database_type: databaseType, database: databaseName.trim() })
      .then((r) => {
        setDatabaseType(r.database_type);
        setDatabaseName(r.database);
        setDuckdbDomains(r.duckdb_domains || {});
        setSaveOk('已保存到 userspace/system/config/database/ 下的配置文件。重启 BFF 或相关进程后生效。');
      })
      .catch((e) => {
        setSaveError(e?.message || '保存失败');
      })
      .finally(() => setSaving(false));
  };

  const handleSaveData = () => {
    setDataSaveError('');
    setDataSaveOk('');
    setDataSaving(true);
    saveDataSettings({
      default_start_date: defaultStartDate.trim(),
      as_of_latest_completed_trading_date: asOfLatestCompletedDate.trim(),
      simulation_results_max_stale_envs: simulationResultsMaxStaleEnvs.trim(),
    })
      .then((r) => {
        setDefaultStartDate(r.default_start_date || '');
        setAsOfLatestCompletedDate(r.as_of_latest_completed_trading_date || '');
        setSimulationResultsMaxStaleEnvs(
          r.simulation_results_max_stale_envs != null
            ? String(r.simulation_results_max_stale_envs)
            : '',
        );
        setDataSaveOk('已保存到 userspace/config/data.json。');
      })
      .catch((e) => {
        setDataSaveError(e?.message || '保存失败');
      })
      .finally(() => setDataSaving(false));
  };

  const handleTabChange = (_event, nextPath) => {
    navigate(`/settings/${nextPath}`);
  };

  return (
    <PageLayout
      className="settings-page"
      breadcrumbsItems={[{ label: '制定策略', to: '/strategy-design' }]}
      breadcrumbsCurrent="设置"
      bannerTitle="设置"
      bannerDescription="系统安装、数据库连接、会员凭证、AI 配置、Agent 配置、数据范围、缓存清理、反馈与统计。"
    >
      <Box className="settings-page-layout">
        <Paper className="settings-page-nav" elevation={0}>
          <Tabs
            orientation="vertical"
            value={section}
            onChange={handleTabChange}
            aria-label="设置分类"
          >
            {SETTINGS_TABS.map((tab) => (
              <Tab key={tab.id} label={tab.label} value={tab.path} />
            ))}
          </Tabs>
        </Paper>

        <Paper className="settings-page-panel" elevation={0}>
          <Routes>
            <Route index element={<Navigate to="membership" replace />} />
            <Route path="membership" element={<SettingsMembershipPanel />} />
            <Route path="system" element={<SettingsSystemPanel />} />
            <Route
              path="database"
              element={(
                <SettingsDatabasePanel
                  loading={loading}
                  loadError={loadError}
                  saveError={saveError}
                  saveOk={saveOk}
                  saving={saving}
                  databaseType={databaseType}
                  databaseName={databaseName}
                  duckdbDomains={duckdbDomains}
                  onDatabaseTypeChange={setDatabaseType}
                  onDatabaseNameChange={setDatabaseName}
                  onSave={handleSaveDatabase}
                  onReload={loadDatabase}
                />
              )}
            />
            <Route
              path="data"
              element={(
                <SettingsDataPanel
                  loading={dataLoading}
                  loadError={dataLoadError}
                  saveError={dataSaveError}
                  saveOk={dataSaveOk}
                  saving={dataSaving}
                  defaultStartDate={defaultStartDate}
                  asOfLatestCompletedDate={asOfLatestCompletedDate}
                  simulationResultsMaxStaleEnvs={simulationResultsMaxStaleEnvs}
                  onDefaultStartDateChange={setDefaultStartDate}
                  onAsOfLatestCompletedDateChange={setAsOfLatestCompletedDate}
                  onSimulationResultsMaxStaleEnvsChange={setSimulationResultsMaxStaleEnvs}
                  onSave={handleSaveData}
                  onReload={loadDataSettings}
                />
              )}
            />
            <Route path="ai" element={<SettingsAssistantPanel />} />
            <Route path="agent" element={<SettingsAgentPanel />} />
            <Route path="cache" element={<SettingsCachePanel />} />
            <Route path="feedback" element={<SettingsFeedbackAndTracePanel />} />
            <Route path="trace" element={<Navigate to="/settings/feedback" replace />} />
            <Route path="*" element={<Navigate to="membership" replace />} />
          </Routes>
        </Paper>
      </Box>
    </PageLayout>
  );
}

export default SettingsPage;
