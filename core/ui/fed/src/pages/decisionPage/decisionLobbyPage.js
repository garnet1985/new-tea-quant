import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
  Paper,
  Snackbar,
  Stack,
  Typography,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import { zhCN } from '@mui/x-data-grid/locales';
import PageLayout from '../../components/pageLayout/pageLayout';
import {
  DECISION_STRATEGY,
  INITIAL_SESSIONS,
  formatMoney,
  newPlayPath,
  playPath,
} from './mockDecisionData';
import './decisionPage.scss';

function AccentCount({ value }) {
  return (
    <Box component="span" className="decision-entry-card__count">
      {value}
    </Box>
  );
}

function DecisionLobbyPage() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState(INITIAL_SESSIONS);
  const [panel, setPanel] = useState(null);
  const [reportSession, setReportSession] = useState(null);
  const [toast, setToast] = useState('');

  const unfinished = useMemo(
    () => sessions.filter((row) => row.status === 'in_progress'),
    [sessions],
  );
  const nextId = useMemo(
    () => sessions.reduce((max, row) => Math.max(max, row.id), 0) + 1,
    [sessions],
  );

  useEffect(() => {
    if (panel === 'continue' && unfinished.length === 0) setPanel(null);
  }, [panel, unfinished.length]);

  const deleteSession = (id) => {
    setSessions((prev) => prev.filter((row) => row.id !== id));
    setToast(`已删除第 ${id} 局（本地 mock，不写盘）`);
  };

  const continueColumns = [
    { field: 'id', headerName: '局', width: 72 },
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
      field: 'cash',
      headerName: '现金',
      minWidth: 140,
      flex: 0.7,
      valueFormatter: (params) => formatMoney(params.value),
    },
    { field: 'holdings', headerName: '持仓', width: 80 },
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
          onClick={() => navigate(playPath(params.row))}
        >
          继续
        </Button>
      ),
    },
  ];

  const manageColumns = [
    { field: 'id', headerName: '局', width: 72 },
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
      field: 'cash',
      headerName: '现金',
      minWidth: 140,
      flex: 0.7,
      valueFormatter: (params) => formatMoney(params.value),
    },
    { field: 'holdings', headerName: '持仓', width: 80 },
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
            onClick={() => deleteSession(params.row.id)}
          >
            删除
          </Button>
        </Stack>
      ),
    },
  ];

  const panelRows = panel === 'continue' ? unfinished : sessions;
  const panelColumns = panel === 'continue' ? continueColumns : manageColumns;

  return (
    <PageLayout
      className="decision-page"
      breadcrumbsItems={[{ label: '决策者', to: '/decision' }]}
      breadcrumbsCurrent="入口"
      bannerTitle="决策者模式"
      bannerDescription="回放当前策略的资金模拟。人只改「选谁」和「买多少股」；纪律出场、现金与手数约束不变。"
      bannerRightSlot={<Chip size="small" variant="outlined" label="静态 UI · 未接 API" />}
    >
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
        <Chip size="small" label={`策略 ${DECISION_STRATEGY.key}`} />
        <Chip size="small" variant="outlined" label={`version ${DECISION_STRATEGY.versionId}`} />
        <Typography variant="body2" color="text.secondary" sx={{ alignSelf: 'center' }}>
          回测区间 {DECISION_STRATEGY.range}
        </Typography>
      </Stack>

      <Box className="decision-entry-grid" sx={{ mb: 2 }}>
        <Card variant="outlined" className="decision-entry-card">
          <CardActionArea onClick={() => navigate(newPlayPath())}>
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
            unfinished.length === 0 ? 'is-disabled' : '',
            panel === 'continue' ? 'is-active' : '',
          ].filter(Boolean).join(' ')}
        >
          <CardActionArea
            onClick={() => setPanel((current) => (current === 'continue' ? null : 'continue'))}
            disabled={unfinished.length === 0}
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
          className={`decision-entry-card${panel === 'manage' ? ' is-active' : ''}`}
        >
          <CardActionArea onClick={() => setPanel((current) => (current === 'manage' ? null : 'manage'))}>
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
                : `${DECISION_STRATEGY.key}/results/simulations/${DECISION_STRATEGY.versionId}/decision/`}
            </Typography>
          </Stack>
          <DataGrid
            autoHeight
            rows={panelRows}
            columns={panelColumns}
            localeText={zhCN.components.MuiDataGrid.defaultProps.localeText}
            hideFooter
            disableRowSelectionOnClick
            sx={{ border: 0, '& .MuiDataGrid-cell': { py: 1 } }}
          />
        </Paper>
      ) : null}

      <Dialog open={Boolean(reportSession)} onClose={() => setReportSession(null)} maxWidth="sm" fullWidth>
        <DialogTitle>
          终局报告 · 第 {reportSession?.id} 局
        </DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2" color="text.secondary">
            报告占位。接入后将展示与机器 portfolio 同结构的资金结果（收益、回撤、对照等），此处暂不进入对局。
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReportSession(null)}>关闭</Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={Boolean(toast)}
        autoHideDuration={2200}
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
