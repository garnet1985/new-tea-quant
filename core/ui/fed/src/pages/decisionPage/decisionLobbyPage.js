import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Paper,
  Snackbar,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import { zhCN } from '@mui/x-data-grid/locales';
import {
  fetchStrategyList,
  fetchStrategySettings,
  getStrategyDisplayLabel,
} from '../../api/strategyApi';
import {
  decisionLobbyPath,
  decisionPlayPath,
  fetchDecisionSessions,
  deleteDecisionSession,
  openDecisionSession,
  readSimulationRange,
} from '../../api/decisionApi';
import PageLayout from '../../components/pageLayout/pageLayout';
import InlineLoadingState from '../../components/inlineLoadingState/inlineLoadingState';
import { NTQ_DATA_GRID_LOADING_SLOTS } from '../../components/dataGridLoadingOverlay/dataGridLoadingOverlay';
import { formatDateTime } from '../../utils/formatDateTime';
import { isHttpStatusError } from 'services/request';
import './decisionPage.scss';

function AccentCount({ value }) {
  return (
    <Box component="span" className="decision-entry-card__count">
      {value}
    </Box>
  );
}

function errorMessage(err, fallback) {
  if (isHttpStatusError(err) && err.message) return err.message;
  return String(err?.message || fallback);
}

function DecisionLobbyPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const strategyFromUrl = String(searchParams.get('strategy') || '').trim();

  const [catalog, setCatalog] = useState([]);
  const [catalogReady, setCatalogReady] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [versionId, setVersionId] = useState('');
  const [rangeLabel, setRangeLabel] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [busy, setBusy] = useState(false);
  const [panel, setPanel] = useState(null);
  const [reportSession, setReportSession] = useState(null);
  const [toast, setToast] = useState('');

  const strategyKey = strategyFromUrl;
  const strategyOptions = useMemo(
    () => catalog.filter((row) => row.name),
    [catalog],
  );

  const unfinished = useMemo(
    () => sessions.filter((row) => row.status === 'in_progress'),
    [sessions],
  );
  const nextId = useMemo(() => {
    const maxId = sessions.reduce((max, row) => {
      const n = Number(row.dmId);
      return Number.isFinite(n) ? Math.max(max, n) : max;
    }, 0);
    return maxId + 1;
  }, [sessions]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetchStrategyList();
        if (cancelled) return;
        const rows = Array.isArray(res?.data) ? res.data : [];
        setCatalog(rows);
      } catch (err) {
        if (!cancelled) setLoadError(errorMessage(err, '无法加载策略目录'));
      } finally {
        if (!cancelled) setCatalogReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!catalogReady || strategyFromUrl || strategyOptions.length === 0) return;
    const enabled = strategyOptions.find((row) => row.is_enabled) || strategyOptions[0];
    setSearchParams({ strategy: enabled.name }, { replace: true });
  }, [catalogReady, strategyFromUrl, strategyOptions, setSearchParams]);

  const reloadSessions = useCallback(async (key) => {
    if (!key) {
      setSessions([]);
      setVersionId('');
      setRangeLabel('');
      setLoading(false);
      return;
    }
    setLoading(true);
    setLoadError('');
    try {
      const [listed, settings] = await Promise.all([
        fetchDecisionSessions(key),
        fetchStrategySettings(key).catch(() => null),
      ]);
      setSessions(listed.sessions);
      setVersionId(listed.versionId || settings?.workbench_version_id || '');
      const range = readSimulationRange(settings?.settings || settings?.disk_settings || {});
      if (range.start && range.end) setRangeLabel(`${range.start} → ${range.end}`);
      else setRangeLabel('');
    } catch (err) {
      setSessions([]);
      setVersionId('');
      setLoadError(errorMessage(err, '无法加载决策会话'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!catalogReady) return;
    reloadSessions(strategyKey);
  }, [catalogReady, strategyKey, reloadSessions]);

  useEffect(() => {
    if (panel === 'continue' && unfinished.length === 0) setPanel(null);
  }, [panel, unfinished.length]);

  const onStrategyChange = (event) => {
    const next = String(event.target.value || '').trim();
    setPanel(null);
    setLoadError('');
    if (next) setSearchParams({ strategy: next });
    else setSearchParams({});
  };

  const startNewGame = async () => {
    if (!strategyKey || busy) return;
    setBusy(true);
    try {
      const snap = await openDecisionSession(strategyKey, { newSession: true });
      navigate(decisionPlayPath({ strategy: strategyKey, session: snap.dmId }));
    } catch (err) {
      setToast(errorMessage(err, '无法开新局'));
    } finally {
      setBusy(false);
    }
  };

  const deleteSession = async (row) => {
    if (!strategyKey || !row?.dmId) return;
    try {
      await deleteDecisionSession(strategyKey, row.dmId);
      setToast(`已删除第 ${row.dmId} 局`);
      await reloadSessions(strategyKey);
    } catch (err) {
      setToast(errorMessage(err, '删除失败'));
    }
  };

  const continueColumns = [
    { field: 'dmId', headerName: '局', width: 72 },
    {
      field: 'status',
      headerName: '状态',
      width: 120,
      renderCell: () => (
        <Chip size="small" label="进行中" color="warning" variant="outlined" />
      ),
    },
    { field: 'date', headerName: '停在', minWidth: 128, flex: 0.6 },
    {
      field: 'updatedAt',
      headerName: '更新',
      minWidth: 140,
      flex: 0.8,
      valueFormatter: (params) => formatDateTime(params.value),
    },
    {
      field: 'actions',
      headerName: '操作',
      sortable: false,
      minWidth: 120,
      flex: 0.6,
      renderCell: (params) => (
        <Button
          size="small"
          variant="contained"
          onClick={() => navigate(decisionPlayPath({
            strategy: strategyKey,
            session: params.row.dmId,
          }))}
        >
          继续
        </Button>
      ),
    },
  ];

  const manageColumns = [
    { field: 'dmId', headerName: '局', width: 72 },
    {
      field: 'status',
      headerName: '状态',
      width: 120,
      renderCell: (params) => (
        <Chip
          size="small"
          label={params.value === 'completed' ? '已完成' : '进行中'}
          color={params.value === 'completed' ? 'success' : 'warning'}
          variant="outlined"
        />
      ),
    },
    { field: 'date', headerName: '停在', minWidth: 128, flex: 0.6 },
    {
      field: 'updatedAt',
      headerName: '更新',
      minWidth: 140,
      flex: 0.8,
      valueFormatter: (params) => formatDateTime(params.value),
    },
    {
      field: 'actions',
      headerName: '操作',
      sortable: false,
      minWidth: 220,
      flex: 1,
      renderCell: (params) => (
        <Stack direction="row" spacing={1}>
          {params.row.status === 'completed' ? (
            <Button
              size="small"
              variant="outlined"
              onClick={() => setReportSession(params.row)}
            >
              查看报告
            </Button>
          ) : null}
          <Button
            size="small"
            variant="outlined"
            color="error"
            onClick={() => deleteSession(params.row)}
          >
            删除
          </Button>
        </Stack>
      ),
    },
  ];

  const panelRows = panel === 'continue' ? unfinished : sessions;
  const panelColumns = panel === 'continue' ? continueColumns : manageColumns;
  const canPlay = Boolean(strategyKey) && !loadError && !loading && !busy;

  return (
    <PageLayout
      className="decision-page"
      breadcrumbsItems={[{ label: '决策者', to: decisionLobbyPath(strategyKey) }]}
      breadcrumbsCurrent="入口"
      bannerTitle="决策者模式"
      bannerDescription="回放当前策略的资金模拟。人只改「选谁」和「买多少股」；纪律出场、现金与手数约束不变。"
    >
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }} alignItems="center">
        <TextField
          select
          size="small"
          label="策略"
          value={strategyKey}
          onChange={onStrategyChange}
          sx={{ minWidth: 220 }}
          disabled={!catalogReady || strategyOptions.length === 0}
        >
          {strategyOptions.length === 0 || !strategyKey ? (
            <MenuItem value="">{strategyOptions.length === 0 ? '暂无策略' : '选择策略'}</MenuItem>
          ) : null}
          {strategyKey && !strategyOptions.some((row) => row.name === strategyKey) ? (
            <MenuItem value={strategyKey}>{strategyKey}</MenuItem>
          ) : null}
          {strategyOptions.map((row) => (
            <MenuItem key={row.name} value={row.name}>
              {getStrategyDisplayLabel(row) || row.name}
            </MenuItem>
          ))}
        </TextField>
        {versionId ? (
          <Chip size="small" variant="outlined" label={`version ${versionId}`} />
        ) : null}
        {rangeLabel ? (
          <Typography variant="body2" color="text.secondary">
            回测区间 {rangeLabel}
          </Typography>
        ) : null}
      </Stack>

      {catalogReady && strategyOptions.length === 0 && !loadError ? (
        <Alert severity="info" variant="outlined" sx={{ mb: 2 }}>
          目录里还没有策略。先到制定策略里添加或导入后再来开局。
        </Alert>
      ) : null}

      {loadError ? (
        <Alert severity="error" variant="outlined" sx={{ mb: 2 }}>
          {loadError}
        </Alert>
      ) : null}

      {!catalogReady || (loading && strategyKey) ? (
        <InlineLoadingState block message="正在加载决策会话…" />
      ) : (
        <>
          <Box className="decision-entry-grid" sx={{ mb: 2 }}>
            <Card variant="outlined" className={`decision-entry-card${canPlay ? '' : ' is-disabled'}`}>
              <CardActionArea onClick={startNewGame} disabled={!canPlay}>
                <CardContent className="decision-entry-card__body">
                  <Typography variant="h6">开始新决策</Typography>
                  <Typography variant="body2" color="text.secondary">
                    从区间第一天的入场机会开一局。时钟只停在有抉择的日子，空日自动跳过。
                  </Typography>
                  <Typography className="decision-entry-card__stat" component="p">
                    将开第
                    <AccentCount value={nextId} />
                    局
                  </Typography>
                </CardContent>
              </CardActionArea>
            </Card>

            <Card
              variant="outlined"
              className={[
                'decision-entry-card',
                unfinished.length === 0 || !canPlay ? 'is-disabled' : '',
                panel === 'continue' ? 'is-active' : '',
              ].filter(Boolean).join(' ')}
            >
              <CardActionArea
                onClick={() => setPanel((current) => (current === 'continue' ? null : 'continue'))}
                disabled={unfinished.length === 0 || !canPlay}
              >
                <CardContent className="decision-entry-card__body">
                  <Typography variant="h6">继续</Typography>
                  <Typography variant="body2" color="text.secondary">
                    从进行中的对局里选一局接着下。没有未完成的对局时不可用。
                  </Typography>
                  <Typography className="decision-entry-card__stat" component="p">
                    <AccentCount value={unfinished.length} />
                    局进行中
                  </Typography>
                </CardContent>
              </CardActionArea>
            </Card>

            <Card
              variant="outlined"
              className={[
                'decision-entry-card',
                !canPlay ? 'is-disabled' : '',
                panel === 'manage' ? 'is-active' : '',
              ].filter(Boolean).join(' ')}
            >
              <CardActionArea
                onClick={() => setPanel((current) => (current === 'manage' ? null : 'manage'))}
                disabled={!canPlay}
              >
                <CardContent className="decision-entry-card__body">
                  <Typography variant="h6">管理</Typography>
                  <Typography variant="body2" color="text.secondary">
                    删除存档；已完成的对局可以查看报告。管理里不能进入对局。
                  </Typography>
                  <Typography className="decision-entry-card__stat" component="p">
                    共
                    <AccentCount value={sessions.length} />
                    局记录
                  </Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          </Box>

          {panel ? (
            <Paper className="decision-grid-paper">
              <Stack
                direction="row"
                alignItems="center"
                justifyContent="space-between"
                sx={{ px: 1.5, pt: 1.5, pb: 1 }}
              >
                <Typography variant="subtitle1" fontWeight={700}>
                  {panel === 'continue' ? '选择要继续的一局' : '管理存档'}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {panel === 'continue'
                    ? '只能选一局未完成的继续'
                    : `${strategyKey}${versionId ? `/results/simulations/${versionId}/decision/` : ''}`}
                </Typography>
              </Stack>
              <DataGrid
                autoHeight
                rows={panelRows}
                columns={panelColumns}
                localeText={zhCN.components.MuiDataGrid.defaultProps.localeText}
                hideFooter
                disableRowSelectionOnClick
                slots={NTQ_DATA_GRID_LOADING_SLOTS}
                sx={{ border: 0, '& .MuiDataGrid-cell': { py: 1 } }}
              />
            </Paper>
          ) : null}
        </>
      )}

      <Dialog open={Boolean(reportSession)} onClose={() => setReportSession(null)} maxWidth="sm" fullWidth>
        <DialogTitle>
          终局报告 · 第 {reportSession?.dmId} 局
        </DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2" color="text.secondary">
            决策者终局报告路由尚未注册。走完后的资金结果写在该局目录里，对照可走现有 portfolio 报告；此处暂不进入对局。
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReportSession(null)}>关闭</Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={Boolean(toast)}
        autoHideDuration={2800}
        onClose={() => setToast('')}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert severity="info" variant="outlined" onClose={() => setToast('')}>
          {toast}
        </Alert>
      </Snackbar>
    </PageLayout>
  );
}

export default DecisionLobbyPage;
