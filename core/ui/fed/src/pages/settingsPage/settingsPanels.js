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
import BecomeMemberLink from '../../views/becomeMemberLink';
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
import { listAiProviders, saveAiProviderApiKey } from '../../api/aiApi';
import {
  clearAgentSession,
  fetchAgentSettings,
  saveAgentSettings,
} from '../../api/agentApi';
import {
  getImportDataProgress,
  getMlExtrasStatus,
  importDemoData,
  installMlExtras,
  resetSetupStatus,
} from '../../api/setupApi';
import { useAsyncAction } from 'service/useAsyncAction';
import { useFakeProgress } from 'service/progress/useFakeProgress';
import { persistDockSelectedId } from '../../containers/assistantChatDock/dockChatStore';

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
  simulationResultsMaxStaleEnvs,
  onDefaultStartDateChange,
  onAsOfLatestCompletedDateChange,
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
        。这里只约束「已入库数据怎么用」：起始日与截至日等，不会凭空补行情。
      </Typography>

      <Alert severity="info" sx={{ width: '100%', alignSelf: 'stretch' }}>
        <Typography variant="body2" component="div">
          库里没有的区间或标的，把截至日拉长或起始日提前都不会生效——系统仍只能用已下载/导入的数据。
        </Typography>
        <Typography variant="body2" component="div" sx={{ mt: 1 }}>
          自带演示数据大约是
          {' '}
          <strong>300 只股票、约 3 年</strong>
          （约 2023–2025 年底）。需要更长历史或全市场时，请先补数据，而不是只改本页：
        </Typography>
        <Box component="ul" sx={{ m: 0, mt: 1, pl: 2.5 }}>
          <li>
            <Typography variant="body2" component="span">
              注册会员后，可在官网下载并导入约 3 年全市场数据；也可在
              {' '}
              <Link component={RouterLink} to="/advanced/data-sources" underline="hover">
                高级功能 → 数据源
              </Link>
              {' '}
              拉取（档位与点数以该页说明为准）。还没有账号？
              {' '}
              <BecomeMemberLink />
              。
            </Typography>
          </li>
          <li>
            <Typography variant="body2" component="span">
              尚未导入演示包时，可到
              {' '}
              <Link component={RouterLink} to="/settings/system" underline="hover">
                设置 → 安装与维护
              </Link>
              ；会员凭证在
              {' '}
              <Link component={RouterLink} to="/settings/membership" underline="hover">
                设置 → 会员
              </Link>
              。
            </Typography>
          </li>
        </Box>
      </Alert>

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
            helperText="YYYYMMDD；更新/拉数的下界。库中更早没有数据时，实际仍从库内最早日开始。"
          />
          <TextField
            label="截至日期（as-of）"
            size="small"
            fullWidth
            value={asOfLatestCompletedDate}
            onChange={(e) => onAsOfLatestCompletedDateChange(e.target.value)}
            placeholder="留空表示不截断"
            helperText="截断 Tag/策略与数据源状态评估的上界；留空则用实时最新已完成交易日。不能超过库内已有行情。"
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

/** 反馈询问 + 匿名使用统计（合并页）。 */
export function SettingsFeedbackAndTracePanel() {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [feedbackSaveOk, setFeedbackSaveOk] = useState('');
  const [traceSaveOk, setTraceSaveOk] = useState('');
  const [promptsDisabled, setPromptsDisabled] = useState(false);
  const [contactUrl, setContactUrl] = useState('');
  const [traceEnabled, setTraceEnabled] = useState(false);
  const [traceDecided, setTraceDecided] = useState(false);
  const [traceDecidedAt, setTraceDecidedAt] = useState('');

  const feedbackSave = useAsyncAction(
    useCallback((nextDisabled) => saveFeedbackSettings({ prompts_disabled: Boolean(nextDisabled) }), []),
  );
  const traceSave = useAsyncAction(
    useCallback((nextEnabled) => saveTraceSettings({ enabled: Boolean(nextEnabled) }), []),
  );

  const load = useCallback(() => {
    setLoadError('');
    setLoading(true);
    Promise.all([fetchFeedbackSettings(), fetchTraceSettings()])
      .then(([feedback, trace]) => {
        setPromptsDisabled(Boolean(feedback.prompts_disabled));
        if (feedback.contact_url) setContactUrl(String(feedback.contact_url));
        setTraceEnabled(Boolean(trace.enabled));
        setTraceDecided(Boolean(trace.decided));
        setTraceDecidedAt(formatTraceDecidedAt(trace.decided_at));
      })
      .catch((e) => {
        setLoadError(e?.message || '读取反馈与使用统计设置失败');
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleFeedbackToggle = async (_event, nextEnabled) => {
    const nextDisabled = !nextEnabled;
    setFeedbackSaveOk('');
    feedbackSave.clearError();
    try {
      const r = await feedbackSave.run(nextDisabled);
      setPromptsDisabled(Boolean(r.prompts_disabled));
      if (r.contact_url) setContactUrl(String(r.contact_url));
      setFeedbackSaveOk(nextDisabled ? '已关闭应用内反馈询问。' : '已开启应用内反馈询问。');
    } catch {
      /* feedbackSave.error */
    }
  };

  const handleTraceToggle = async (_event, next) => {
    setTraceSaveOk('');
    traceSave.clearError();
    try {
      const r = await traceSave.run(Boolean(next));
      setTraceEnabled(Boolean(r.enabled));
      setTraceDecided(Boolean(r.decided));
      setTraceDecidedAt(formatTraceDecidedAt(r.decided_at));
      setTraceSaveOk(next ? '已开启匿名使用统计。' : '已关闭匿名使用统计。本地排队事件已清空。');
    } catch {
      /* traceSave.error */
    }
  };

  const busy = feedbackSave.busy || traceSave.busy;

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="subtitle1" fontWeight={700}>
          反馈与统计
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          管理应用内反馈询问，以及可选的匿名使用统计。
        </Typography>
      </Box>

      {loadError ? <Alert severity="error">{loadError}</Alert> : null}
      {feedbackSave.error ? <Alert severity="error">{feedbackSave.error}</Alert> : null}
      {traceSave.error ? <Alert severity="error">{traceSave.error}</Alert> : null}
      {feedbackSaveOk ? <Alert severity="success">{feedbackSaveOk}</Alert> : null}
      {traceSaveOk ? <Alert severity="success">{traceSaveOk}</Alert> : null}

      {loading ? (
        <PageLoadingState message="正在加载反馈与统计设置…" minHeight="36vh" />
      ) : (
        <Stack spacing={3} sx={{ maxWidth: 560 }}>
          <Stack spacing={1.5}>
            <Typography variant="subtitle2" fontWeight={700}>
              反馈
            </Typography>
            <Typography variant="body2" color="text.secondary">
              任务成功后会弹出简短反馈，每个半天（0 点到 12 点、12 点到 24 点）最多一次。关闭询问只在本页。一旦你主动发送，不会再要求任何本地授权。
              更长的问题请走官网联系页。
            </Typography>
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
                  onChange={handleFeedbackToggle}
                  disabled={busy}
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
                  size="small"
                >
                  打开官网联系页
                </Button>
              </Box>
            ) : null}
          </Stack>

          <Stack spacing={1.5}>
            <Typography variant="subtitle2" fontWeight={700}>
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
            {!traceDecided ? (
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
                  checked={traceEnabled}
                  onChange={handleTraceToggle}
                  disabled={busy}
                  inputProps={{ 'aria-label': '开启匿名使用统计' }}
                />
              )}
              label={traceEnabled ? '已开启匿名使用统计' : '未开启匿名使用统计'}
            />
            {traceDecided && traceDecidedAt ? (
              <Typography variant="caption" color="text.secondary">
                最近决定时间：
                {traceDecidedAt}
              </Typography>
            ) : null}
          </Stack>

          <Box>
            <Button variant="outlined" onClick={load} disabled={busy || loading}>
              重新读取
            </Button>
          </Box>
        </Stack>
      )}
    </Stack>
  );
}

const LEDGER_INITIAL = 20;
const LEDGER_MORE = 50;

export function SettingsMembershipPanel() {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [saveOk, setSaveOk] = useState('');
  const [configured, setConfigured] = useState(false);
  const [invalid, setInvalid] = useState(false);
  const [filePath, setFilePath] = useState('userspace/system/membership/membership_token.txt');
  const [token, setToken] = useState('');
  const [catfood, setCatfood] = useState(null);
  const [catfoodFree, setCatfoodFree] = useState(null);
  const [catfoodPaid, setCatfoodPaid] = useState(null);
  const [catfoodFreeExpiresAt, setCatfoodFreeExpiresAt] = useState(null);
  const [ledgerItems, setLedgerItems] = useState([]);
  const [ledgerLimit, setLedgerLimit] = useState(LEDGER_INITIAL);
  const [ledgerHasMore, setLedgerHasMore] = useState(false);
  const [ledgerLoading, setLedgerLoading] = useState(false);
  const [ledgerLoadingMore, setLedgerLoadingMore] = useState(false);

  const saveAction = useAsyncAction(useCallback((value) => saveMembershipToken(value), []));
  const clearAction = useAsyncAction(useCallback(() => clearMembershipToken(), []));

  const applyState = useCallback((r) => {
    setConfigured(Boolean(r.configured));
    setInvalid(Boolean(r.invalid));
    if (r.path) setFilePath(r.path);
  }, []);

  const loadLedger = useCallback((ready, { limit = LEDGER_INITIAL, append = false } = {}) => {
    if (!ready) {
      setCatfood(null);
      setCatfoodFree(null);
      setCatfoodPaid(null);
      setCatfoodFreeExpiresAt(null);
      setLedgerItems([]);
      setLedgerLimit(LEDGER_INITIAL);
      setLedgerHasMore(false);
      return;
    }
    const nextLimit = Math.max(1, Number(limit) || LEDGER_INITIAL);
    if (append) setLedgerLoadingMore(true);
    else setLedgerLoading(true);
    Promise.all([
      fetchMemberProfile().catch(() => null),
      fetchCatfoodLedger(nextLimit).catch(() => null),
    ])
      .then(([profile, ledger]) => {
        if (profile?.signed_in && profile.catfood != null) {
          setCatfood(Number(profile.catfood));
          setCatfoodFree(
            profile.catfood_free == null || Number.isNaN(Number(profile.catfood_free))
              ? null
              : Number(profile.catfood_free),
          );
          setCatfoodPaid(
            profile.catfood_paid == null || Number.isNaN(Number(profile.catfood_paid))
              ? null
              : Number(profile.catfood_paid),
          );
          setCatfoodFreeExpiresAt(String(profile.catfood_free_expires_at || '').trim() || null);
        } else if (ledger?.available && ledger.catfood != null) {
          setCatfood(Number(ledger.catfood));
          setCatfoodFree(null);
          setCatfoodPaid(null);
          setCatfoodFreeExpiresAt(null);
        } else {
          setCatfood(null);
          setCatfoodFree(null);
          setCatfoodPaid(null);
          setCatfoodFreeExpiresAt(null);
        }
        const items = Array.isArray(ledger?.items) ? ledger.items : [];
        setLedgerItems(items);
        setLedgerLimit(nextLimit);
        setLedgerHasMore(items.length >= nextLimit);
      })
      .finally(() => {
        setLedgerLoading(false);
        setLedgerLoadingMore(false);
      });
  }, []);

  const handleLedgerLoadMore = useCallback(() => {
    loadLedger(true, { limit: ledgerLimit + LEDGER_MORE, append: true });
  }, [ledgerLimit, loadLedger]);

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
      <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap" useFlexGap>
        <Typography variant="subtitle1" fontWeight={700}>
          会员
        </Typography>
        {!configured ? <BecomeMemberLink variant="button" /> : null}
      </Stack>
      <Typography variant="body2" color="text.secondary">
        把官网会员中心的通用凭证贴到这里，或直接把文件放到
        {' '}
        {filePath}
        。文件里是有效凭证后，新茶会通过官网回答（NTQ AI）。没有这份凭证时，可在 AI 配置里使用自己的密钥。
        {!configured ? ' 还没有账号时，先点上方「成为会员」注册，再到会员中心复制通用凭证回来装载。' : null}
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
      </Stack>
      {configured && catfood != null && Number.isFinite(catfood) ? (
        <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.6 }}>
          {(() => {
            const total = Number(catfood).toFixed(2);
            const free = catfoodFree != null && Number.isFinite(catfoodFree)
              ? Number(catfoodFree)
              : null;
            const paid = catfoodPaid != null && Number.isFinite(catfoodPaid)
              ? Number(catfoodPaid)
              : null;
            const expire = catfoodFreeExpiresAt;
            if (free != null && free > 0 && expire) {
              return (
                <>
                  您还有
                  {' '}
                  <Box component="span" sx={{ color: 'primary.main', fontWeight: 600 }}>
                    {total}
                  </Box>
                  {' '}
                  猫粮，其中
                  {' '}
                  <Box component="span" sx={{ color: 'primary.main', fontWeight: 600 }}>
                    {free.toFixed(2)}
                  </Box>
                  {' '}
                  （月赠）在
                  {' '}
                  {expire}
                  {' '}
                  过期
                  {paid != null && paid > 0 ? (
                    <>
                      ；另有
                      {' '}
                      <Box component="span" sx={{ color: 'primary.main', fontWeight: 600 }}>
                        {paid.toFixed(2)}
                      </Box>
                      {' '}
                      充值余额不过期
                    </>
                  ) : null}
                  。
                </>
              );
            }
            return (
              <>
                您还有
                {' '}
                <Box component="span" sx={{ color: 'primary.main', fontWeight: 600 }}>
                  {total}
                </Box>
                {' '}
                猫粮
                {paid != null && paid > 0 ? '（充值余额不过期）' : ''}
                。
              </>
            );
          })()}
        </Typography>
      ) : null}
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
              disabled={ledgerLoading || ledgerLoadingMore}
              onClick={() => loadLedger(true, { limit: LEDGER_INITIAL })}
            >
              刷新
            </Button>
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            最近对话消耗、月赠与调整。默认最近
            {LEDGER_INITIAL}
            条。
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
              {ledgerHasMore ? (
                <Box sx={{ pt: 0.5 }}>
                  <Button
                    size="small"
                    variant="text"
                    disabled={ledgerLoadingMore}
                    onClick={handleLedgerLoadMore}
                  >
                    {ledgerLoadingMore ? '加载中…' : `查看更多（再 ${LEDGER_MORE} 条）`}
                  </Button>
                </Box>
              ) : null}
            </Stack>
          ) : null}
        </Box>
      ) : null}
    </Stack>
  );
}

/** NTQ AI：只读指引，不在此页配置凭证。 */
function NtqProxyCard({ configured }) {
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
          label={configured ? '已配置' : '未配置'}
        />
      </Stack>
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
        官网代理 · 只读提示（凭证在「会员」页配置）
      </Typography>
      {configured ? (
        <Typography variant="body2" sx={{ mt: 1.5 }}>
          NTQ AI 已配置，可直接使用。若想使用自己的模型，可在 AI 交互框中选择下方已配置的其他 AI。
        </Typography>
      ) : (
        <Typography variant="body2" sx={{ mt: 1.5 }}>
          尚未配置 NTQ AI。请先到
          {' '}
          <Link component={RouterLink} to="/settings/membership" underline="hover">
            设置 → 会员
          </Link>
          {' '}
          放入会员 token；本页只做指引，不在这里填写凭证。
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
        AI 配置
      </Typography>
      <Typography variant="body2" color="text.secondary">
        NTQ AI 状态见下方提示；自有供应商可在此写入 API Key。页面不会回读明文，只会显示是否已配置。
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
              还没有发现大模型供应商。需要先在 userspace/extensions/llm_providers/ 下放好供应商目录和 config.py。
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

/** Agent 产品设置：默认通道、偏好、补充说明、清空会话。不含超时/步数等高级项。 */
export function SettingsAgentPanel() {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [saveOk, setSaveOk] = useState('');
  const [saveError, setSaveError] = useState('');
  const [saving, setSaving] = useState(false);
  const [providerOptions, setProviderOptions] = useState([{ id: 'ntq', label: 'NTQ AI' }]);
  const [defaultProviderId, setDefaultProviderId] = useState('ntq');
  const [contextPrompt, setContextPrompt] = useState('');
  const [contextPromptMaxChars, setContextPromptMaxChars] = useState(2000);
  const [preferences, setPreferences] = useState([]);
  const [preferenceMaxRules, setPreferenceMaxRules] = useState(40);
  const [preferenceMaxChars, setPreferenceMaxChars] = useState(200);
  const [draftRule, setDraftRule] = useState('');
  const [clearBusy, setClearBusy] = useState(false);
  const [clearOk, setClearOk] = useState('');
  const [clearError, setClearError] = useState('');

  const applySettings = useCallback((settings) => {
    setDefaultProviderId(settings.defaultProviderId || 'ntq');
    setContextPrompt(settings.contextPrompt || '');
    setContextPromptMaxChars(settings.contextPromptMaxChars || 2000);
    setPreferences(Array.isArray(settings.preferences) ? settings.preferences : []);
    setPreferenceMaxRules(settings.preferenceMaxRules || 40);
    setPreferenceMaxChars(settings.preferenceMaxChars || 200);
  }, []);

  const load = useCallback(() => {
    setLoadError('');
    setLoading(true);
    Promise.all([
      fetchAgentSettings(),
      listAiProviders().catch(() => []),
      fetchMembershipSettings().catch(() => ({ configured: false })),
    ])
      .then(([settings, providers, membership]) => {
        applySettings(settings);
        const options = [{ id: 'ntq', label: membership?.configured ? 'NTQ AI（已配置）' : 'NTQ AI' }];
        (Array.isArray(providers) ? providers : []).forEach((item) => {
          if (!item?.providerId || !item.enabled || !item.hasApiKey) return;
          options.push({ id: String(item.providerId), label: String(item.providerId) });
        });
        setProviderOptions(options);
        if (!options.some((item) => item.id === settings.defaultProviderId)) {
          setDefaultProviderId(options[0]?.id || 'ntq');
        }
      })
      .catch((e) => {
        setLoadError(e?.message || '读取 Agent 设置失败');
      })
      .finally(() => setLoading(false));
  }, [applySettings]);

  useEffect(() => {
    load();
  }, [load]);

  const handleAddPreference = () => {
    const text = draftRule.trim().slice(0, preferenceMaxChars);
    if (!text) return;
    if (preferences.includes(text)) {
      setDraftRule('');
      return;
    }
    if (preferences.length >= preferenceMaxRules) {
      setSaveError(`最多 ${preferenceMaxRules} 条偏好`);
      return;
    }
    setPreferences((prev) => [...prev, text]);
    setDraftRule('');
    setSaveError('');
  };

  const handleRemovePreference = (rule) => {
    setPreferences((prev) => prev.filter((item) => item !== rule));
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveOk('');
    setSaveError('');
    try {
      const next = await saveAgentSettings({
        defaultProviderId,
        contextPrompt,
        preferences,
      });
      applySettings(next);
      persistDockSelectedId(next.defaultProviderId);
      setSaveOk('已保存 Agent 设置。');
    } catch (e) {
      setSaveError(e?.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleClearSession = async () => {
    setClearBusy(true);
    setClearOk('');
    setClearError('');
    try {
      await clearAgentSession();
      setClearOk('已清空本机会话对话与局部任务状态。跨会话偏好与策略文件未改动。');
    } catch (e) {
      setClearError(e?.message || '清空会话失败');
    } finally {
      setClearBusy(false);
    }
  };

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="subtitle1" fontWeight={700}>
          Agent 配置
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          管理助理的默认通道、跨会话偏好与补充说明。密钥仍在「AI 配置」；会员凭证在「会员」。
        </Typography>
      </Box>

      {loadError ? <Alert severity="error">{loadError}</Alert> : null}
      {saveError ? <Alert severity="error">{saveError}</Alert> : null}
      {saveOk ? <Alert severity="success">{saveOk}</Alert> : null}
      {clearError ? <Alert severity="error">{clearError}</Alert> : null}
      {clearOk ? <Alert severity="success">{clearOk}</Alert> : null}

      {loading ? (
        <PageLoadingState message="正在加载 Agent 设置…" minHeight="36vh" />
      ) : (
        <Stack spacing={3} sx={{ maxWidth: 560 }}>
          <Stack spacing={1.5}>
            <Typography variant="subtitle2" fontWeight={700}>
              默认 AI 通道
            </Typography>
            <Typography variant="body2" color="text.secondary">
              打开聊天框且尚未手动切换时使用。可随时在聊天框里改选；密钥请到「AI 配置」填写。
            </Typography>
            <FormControl size="small" fullWidth>
              <InputLabel id="agent-default-provider-label">默认通道</InputLabel>
              <Select
                labelId="agent-default-provider-label"
                label="默认通道"
                value={
                  providerOptions.some((item) => item.id === defaultProviderId)
                    ? defaultProviderId
                    : (providerOptions[0]?.id || 'ntq')
                }
                onChange={(e) => setDefaultProviderId(e.target.value)}
              >
                {providerOptions.map((item) => (
                  <MenuItem key={item.id} value={item.id}>
                    {item.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>

          <Stack spacing={1.5}>
            <Typography variant="subtitle2" fontWeight={700}>
              跨会话偏好
            </Typography>
            <Typography variant="body2" color="text.secondary">
              每条会长期带入对话（最多
              {preferenceMaxRules}
              条，每条
              {preferenceMaxChars}
              字）。清空会话不会删这些。
            </Typography>
            {preferences.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                还没有偏好。
              </Typography>
            ) : (
              <Stack spacing={0.75}>
                {preferences.map((rule) => (
                  <Stack
                    key={rule}
                    direction="row"
                    spacing={1}
                    alignItems="center"
                    sx={{
                      py: 0.5,
                      borderBottom: '1px solid',
                      borderColor: 'divider',
                    }}
                  >
                    <Typography variant="body2" sx={{ flex: 1 }}>
                      {rule}
                    </Typography>
                    <Button size="small" onClick={() => handleRemovePreference(rule)}>
                      删除
                    </Button>
                  </Stack>
                ))}
              </Stack>
            )}
            <Stack direction="row" spacing={1} alignItems="flex-start">
              <TextField
                size="small"
                fullWidth
                label="新增偏好"
                placeholder="例如：回答尽量简短"
                value={draftRule}
                onChange={(e) => setDraftRule(e.target.value.slice(0, preferenceMaxChars))}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddPreference();
                  }
                }}
                helperText={`${draftRule.length}/${preferenceMaxChars}`}
              />
              <Button
                variant="outlined"
                sx={{ mt: '2px', flexShrink: 0 }}
                disabled={!draftRule.trim() || preferences.length >= preferenceMaxRules}
                onClick={handleAddPreference}
              >
                添加
              </Button>
            </Stack>
          </Stack>

          <Stack spacing={1.5}>
            <Typography variant="subtitle2" fontWeight={700}>
              补充说明
            </Typography>
            <Typography variant="body2" color="text.secondary">
              追加到助理上下文（不会覆盖产品红线）。适合写风格或常用约定，最多
              {' '}
              {contextPromptMaxChars}
              {' '}
              字。
            </Typography>
            <TextField
              size="small"
              fullWidth
              multiline
              minRows={4}
              value={contextPrompt}
              onChange={(e) => setContextPrompt(e.target.value.slice(0, contextPromptMaxChars))}
              placeholder="例如：优先用中文解释；涉及回测先确认区间。"
              helperText={`${contextPrompt.length}/${contextPromptMaxChars}`}
            />
          </Stack>

          <Stack spacing={1.5}>
            <Typography variant="subtitle2" fontWeight={700}>
              会话
            </Typography>
            <Typography variant="body2" color="text.secondary">
              清空本机当前会话的对话记录与局部任务状态。不会删除跨会话偏好、策略代码或回测报告。
            </Typography>
            <Box>
              <Button
                variant="outlined"
                color="inherit"
                disabled={clearBusy || saving}
                onClick={handleClearSession}
              >
                {clearBusy ? '清空中…' : '清空本机会话'}
              </Button>
            </Box>
          </Stack>

          <Box>
            <Button variant="contained" onClick={handleSave} disabled={saving}>
              {saving ? '保存中…' : '保存 Agent 设置'}
            </Button>
            <Button sx={{ ml: 1 }} variant="outlined" onClick={load} disabled={saving || clearBusy}>
              重新读取
            </Button>
          </Box>
        </Stack>
      )}
    </Stack>
  );
}
