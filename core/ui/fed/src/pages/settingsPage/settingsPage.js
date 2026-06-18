import React, { useCallback, useEffect, useMemo } from 'react';
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { Box, Paper, Tab, Tabs } from '@mui/material';
import {
  fetchDatabaseSettings,
  fetchDataSettings,
  saveDatabaseSettings,
  saveDataSettings,
} from '../../api/apis/settingsApi';
import PageLayout from '../../components/pageLayout/pageLayout';
import {
  SettingsDataPanel,
  SettingsDatabasePanel,
  SettingsSystemPanel,
} from './settingsPanels';
import './settingsPage.scss';

const SETTINGS_TABS = [
  { id: 'system', label: '安装与维护', path: 'system' },
  { id: 'database', label: '数据库', path: 'database' },
  { id: 'data', label: '数据范围', path: 'data' },
];

function useSettingsSection() {
  const location = useLocation();
  return useMemo(() => {
    const tail = location.pathname.replace(/\/+$/, '').split('/').pop() || '';
    const found = SETTINGS_TABS.find((tab) => tab.path === tail);
    return found ? found.path : 'system';
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
  const [useSampleStockList, setUseSampleStockList] = React.useState('');

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
        setUseSampleStockList(
          r.use_sample_stock_list != null ? String(r.use_sample_stock_list) : '',
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
      use_sample_stock_list: useSampleStockList.trim(),
    })
      .then((r) => {
        setDefaultStartDate(r.default_start_date || '');
        setAsOfLatestCompletedDate(r.as_of_latest_completed_trading_date || '');
        setUseSampleStockList(
          r.use_sample_stock_list != null ? String(r.use_sample_stock_list) : '',
        );
        setDataSaveOk('已保存到 userspace/config/data.json。数据源列表的截至日与更新状态将按新配置评估。');
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
      bannerDescription="系统安装、数据库连接与 data.json 数据范围。"
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
            <Route index element={<Navigate to="system" replace />} />
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
                  useSampleStockList={useSampleStockList}
                  onDefaultStartDateChange={setDefaultStartDate}
                  onAsOfLatestCompletedDateChange={setAsOfLatestCompletedDate}
                  onUseSampleStockListChange={setUseSampleStockList}
                  onSave={handleSaveData}
                  onReload={loadDataSettings}
                />
              )}
            />
            <Route path="*" element={<Navigate to="system" replace />} />
          </Routes>
        </Paper>
      </Box>
    </PageLayout>
  );
}

export default SettingsPage;
