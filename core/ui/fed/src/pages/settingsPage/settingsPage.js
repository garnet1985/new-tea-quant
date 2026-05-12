import React, { useCallback, useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { fetchDatabaseSettings, saveDatabaseSettings } from '../../api/apis/settingsApi';
import PageLayout from '../../components/pageLayout/pageLayout';

function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [saveError, setSaveError] = useState('');
  const [saveOk, setSaveOk] = useState('');
  const [saving, setSaving] = useState(false);

  const [databaseType, setDatabaseType] = useState('postgresql');
  const [databaseName, setDatabaseName] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    setLoadError('');
    fetchDatabaseSettings()
      .then((r) => {
        setDatabaseType(r.database_type);
        setDatabaseName(r.database);
      })
      .catch((e) => {
        setLoadError(e?.message || '读取数据库配置失败');
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleSave = () => {
    setSaveError('');
    setSaveOk('');
    setSaving(true);
    saveDatabaseSettings({ database_type: databaseType, database: databaseName.trim() })
      .then((r) => {
        setDatabaseType(r.database_type);
        setDatabaseName(r.database);
        setSaveOk('已保存到 userspace/config/database/ 下的配置文件。重启 BFF 或相关进程后生效。');
      })
      .catch((e) => {
        setSaveError(e?.message || '保存失败');
      })
      .finally(() => setSaving(false));
  };

  return (
    <PageLayout
      className="settings-page"
      breadcrumbsItems={[{ label: '策略工作台', to: '/strategy-workbench' }]}
      breadcrumbsCurrent="设置"
      bannerTitle="设置"
      bannerDescription="系统安装入口与 userspace 数据库连接（库类型、库名）的快速调整。"
    >
      <Stack spacing={2.5} sx={{ maxWidth: 720 }}>
        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>
              安装与维护
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              需要重新执行引导安装（数据路径、数据库连接、导入等）时，请进入安装向导。
            </Typography>
            <Button component={RouterLink} to="/setup" variant="contained" color="secondary">
              重新安装
            </Button>
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>
              数据库
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              对应 userspace 内
              {' '}
              <Typography component="span" variant="body2" sx={{ fontFamily: 'ui-monospace, monospace' }}>
                config/database/common.json
              </Typography>
              {' '}
              中的
              {' '}
              <code>database_type</code>
              ，以及
              {' '}
              <Typography component="span" variant="body2" sx={{ fontFamily: 'ui-monospace, monospace' }}>
                postgresql.json
              </Typography>
              {' / '}
              <Typography component="span" variant="body2" sx={{ fontFamily: 'ui-monospace, monospace' }}>
                mysql.json
              </Typography>
              {' '}
              中的
              {' '}
              <code>database</code>
              （库名）。其它连接字段请直接编辑上述文件或通过环境变量覆盖。
            </Typography>

            {loadError ? <Alert severity="error" sx={{ mb: 2 }}>{loadError}</Alert> : null}
            {saveError ? <Alert severity="error" sx={{ mb: 2 }}>{saveError}</Alert> : null}
            {saveOk ? <Alert severity="success" sx={{ mb: 2 }}>{saveOk}</Alert> : null}

            <Stack spacing={2} sx={{ maxWidth: 420 }}>
              <FormControl fullWidth size="small" disabled={loading}>
                <InputLabel id="settings-db-type-label">数据库类型</InputLabel>
                <Select
                  labelId="settings-db-type-label"
                  label="数据库类型"
                  value={databaseType}
                  onChange={(e) => setDatabaseType(e.target.value)}
                >
                  <MenuItem value="postgresql">PostgreSQL</MenuItem>
                  <MenuItem value="mysql">MySQL</MenuItem>
                </Select>
              </FormControl>
              <TextField
                label="数据库名（库名）"
                size="small"
                fullWidth
                disabled={loading}
                value={databaseName}
                onChange={(e) => setDatabaseName(e.target.value)}
                helperText="仅允许字母、数字、下划线、连字符与点号。"
              />
              <Box>
                <Button variant="contained" onClick={handleSave} disabled={loading || saving}>
                  {saving ? '保存中…' : '保存数据库设置'}
                </Button>
                <Button sx={{ ml: 1 }} variant="outlined" onClick={load} disabled={loading || saving}>
                  重新读取
                </Button>
              </Box>
            </Stack>
          </CardContent>
        </Card>
      </Stack>
    </PageLayout>
  );
}

export default SettingsPage;
