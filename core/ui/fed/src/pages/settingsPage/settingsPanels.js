import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link as RouterLink, useLocation, useNavigate } from 'react-router-dom';
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
  Link,
  MenuItem,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
  Chip,
} from '@mui/material';
import InlineLoadingState from '../../views/inlineLoadingState';
import PageLoadingState from '../../views/pageLoadingState';
import NtqIcon from '../../views/ntqIcon';
import { formatDateTime } from '../../service/format/formatDateTime';
import {
  clearMembershipToken,
  clearSettingsCache,
  fetchCatfoodLedger,
  fetchMemberProfile,
  fetchMembershipSettings,
  fetchTraceSettings,
  saveMembershipToken,
  saveTraceSettings,
} from '../../api/settingsApi';
import { fetchFeedbackSettings, saveFeedbackSettings } from '../../api/feedbackApi';
import { fetchSiteUrls } from '../../api/siteApi';
import { listAiProviders, saveAiProviderApiKey } from '../../api/aiApi';
import {
  getImportDataProgress,
  getMlExtrasStatus,
  importDemoData,
  installMlExtras,
  resetSetupStatus,
} from '../../api/setupApi';
import { useAsyncAction } from 'service/useAsyncAction';
import { useFakeProgress } from 'service/progress/useFakeProgress';

export function SettingsSystemPanel() {
  const navigate = useNavigate();
  const [mlStatus, setMlStatus] = useState(null);
  const [mlLoadError, setMlLoadError] = useState('');
  const [mlOk, setMlOk] = useState('');
  const [installing, setInstalling] = useState(false);
  const [reinstallOpen, setReinstallOpen] = useState(false);
  const [reinstalling, setReinstalling] = useState(false);
  const [reinstallError, setReinstallError] = useState('');
  const [importOpen, setImportOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState('');
  const [importOk, setImportOk] = useState('');
  const [importProgress, setImportProgress] = useState(null);
  const fakePercent = useFakeProgress(installing, 8);

  const loadMlStatus = useCallback(() => {
    setMlLoadError('');
    return getMlExtrasStatus()
      .then((next) => {
        setMlStatus(next);
      })
      .catch((err) => {
        setMlLoadError(err?.message || '无法检查机器学习依赖状态。');
      });
  }, []);

  useEffect(() => {
    loadMlStatus();
  }, [loadMlStatus]);

  useEffect(() => {
    if (!importing) return undefined;
    let stopped = false;
    const tick = () => {
      getImportDataProgress()
        .then((next) => {
          if (!stopped) setImportProgress(next);
        })
        .catch(() => {});
    };
    tick();
    const timerId = setInterval(tick, 800);
    return () => {
      stopped = true;
      clearInterval(timerId);
    };
  }, [importing]);

  const handleInstallMl = async () => {
    setInstalling(true);
    setMlOk('');
    setMlLoadError('');
    try {
      const next = await installMlExtras();
      setMlStatus(next);
      setMlOk(next.installed ? '机器学习依赖已安装。' : '安装请求已完成，请刷新后复查。');
    } catch (err) {
      setMlLoadError(err?.message || '安装失败，请检查网络后重试。');
    } finally {
      setInstalling(false);
    }
  };

  const handleConfirmImport = async () => {
    setImporting(true);
    setImportError('');
    setImportOk('');
    setImportProgress(null);
    try {
      await importDemoData();
      setImportOpen(false);
      setImportOk('演示数据已导入。');
    } catch (err) {
      setImportError(err?.message || '演示数据导入失败，请稍后重试。');
    } finally {
      setImporting(false);
    }
  };

  const handleConfirmReinstall = async () => {
    setReinstalling(true);
    setReinstallError('');
    try {
      await resetSetupStatus();
      setReinstallOpen(false);
      navigate('/setup', { replace: true, state: { autoStart: true } });
    } catch (err) {
      setReinstallError(err?.message || '无法重置安装状态，请检查网络后重试。');
    } finally {
      setReinstalling(false);
    }
  };

  const mlInstalled = Boolean(mlStatus?.installed);
  const importBusy = importing || reinstalling;
  const importProgressText = importProgress?.totalTables
    ? `正在导入 ${importProgress.completedCount}/${importProgress.totalTables}${
      importProgress.currentTable ? `：${importProgress.currentTable}` : ''
    }`
    : '正在导入演示数据…';

  return (
    <Stack spacing={2}>
      <Typography variant="subtitle1" fontWeight={700}>
        安装与维护
      </Typography>
      <Typography variant="body2" color="text.secondary">
        重新安装会再次走引导：数据路径、数据库连接、演示数据和可选的机器学习依赖。确认后从第一步开始，不会停留在「安装完成」页。
      </Typography>
      {reinstallError ? <Alert severity="error">{reinstallError}</Alert> : null}
      <Box>
        <Button
          variant="contained"
          color="secondary"
          disabled={importBusy}
          onClick={() => {
            setReinstallError('');
            setReinstallOpen(true);
          }}
        >
          重新安装
        </Button>
      </Box>
      <Dialog
        open={reinstallOpen}
        onClose={() => !reinstalling && setReinstallOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>确认重新安装？</DialogTitle>
        <DialogContent>
          <DialogContentText component="div">
            向导会从头执行。请先了解这些风险：
            <Box component="ul" sx={{ mt: 1, mb: 0, pl: 2 }}>
              <li>可能覆盖 userspace 路径选择，以及数据库连接配置。</li>
              <li>若选择导入演示数据，现有表数据可能被覆盖。</li>
              <li>进行中的回测 / 扫描结果不会自动备份。</li>
              <li>已安装的 Python 依赖不会被卸载；机器学习组件仍可稍后在本页补装。</li>
            </Box>
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReinstallOpen(false)} disabled={reinstalling}>
            取消
          </Button>
          <Button
            variant="contained"
            color="warning"
            onClick={handleConfirmReinstall}
            disabled={reinstalling}
          >
            {reinstalling ? '正在进入安装…' : '确认，从第一步开始'}
          </Button>
        </DialogActions>
      </Dialog>

      <Typography variant="subtitle1" fontWeight={700} sx={{ pt: 1 }}>
        演示数据
      </Typography>
      <Typography variant="body2" color="text.secondary">
        安装时如果跳过了演示数据，可以在这里导入。导入会清空数据包中的表再写入，可能覆盖已有数据。
      </Typography>
      {importError ? <Alert severity="error">{importError}</Alert> : null}
      {importOk ? <Alert severity="success">{importOk}</Alert> : null}
      {importing ? (
        <Typography variant="body2" color="text.secondary">
          {importProgressText}
        </Typography>
      ) : null}
      <Box>
        <Button
          variant="outlined"
          disabled={importBusy}
          onClick={() => {
            setImportError('');
            setImportOk('');
            setImportOpen(true);
          }}
        >
          导入演示数据
        </Button>
      </Box>
      <Dialog
        open={importOpen}
        onClose={() => !importing && setImportOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>导入演示数据？</DialogTitle>
        <DialogContent>
          <DialogContentText>
            演示数据包里的表会被清空后重写，可能覆盖已有行情。请先退出其他正在使用这个数据库的程序，再继续。
          </DialogContentText>
          {importError ? (
            <Alert severity="error" sx={{ mt: 2 }}>{importError}</Alert>
          ) : null}
          {importing ? (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              {importProgressText}
            </Typography>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setImportOpen(false)} disabled={importing}>
            取消
          </Button>
          <Button
            variant="contained"
            onClick={handleConfirmImport}
            disabled={importing}
          >
            {importing ? '正在导入…' : '开始导入'}
          </Button>
        </DialogActions>
      </Dialog>

      <Typography variant="subtitle1" fontWeight={700} sx={{ pt: 1 }}>
        机器学习组件
      </Typography>
      <Typography variant="body2" color="text.secondary">
        分析库的统计 / ML 原语会用到这些依赖（XGBoost / SHAP）。跳过安装向导后可在这里补装，可能需要几分钟。
      </Typography>
      {mlLoadError ? <Alert severity="error">{mlLoadError}</Alert> : null}
      {mlOk ? <Alert severity="success">{mlOk}</Alert> : null}
      {mlStatus == null && !mlLoadError ? (
        <InlineLoadingState message="正在检查机器学习依赖…" />
      ) : (
        <Typography variant="body2" color="text.secondary">
          {mlInstalled
            ? `已安装${mlStatus?.shap ? '（含 SHAP）' : '（XGBoost）'}。`
            : '尚未安装。分析库的机器学习阶段在未安装时会跳过。'}
        </Typography>
      )}
      {installing ? (
        <Box>
          <Typography variant="caption" color="text.secondary">
            正在安装… {fakePercent}%
          </Typography>
          <Box sx={{ mt: 0.5, height: 8, borderRadius: 1, bgcolor: 'grey.200', overflow: 'hidden' }}>
            <Box
              sx={{
                width: `${fakePercent}%`,
                bgcolor: 'primary.main',
                height: '100%',
                transition: 'width 0.4s ease',
              }}
            />
          </Box>
        </Box>
      ) : null}
      <Box>
        <Button
          variant="outlined"
          disabled={mlInstalled || installing}
          onClick={handleInstallMl}
        >
          {mlInstalled ? '已安装' : '安装机器学习依赖'}
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
        <PageLoadingState message="正在加载数据库配置…" minHeight="36vh" />
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
  simulationResultsMaxStaleEnvs,
  onDefaultStartDateChange,
  onAsOfLatestCompletedDateChange,
  onUseSampleStockListChange,
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
        <PageLoadingState message="正在加载数据配置…" minHeight="36vh" />
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
          <Box id="settings-retention">
            <TextField
              label="过时回测环境保留组数"
              size="small"
              fullWidth
              value={simulationResultsMaxStaleEnvs}
              onChange={(e) => onSimulationResultsMaxStaleEnvsChange(e.target.value)}
              placeholder="5"
              helperText="改代码或核心后旧环境不能再跑，最多留这么多组档案。超出则整组删除。当前环境不限份数。"
            />
          </Box>
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
    key: 'clear_backtest_results',
    label: '回测结果临时文件清理',
    hint: '删除各策略 results/simulations/ 下的枚举、价格、投资模拟产物。',
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

function formatTraceDecidedAt(raw) {
  return formatDateTime(raw, { style: 'absolute' });
}

export function SettingsTracePanel() {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [saveOk, setSaveOk] = useState('');
  const [enabled, setEnabled] = useState(false);
  const [decided, setDecided] = useState(false);
  const [decidedAt, setDecidedAt] = useState('');

  const saveAction = useAsyncAction(
    useCallback((nextEnabled) => saveTraceSettings({ enabled: Boolean(nextEnabled) }), []),
  );

  const applyState = useCallback((r) => {
    setEnabled(Boolean(r.enabled));
    setDecided(Boolean(r.decided));
    setDecidedAt(formatTraceDecidedAt(r.decided_at));
  }, []);

  const load = useCallback(() => {
    setLoadError('');
    setLoading(true);
    fetchTraceSettings()
      .then(applyState)
      .catch((e) => {
        setLoadError(e?.message || '读取使用统计设置失败');
      })
      .finally(() => setLoading(false));
  }, [applyState]);

  useEffect(() => {
    load();
  }, [load]);

  const handleToggle = async (_event, next) => {
    setSaveOk('');
    saveAction.clearError();
    try {
      const r = await saveAction.run(Boolean(next));
      applyState(r);
      setSaveOk(next ? '已开启匿名使用统计。' : '已关闭匿名使用统计。本地排队事件已清空。');
    } catch {
      /* saveAction.error */
    }
  };

  return (
    <Stack spacing={2}>
      <Typography variant="subtitle1" fontWeight={700}>
        使用统计
      </Typography>
      <Typography variant="body2" color="text.secondary">
        可选的匿名使用数据，用于改进 New Tea Quant。不包含策略代码、回测结果、账户或个人身份信息。
        详见
        {' '}
        <Link component={RouterLink} to="/what-we-will-track" underline="hover">
          我们收集哪些信息
        </Link>
        。
      </Typography>

      {loadError ? <Alert severity="error">{loadError}</Alert> : null}
      {saveAction.error ? <Alert severity="error">{saveAction.error}</Alert> : null}
      {saveOk ? <Alert severity="success">{saveOk}</Alert> : null}

      {loading ? (
        <PageLoadingState message="正在加载使用统计设置…" minHeight="36vh" />
      ) : (
        <Stack spacing={1.5} sx={{ maxWidth: 520 }}>
          {!decided ? (
            <Alert severity="info">
              尚未选择偏好。打开开关即表示同意；关闭表示不同意。之后可随时在此更改。
            </Alert>
          ) : null}
          <FormControlLabel
            sx={{
              ml: 0,
              gap: 1.5,
              alignItems: 'center',
              '& .MuiFormControlLabel-label': { marginLeft: 0 },
            }}
            control={(
              <Switch
                checked={enabled}
                onChange={handleToggle}
                disabled={saveAction.busy}
                inputProps={{ 'aria-label': '开启匿名使用统计' }}
              />
            )}
            label={enabled ? '已开启匿名使用统计' : '未开启匿名使用统计'}
          />
          {decided && decidedAt ? (
            <Typography variant="caption" color="text.secondary">
              最近决定时间：
              {decidedAt}
            </Typography>
          ) : null}
          <Box>
            <Button variant="outlined" onClick={load} disabled={saveAction.busy || loading}>
              重新读取
            </Button>
          </Box>
        </Stack>
      )}
    </Stack>
  );
}

export function SettingsFeedbackPanel() {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [saveOk, setSaveOk] = useState('');
  const [promptsDisabled, setPromptsDisabled] = useState(false);
  const [contactUrl, setContactUrl] = useState('');

  const saveAction = useAsyncAction(
    useCallback((nextDisabled) => saveFeedbackSettings({ prompts_disabled: Boolean(nextDisabled) }), []),
  );

  const applyState = useCallback((r) => {
    setPromptsDisabled(Boolean(r.prompts_disabled));
    if (r.contact_url) setContactUrl(String(r.contact_url));
  }, []);

  const load = useCallback(() => {
    setLoadError('');
    setLoading(true);
    fetchFeedbackSettings()
      .then(applyState)
      .catch((e) => {
        setLoadError(e?.message || '读取反馈设置失败');
      })
      .finally(() => setLoading(false));
  }, [applyState]);

  useEffect(() => {
    load();
  }, [load]);

  const handleToggle = async (_event, nextEnabled) => {
    // Switch ON = prompts enabled = prompts_disabled false
    const nextDisabled = !nextEnabled;
    setSaveOk('');
    saveAction.clearError();
    try {
      const r = await saveAction.run(nextDisabled);
      applyState(r);
      setSaveOk(nextDisabled ? '已关闭应用内反馈询问。' : '已开启应用内反馈询问。');
    } catch {
      /* saveAction.error */
    }
  };

  return (
    <Stack spacing={2}>
      <Typography variant="subtitle1" fontWeight={700}>
        反馈
      </Typography>
      <Typography variant="body2" color="text.secondary">
        任务成功后会弹出简短反馈，每个半天（0 点到 12 点、12 点到 24 点）最多一次。关闭询问只在本页。一旦你主动发送，不会再要求任何本地授权。
        更长的问题请走官网联系页。
      </Typography>

      {loadError ? <Alert severity="error">{loadError}</Alert> : null}
      {saveAction.error ? <Alert severity="error">{saveAction.error}</Alert> : null}
      {saveOk ? <Alert severity="success">{saveOk}</Alert> : null}

      {loading ? (
        <PageLoadingState message="正在加载反馈设置…" minHeight="36vh" />
      ) : (
        <Stack spacing={1.5} sx={{ maxWidth: 520 }}>
          <FormControlLabel
            sx={{
              ml: 0,
              gap: 1.5,
              alignItems: 'center',
              '& .MuiFormControlLabel-label': { marginLeft: 0 },
            }}
            control={(
              <Switch
                checked={!promptsDisabled}
                onChange={handleToggle}
                disabled={saveAction.busy}
                inputProps={{ 'aria-label': '开启应用内反馈询问' }}
              />
            )}
            label={promptsDisabled ? '已关闭应用内反馈询问' : '允许应用内反馈询问'}
          />
          {contactUrl ? (
            <Box>
              <Button
                component="a"
                href={contactUrl}
                target="_blank"
                rel="noopener noreferrer"
                variant="outlined"
              >
                打开官网联系页
              </Button>
            </Box>
          ) : null}
          <Box>
            <Button variant="text" onClick={load} disabled={saveAction.busy || loading}>
              重新读取
            </Button>
          </Box>
        </Stack>
      )}
    </Stack>
  );
}

export function SettingsMembershipPanel() {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [saveOk, setSaveOk] = useState('');
  const [configured, setConfigured] = useState(false);
  const [invalid, setInvalid] = useState(false);
  const [filePath, setFilePath] = useState('userspace/system/membership/membership_token.txt');
  const [token, setToken] = useState('');
  const [catfood, setCatfood] = useState(null);
  const [ledgerItems, setLedgerItems] = useState([]);
  const [ledgerLoading, setLedgerLoading] = useState(false);

  const saveAction = useAsyncAction(useCallback((value) => saveMembershipToken(value), []));
  const clearAction = useAsyncAction(useCallback(() => clearMembershipToken(), []));

  const applyState = useCallback((r) => {
    setConfigured(Boolean(r.configured));
    setInvalid(Boolean(r.invalid));
    if (r.path) setFilePath(r.path);
  }, []);

  const loadLedger = useCallback((ready) => {
    if (!ready) {
      setCatfood(null);
      setLedgerItems([]);
      return;
    }
    setLedgerLoading(true);
    Promise.all([
      fetchMemberProfile().catch(() => null),
      fetchCatfoodLedger(30).catch(() => null),
    ])
      .then(([profile, ledger]) => {
        if (profile?.signed_in && profile.catfood != null) {
          setCatfood(Number(profile.catfood));
        } else if (ledger?.available && ledger.catfood != null) {
          setCatfood(Number(ledger.catfood));
        } else {
          setCatfood(null);
        }
        setLedgerItems(Array.isArray(ledger?.items) ? ledger.items : []);
      })
      .finally(() => setLedgerLoading(false));
  }, []);

  const load = useCallback(() => {
    setLoadError('');
    setLoading(true);
    fetchMembershipSettings()
      .then((r) => {
        applyState(r);
        loadLedger(Boolean(r.configured));
      })
      .catch((e) => {
        setLoadError(e?.message || '读取会员凭证失败');
      })
      .finally(() => setLoading(false));
  }, [applyState, loadLedger]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSave = async () => {
    setSaveOk('');
    saveAction.clearError();
    try {
      const r = await saveAction.run(token);
      applyState(r);
      setToken('');
      setSaveOk('通用凭证已装载。');
      loadLedger(Boolean(r.configured));
    } catch {
      /* saveAction.error */
    }
  };

  const handleClear = async () => {
    setSaveOk('');
    clearAction.clearError();
    try {
      const r = await clearAction.run();
      applyState(r);
      setToken('');
      setSaveOk('已移除通用凭证。');
      loadLedger(false);
    } catch {
      /* clearAction.error */
    }
  };

  if (loading) {
    return <InlineLoadingState />;
  }

  return (
    <Stack spacing={2}>
      <Typography variant="subtitle1" fontWeight={700}>
        会员
      </Typography>
      <Typography variant="body2" color="text.secondary">
        把官网会员中心的通用凭证贴到这里，或直接把文件放到
        {' '}
        {filePath}
        。文件里是有效凭证后，新茶会通过官网回答。没有这份凭证时，仍使用 AI 助理里自己的密钥。
      </Typography>
      {loadError ? <Alert severity="error">{loadError}</Alert> : null}
      {saveOk ? <Alert severity="success">{saveOk}</Alert> : null}
      {saveAction.error ? <Alert severity="error">{saveAction.error}</Alert> : null}
      {clearAction.error ? <Alert severity="error">{clearAction.error}</Alert> : null}
      <Stack direction="row" spacing={1} alignItems="center">
        <Chip
          size="small"
          color={configured ? 'success' : 'default'}
          label={configured ? '已装载' : '尚未装载'}
        />
        {invalid ? (
          <Typography variant="body2" color="error">
            文件在，但内容不是通用凭证。
          </Typography>
        ) : null}
        {configured && catfood != null && Number.isFinite(catfood) ? (
          <Typography variant="body2" color="text.secondary">
            猫粮
            {' '}
            {Number(catfood).toFixed(2)}
          </Typography>
        ) : null}
      </Stack>
      <TextField
        className="membership-token-field"
        label="通用凭证"
        placeholder="粘贴通用凭证"
        type="password"
        size="small"
        value={token}
        autoComplete="off"
        onChange={(e) => setToken(e.target.value)}
        helperText="只写入文件，页面不会再显示已保存的凭证。"
        fullWidth
        InputLabelProps={{ shrink: true }}
        sx={{
          '& .MuiInputLabel-root': {
            position: 'static',
            transform: 'none !important',
            marginBottom: '6px',
            maxWidth: '100%',
            fontSize: '0.8rem',
            lineHeight: 1.4,
            letterSpacing: 'normal',
            color: 'text.secondary',
            pointerEvents: 'none',
          },
          '& .MuiOutlinedInput-root': {
            background: 'transparent',
            minHeight: 0,
            padding: 0,
            backdropFilter: 'none',
          },
          '& .MuiOutlinedInput-notchedOutline': {
            display: 'none',
          },
          '& .MuiOutlinedInput-input': {
            boxSizing: 'border-box',
            height: 40,
            margin: 0,
            padding: '0 12px !important',
            lineHeight: '40px',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            borderRadius: '5px',
            background: 'var(--ntq-white-03)',
          },
          '& .MuiOutlinedInput-root:hover .MuiOutlinedInput-input': {
            borderColor: 'rgba(255, 255, 255, 0.18)',
          },
          '& .MuiOutlinedInput-root.Mui-focused .MuiOutlinedInput-input': {
            borderColor: 'rgba(255, 255, 255, 0.28)',
          },
        }}
      />
      <Stack direction="row" spacing={1}>
        <Button
          variant="contained"
          disabled={saveAction.busy || !token.trim()}
          onClick={handleSave}
        >
          装载
        </Button>
        <Button
          variant="outlined"
          color="inherit"
          disabled={clearAction.busy || (!configured && !invalid)}
          onClick={handleClear}
        >
          移除
        </Button>
      </Stack>
      {configured ? (
        <Box>
          <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
            <Typography variant="subtitle2" fontWeight={700}>
              猫粮记录
            </Typography>
            <Button
              size="small"
              variant="text"
              disabled={ledgerLoading}
              onClick={() => loadLedger(true)}
            >
              刷新
            </Button>
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            最近对话消耗、月赠与调整。
          </Typography>
          {ledgerLoading ? <InlineLoadingState /> : null}
          {!ledgerLoading && ledgerItems.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              还没有记录。
            </Typography>
          ) : null}
          {!ledgerLoading && ledgerItems.length > 0 ? (
            <Stack spacing={0.75}>
              {ledgerItems.map((row) => {
                const delta = Number(row.catfoodDelta);
                const deltaText = Number.isFinite(delta)
                  ? `${delta > 0 ? '+' : ''}${delta.toFixed(2)}`
                  : '—';
                const after = Number(row.catfoodBalanceAfter);
                return (
                  <Box
                    key={row.id || `${row.created}-${row.reason}-${row.mode}`}
                    sx={{
                      display: 'grid',
                      gridTemplateColumns: 'minmax(7rem, auto) 1fr auto auto',
                      gap: 1,
                      alignItems: 'baseline',
                      py: 0.75,
                      borderBottom: '1px solid',
                      borderColor: 'divider',
                      fontSize: '0.8rem',
                    }}
                  >
                    <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: 'nowrap' }}>
                      {formatDateTime(row.created, { style: 'absolute' })}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" noWrap>
                      {row.reasonLabel || row.reason}
                    </Typography>
                    <Typography
                      variant="body2"
                      fontWeight={700}
                      color={delta < 0 ? 'primary.main' : delta > 0 ? 'success.main' : 'text.secondary'}
                      sx={{ fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}
                    >
                      {deltaText}
                    </Typography>
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}
                    >
                      {Number.isFinite(after) ? `→ ${after.toFixed(2)}` : ''}
                    </Typography>
                  </Box>
                );
              })}
            </Stack>
          ) : null}
        </Box>
      ) : null}
    </Stack>
  );
}

function NtqProxyCard({ configured }) {
  const [registerUrl, setRegisterUrl] = useState('');

  useEffect(() => {
    let alive = true;
    fetchSiteUrls()
      .then((urls) => {
        if (alive) setRegisterUrl(urls.registerUrl);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  return (
    <Box
      sx={{
        p: 2,
        border: '1px solid',
        borderColor: configured ? 'success.main' : 'divider',
        bgcolor: configured ? 'action.hover' : 'transparent',
        borderRadius: 1,
      }}
    >
      <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1}>
        <Typography variant="body2" fontWeight={700}>
          NTQ AI
        </Typography>
        <Chip
          size="small"
          color={configured ? 'success' : 'default'}
          variant={configured ? 'filled' : 'outlined'}
          label={configured ? '已接入' : '尚未装载凭证'}
        />
      </Stack>
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
        官网代理 · 每天 30 次回答
      </Typography>
      {configured ? (
        <Typography variant="body2" sx={{ mt: 1.5 }}>
          通用凭证已装载。对话经官网转发，不用再填模型密钥。
          {' '}
          <Link component={RouterLink} to="/settings/membership">
            查看会员凭证
          </Link>
        </Typography>
      ) : (
        <Typography variant="body2" sx={{ mt: 1.5 }}>
          到官网注册会员，在会员中心复制通用凭证，再放到设置 → 会员。
          {' '}
          {registerUrl ? (
            <Link href={registerUrl} target="_blank" rel="noreferrer">
              去官网注册
            </Link>
          ) : null}
          {' '}
          <Link component={RouterLink} to="/settings/membership">
            去装载凭证
          </Link>
        </Typography>
      )}
    </Box>
  );
}

export function SettingsAssistantPanel() {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [saveError, setSaveError] = useState('');
  const [saveOk, setSaveOk] = useState('');
  const [providers, setProviders] = useState([]);
  const [membershipReady, setMembershipReady] = useState(false);
  const [drafts, setDrafts] = useState({});
  const [savingId, setSavingId] = useState('');

  const load = useCallback(() => {
    setLoadError('');
    setLoading(true);
    Promise.all([
      listAiProviders(),
      fetchMembershipSettings().catch(() => ({ configured: false })),
    ])
      .then(([items, membership]) => {
        setProviders(Array.isArray(items) ? items : []);
        setMembershipReady(Boolean(membership?.configured));
      })
      .catch((e) => {
        setLoadError(e?.message || '读取 AI 供应商失败');
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleDraftChange = (providerId) => (event) => {
    const value = event.target.value;
    setDrafts((prev) => ({ ...prev, [providerId]: value }));
    setSaveOk('');
    setSaveError('');
  };

  const handleSave = (providerId) => {
    const apiKey = String(drafts[providerId] || '').trim();
    if (!apiKey || savingId) return;
    setSavingId(providerId);
    setSaveError('');
    setSaveOk('');
    saveAiProviderApiKey(providerId, apiKey)
      .then((updated) => {
        setProviders((prev) => prev.map((item) => (
          item.providerId === updated.providerId ? { ...item, ...updated } : item
        )));
        setDrafts((prev) => ({ ...prev, [providerId]: '' }));
        setSaveOk(`已保存 ${updated.providerId} 的 API Key。`);
      })
      .catch((e) => {
        setSaveError(e?.message || '保存失败');
      })
      .finally(() => setSavingId(''));
  };

  const sortedProviders = useMemo(() => {
    const items = Array.isArray(providers) ? [...providers] : [];
    items.sort((a, b) => {
      const aKey = Boolean(a?.hasApiKey);
      const bKey = Boolean(b?.hasApiKey);
      if (aKey !== bKey) return aKey ? -1 : 1;
      return String(a?.providerId || '').localeCompare(String(b?.providerId || ''));
    });
    return items;
  }, [providers]);

  return (
    <Stack spacing={2}>
      <Typography variant="subtitle1" fontWeight={700}>
        AI 助理
      </Typography>
      <Typography variant="body2" color="text.secondary">
        把密钥写入本机已发现的供应商。页面不会回读明文，只会显示是否已配置。
      </Typography>

      {loadError ? <Alert severity="error">{loadError}</Alert> : null}
      {saveError ? <Alert severity="error">{saveError}</Alert> : null}
      {saveOk ? (
        <Alert
          severity="success"
          icon={<NtqIcon name="success" size={22} tone="success" />}
        >
          {saveOk}
        </Alert>
      ) : null}

      {loading ? (
        <PageLoadingState message="正在加载 AI 供应商…" minHeight="36vh" />
      ) : (
        <Stack spacing={2} sx={{ maxWidth: 560 }}>
          <NtqProxyCard configured={membershipReady} />
          {sortedProviders.length === 0 ? (
            <Alert severity="info">
              还没有发现 AI 供应商。需要先在 userspace 里放好供应商目录和 config.py。
            </Alert>
          ) : sortedProviders.map((item) => {
            const draft = drafts[item.providerId] || '';
            const busy = savingId === item.providerId;
            const configured = Boolean(item.hasApiKey);
            return (
              <Box
                key={item.providerId}
                sx={{
                  p: 2,
                  border: '1px solid',
                  borderColor: configured ? 'success.main' : 'divider',
                  bgcolor: configured ? 'action.hover' : 'transparent',
                  borderRadius: 1,
                }}
              >
                <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1}>
                  <Typography variant="body2" fontWeight={700}>
                    {item.providerId}
                  </Typography>
                  <Chip
                    size="small"
                    color={configured ? 'success' : 'default'}
                    variant={configured ? 'filled' : 'outlined'}
                    label={configured ? '已配置 API Key' : '尚未配置 API Key'}
                  />
                </Stack>
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                  {item.model}
                  {item.baseUrl ? ` · ${item.baseUrl}` : ''}
                  {item.enabled ? '' : ' · 已禁用'}
                </Typography>
                <TextField
                  type="password"
                  label="API Key"
                  value={draft}
                  onChange={handleDraftChange(item.providerId)}
                  autoComplete="off"
                  fullWidth
                  size="small"
                  sx={{ mt: 1.5 }}
                  disabled={Boolean(savingId)}
                  placeholder={configured ? '输入新密钥可覆盖' : '粘贴 API Key'}
                />
                <Box sx={{ mt: 1.5 }}>
                  <Button
                    variant="contained"
                    color="secondary"
                    disabled={!draft.trim() || Boolean(savingId)}
                    onClick={() => handleSave(item.providerId)}
                  >
                    {busy ? '保存中…' : '保存'}
                  </Button>
                </Box>
              </Box>
            );
          })}
          <Box>
            <Button variant="outlined" onClick={load} disabled={Boolean(savingId) || loading}>
              重新读取
            </Button>
          </Box>
        </Stack>
      )}
    </Stack>
  );
}
