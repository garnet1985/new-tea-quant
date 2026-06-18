import React, { useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  FormControl,
  FormControlLabel,
  FormGroup,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import InlineLoadingState from '../../components/inlineLoadingState/inlineLoadingState';
import NtqIcon from '../../components/ntqIcon/ntqIcon';
import { clearSettingsCache } from '../../api/apis/settingsApi';

export function SettingsSystemPanel() {
  return (
    <Stack spacing={2}>
      <Typography variant="subtitle1" fontWeight={700}>
        安装与维护
      </Typography>
      <Typography variant="body2" color="text.secondary">
        需要重新执行引导安装（数据路径、数据库连接、导入等）时，请进入安装向导。
      </Typography>
      <Box>
        <Button component={RouterLink} to="/setup" variant="contained" color="secondary">
          重新安装
        </Button>
      </Box>
    </Stack>
  );
}

export function SettingsDatabasePanel({
  loading,
  loadError,
  saveError,
  saveOk,
  saving,
  databaseType,
  databaseName,
  duckdbDomains,
  onDatabaseTypeChange,
  onDatabaseNameChange,
  onSave,
  onReload,
}) {
  const isDuckdb = databaseType === 'duckdb';

  return (
    <Stack spacing={2}>
      <Typography variant="subtitle1" fontWeight={700}>
        数据库
      </Typography>
      <Typography variant="body2" color="text.secondary">
        对应
        {' '}
        <Typography component="span" variant="body2" sx={{ fontFamily: 'ui-monospace, monospace' }}>
          userspace/system/config/database/common.json
        </Typography>
        {' '}
        中的
        {' '}
        <code>database_type</code>
        。
        DuckDB 使用
        {' '}
        <Typography component="span" variant="body2" sx={{ fontFamily: 'ui-monospace, monospace' }}>
          duckdb.json
        </Typography>
        {' '}
        中的三域文件路径（相对
        {' '}
        <Typography component="span" variant="body2" sx={{ fontFamily: 'ui-monospace, monospace' }}>
          userspace/system/db/
        </Typography>
        ）。
        PostgreSQL / MySQL 另需编辑对应 json 中的连接字段。
      </Typography>

      {loadError ? <Alert severity="error">{loadError}</Alert> : null}
      {saveError ? <Alert severity="error">{saveError}</Alert> : null}
      {saveOk ? <Alert severity="success">{saveOk}</Alert> : null}

      {loading ? (
        <InlineLoadingState block message="正在加载数据库配置…" />
      ) : (
        <Stack spacing={2} sx={{ maxWidth: 420 }}>
          <FormControl fullWidth size="small">
            <InputLabel id="settings-db-type-label">数据库类型</InputLabel>
            <Select
              labelId="settings-db-type-label"
              label="数据库类型"
              value={databaseType}
              onChange={(e) => onDatabaseTypeChange(e.target.value)}
            >
              <MenuItem value="duckdb">DuckDB（推荐，本地文件）</MenuItem>
              <MenuItem value="postgresql">PostgreSQL</MenuItem>
              <MenuItem value="mysql">MySQL</MenuItem>
            </Select>
          </FormControl>
          {isDuckdb ? (
            <Alert severity="info">
              当前使用 DuckDB。数据文件位于 userspace/system/db/，默认域：
              {Object.keys(duckdbDomains).length > 0 ? (
                <Box component="ul" sx={{ mt: 1, mb: 0, pl: 2 }}>
                  {Object.entries(duckdbDomains).map(([domain, path]) => (
                    <li key={domain}>
                      <code>{domain}</code>
                      :
                      {' '}
                      <code>{path}</code>
                    </li>
                  ))}
                </Box>
              ) : (
                <Typography variant="body2" sx={{ mt: 1 }}>
                  data.duckdb / tag.duckdb / strategy.duckdb（使用 core 默认配置）
                </Typography>
              )}
              高级参数请直接编辑 duckdb.json。
            </Alert>
          ) : (
            <TextField
              label="数据库名（库名）"
              size="small"
              fullWidth
              value={databaseName}
              onChange={(e) => onDatabaseNameChange(e.target.value)}
              helperText="仅允许字母、数字、下划线、连字符与点号。"
            />
          )}
          <Box>
            <Button variant="contained" onClick={onSave} disabled={saving}>
              {saving ? '保存中…' : '保存数据库设置'}
            </Button>
            <Button sx={{ ml: 1 }} variant="outlined" onClick={onReload} disabled={saving}>
              重新读取
            </Button>
          </Box>
        </Stack>
      )}
    </Stack>
  );
}

export function SettingsDataPanel({
  loading,
  loadError,
  saveError,
  saveOk,
  saving,
  defaultStartDate,
  asOfLatestCompletedDate,
  useSampleStockList,
  onDefaultStartDateChange,
  onAsOfLatestCompletedDateChange,
  onUseSampleStockListChange,
  onSave,
  onReload,
}) {
  return (
    <Stack spacing={2}>
      <Typography variant="subtitle1" fontWeight={700}>
        数据范围
      </Typography>
      <Typography variant="body2" color="text.secondary">
        对应
        {' '}
        <Typography component="span" variant="body2" sx={{ fontFamily: 'ui-monospace, monospace' }}>
          userspace/config/data.json
        </Typography>
        。截至日截断会影响数据源更新状态评估与 Tag/策略的数据边界。
      </Typography>

      {loadError ? <Alert severity="error">{loadError}</Alert> : null}
      {saveError ? <Alert severity="error">{saveError}</Alert> : null}
      {saveOk ? <Alert severity="success">{saveOk}</Alert> : null}

      {loading ? (
        <InlineLoadingState block message="正在加载数据配置…" />
      ) : (
        <Stack spacing={2} sx={{ maxWidth: 420 }}>
          <TextField
            label="默认起始日期"
            size="small"
            fullWidth
            value={defaultStartDate}
            onChange={(e) => onDefaultStartDateChange(e.target.value)}
            placeholder="20080101"
            helperText="YYYYMMDD；更新拉数下界。"
          />
          <TextField
            label="截至日期（as-of）"
            size="small"
            fullWidth
            value={asOfLatestCompletedDate}
            onChange={(e) => onAsOfLatestCompletedDateChange(e.target.value)}
            placeholder="留空表示不截断"
            helperText="as_of_latest_completed_trading_date；留空则使用实时最新已完成交易日。"
          />
          <TextField
            label="样本股票池规模"
            size="small"
            fullWidth
            value={useSampleStockList}
            onChange={(e) => onUseSampleStockListChange(e.target.value)}
            placeholder="留空表示全市场"
            helperText="use_sample_stock_list；正整数 N 对应 stratified_N 样本池。"
          />
          <Box>
            <Button variant="contained" onClick={onSave} disabled={saving}>
              {saving ? '保存中…' : '保存数据设置'}
            </Button>
            <Button sx={{ ml: 1 }} variant="outlined" onClick={onReload} disabled={saving}>
              重新读取
            </Button>
          </Box>
        </Stack>
      )}
    </Stack>
  );
}

const CACHE_OPTIONS = [
  {
    key: 'clear_db_cache',
    label: '数据库缓存清理',
    hint: '清空 sys_strategy_workbench_snapshot（策略调试版本快照）。不会删除磁盘 results/。',
  },
  {
    key: 'clear_backtest_results',
    label: '回测结果临时文件清理',
    hint: '删除各策略 results/simulations/ 下的枚举、价格、资金模拟产物。',
  },
  {
    key: 'clear_scan_results',
    label: '扫描结果临时文件清理',
    hint: '删除各策略 results/scan/ 下的扫描机会缓存。',
  },
  {
    key: 'clear_userspace_ntq',
    label: '用户空间缓存清理',
    hint: '删除 userspace/.ntq/（进度、pipeline 租约、tmp 等）。不含仓库根 .ntq/。',
  },
];

const DEFAULT_CACHE_SELECTION = {
  clear_db_cache: true,
  clear_backtest_results: true,
  clear_scan_results: true,
  clear_userspace_ntq: true,
};

export function SettingsCachePanel() {
  const [selection, setSelection] = useState({ ...DEFAULT_CACHE_SELECTION });
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [clearError, setClearError] = useState('');
  const [clearOk, setClearOk] = useState('');

  const hasSelection = useMemo(
    () => Object.values(selection).some(Boolean),
    [selection],
  );

  const selectedLabels = useMemo(
    () => CACHE_OPTIONS.filter((opt) => selection[opt.key]).map((opt) => opt.label),
    [selection],
  );

  const handleToggle = (key) => (_event, checked) => {
    setSelection((prev) => ({ ...prev, [key]: checked }));
    setClearOk('');
    setClearError('');
  };

  const handleConfirmClear = () => {
    setClearing(true);
    setClearError('');
    setClearOk('');
    clearSettingsCache(selection)
      .then((res) => {
        setClearOk(res.message || '缓存已经全部清理');
        setSelection({ ...DEFAULT_CACHE_SELECTION });
      })
      .catch((e) => {
        setClearError(e?.message || '清理失败');
      })
      .finally(() => {
        setClearing(false);
        setConfirmOpen(false);
      });
  };

  return (
    <Stack spacing={2}>
      <Typography variant="subtitle1" fontWeight={700}>
        缓存管理
      </Typography>
      <Typography variant="body2" color="text.secondary">
        勾选需要清理的缓存类型，点击「一键清理」。有 Tag、扫描、回测等任务进行中时将拒绝清理。
      </Typography>

      {clearError ? <Alert severity="error">{clearError}</Alert> : null}
      {clearOk ? (
        <Alert
          severity="success"
          icon={<NtqIcon name="success" size={22} tone="success" />}
        >
          {clearOk}
        </Alert>
      ) : null}

      <FormGroup sx={{ maxWidth: 560 }}>
        {CACHE_OPTIONS.map((opt) => (
          <FormControlLabel
            key={opt.key}
            control={(
              <Checkbox
                checked={Boolean(selection[opt.key])}
                onChange={handleToggle(opt.key)}
                disabled={clearing}
              />
            )}
            label={(
              <Box>
                <Typography variant="body2" fontWeight={600}>{opt.label}</Typography>
                <Typography variant="caption" color="text.secondary" display="block">
                  {opt.hint}
                </Typography>
              </Box>
            )}
            sx={{ alignItems: 'flex-start', mb: 1 }}
          />
        ))}
      </FormGroup>

      <Box>
        <Button
          variant="contained"
          color="secondary"
          disabled={!hasSelection || clearing}
          onClick={() => setConfirmOpen(true)}
        >
          {clearing ? '清理中…' : '一键清理'}
        </Button>
      </Box>

      <Dialog open={confirmOpen} onClose={() => !clearing && setConfirmOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>确认清理缓存</DialogTitle>
        <DialogContent>
          <DialogContentText component="div">
            将清理以下项，此操作不可撤销：
            <Box component="ul" sx={{ mt: 1, mb: 0, pl: 2 }}>
              {selectedLabels.map((label) => (
                <li key={label}>{label}</li>
              ))}
            </Box>
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmOpen(false)} disabled={clearing}>
            取消
          </Button>
          <Button variant="contained" color="secondary" onClick={handleConfirmClear} disabled={clearing}>
            {clearing ? '清理中…' : '确认清理'}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
