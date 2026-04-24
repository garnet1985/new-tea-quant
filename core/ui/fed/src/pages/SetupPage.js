import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Backdrop,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  CircularProgress,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Stack,
  Step,
  StepLabel,
  Stepper,
  TextField,
  Typography,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded';
import CancelRoundedIcon from '@mui/icons-material/CancelRounded';
import AutorenewRoundedIcon from '@mui/icons-material/AutorenewRounded';
import RadioButtonUncheckedRoundedIcon from '@mui/icons-material/RadioButtonUncheckedRounded';
import { Link as RouterLink } from 'react-router-dom';
import {
  getSetupDefinition,
  getImportDataProgress,
  getSetupStatus,
  precheckDbConnection,
  precheckUserspacePath,
  resetSetupStatus,
  retryFailedStep,
  startSetupWorkflow,
  submitInteractiveStep,
} from '../api/apis/setupApi';

const STEP_STATUS = {
  NOT_STARTED: 'not_started',
  WAITING_INPUT: 'waiting_input',
  RUNNING: 'running',
  SUCCESS: 'success',
  FAILED: 'failed',
};
const DEFAULT_STEP_ID = 'db_connection';
const EMPTY_IMPORT_PROGRESS = {
  running: false,
  totalTables: 0,
  completedCount: 0,
  currentTable: '',
  percent: 0,
};

function SetupPage() {
  const [definition, setDefinition] = useState([]);
  const [status, setStatus] = useState(null);
  const [flowStage, setFlowStage] = useState('input');
  const [runningStep, setRunningStep] = useState('');
  const [progressText, setProgressText] = useState('等待开始');
  const [errorMessage, setErrorMessage] = useState('');
  const [failedStep, setFailedStep] = useState('');
  const [pausedStep, setPausedStep] = useState('');
  const [formValues, setFormValues] = useState({});
  const [userspacePathEditable, setUserspacePathEditable] = useState(false);
  const [overwriteConfirmOpen, setOverwriteConfirmOpen] = useState(false);
  const [dbRiskConfirmOpen, setDbRiskConfirmOpen] = useState(false);
  const [dbRiskContext, setDbRiskContext] = useState({ dbType: '', database: '' });
  const [bootstrapping, setBootstrapping] = useState(true);
  const [userspacePathExists, setUserspacePathExists] = useState(false);
  const [checkingUserspacePath, setCheckingUserspacePath] = useState(false);
  const [importProgress, setImportProgress] = useState(EMPTY_IMPORT_PROGRESS);

  const restoreFlowStage = (defs, current) => {
    const stepStates = current?.stepStates || [];
    const stateById = new Map(stepStates.map((item) => [item.stepId, item]));
    const allSuccess = defs.length > 0 && defs.every((step) => stateById.get(step.id)?.status === STEP_STATUS.SUCCESS);

    if (allSuccess || current?.isReady) {
      setFlowStage('success');
      setProgressText('安装完成');
      setFailedStep('');
      setPausedStep('');
      return;
    }

    // 未完成时始终回到“开始安装”入口，避免用户刚进入页面就被自动恢复到中间步骤而产生困惑。
    setFlowStage('input');
    setProgressText('点击“开始安装”将从第一步重新执行');
    setRunningStep('');
    setFailedStep('');
    setPausedStep('');
    setErrorMessage('');
  };

  useEffect(() => {
    Promise.all([getSetupDefinition(), getSetupStatus()])
      .then(([defs, current]) => {
        if (current?.isReady) {
          setDefinition(defs);
          setStatus(current);
          restoreFlowStage(defs, current);
          return;
        }

        // 产品语义：入口只允许“未开始”或“已完成”，禁止显示中间态（如 50%）。
        resetSetupStatus().then((fresh) => {
          setDefinition(defs);
          setStatus(fresh);
          restoreFlowStage(defs, fresh);
        });
      })
      .finally(() => {
        setBootstrapping(false);
      });
  }, []);

  const activeStep = useMemo(() => {
    if (!status || definition.length === 0) return 0;
    if (flowStage === 'input') return 0;
    const firstPendingIndex = definition.findIndex((step) => {
      const state = (status.stepStates || []).find((item) => item.stepId === step.id);
      return state?.status !== STEP_STATUS.SUCCESS;
    });
    return firstPendingIndex < 0 ? definition.length : firstPendingIndex;
  }, [definition, flowStage, status]);

  const rows = useMemo(() => {
    if (!status || definition.length === 0) return [];
    const stateById = new Map((status.stepStates || []).map((item) => [item.stepId, item]));
    return definition.map((step, idx) => {
      const state = stateById.get(step.id);
      let displayState = '待完成';
      if (flowStage === 'input') displayState = '待开始';
      if (state?.status === STEP_STATUS.SUCCESS) displayState = '已完成';
      if (state?.status === STEP_STATUS.FAILED) displayState = '失败';
      if (state?.status === STEP_STATUS.WAITING_INPUT) displayState = '待输入';
      return {
        id: step.id,
        stepId: step.id,
        order: idx + 1,
        name: step.name,
        state: displayState,
        detail: step.description,
      };
    });
  }, [definition, flowStage, status]);

  const runningWithProgress = (runner) => runner(({ stepId, status: progressStatus, snapshot }) => {
    setRunningStep(progressStatus === 'running' ? stepId : '');
    if (progressStatus === 'running') {
      const label = definition.find((step) => step.id === stepId)?.name || stepId;
      setProgressText(`正在执行: ${label}`);
    }
    if (snapshot) setStatus(snapshot);
  });

  const consumePipelineResult = (result, defaultFailedStep = DEFAULT_STEP_ID) => {
    setRunningStep('');
    if (result.ok) {
      setStatus(result.status);
      setFlowStage('success');
      setProgressText('安装完成');
      setFailedStep('');
      setPausedStep('');
      return;
    }
    if (result.kind === 'paused') {
      setStatus(result.status);
      setFlowStage('interaction');
      setPausedStep(result.pausedStepId || defaultFailedStep);
      const initialValues = result.status?.inputsByStep?.[result.pausedStepId || defaultFailedStep] || {};
      setFormValues(initialValues);
      setUserspacePathEditable(false);
      setUserspacePathExists(false);
      setProgressText('等待用户输入...');
      setErrorMessage('');
      return;
    }
    setStatus(result.status || status);
    setFlowStage('fail');
    setFailedStep(result.failedStepId || defaultFailedStep);
    setPausedStep('');
    setErrorMessage(result.message || '安装失败，请检查配置后重试。');
  };

  const renderStepStateCell = useCallback((params, pendingLabel = '待完成') => {
    if (runningStep && params.row.id === runningStep) {
      return (
        <Stack direction="row" spacing={1} alignItems="center">
          <AutorenewRoundedIcon
            color="primary"
            sx={{
              animation: 'spin 1s linear infinite',
              '@keyframes spin': {
                '0%': { transform: 'rotate(0deg)' },
                '100%': { transform: 'rotate(360deg)' },
              },
            }}
          />
          <Typography variant="body2">执行中...</Typography>
        </Stack>
      );
    }
    if (params.value === '已完成') {
      return (
        <Stack direction="row" spacing={1} alignItems="center">
          <CheckCircleRoundedIcon sx={{ color: 'success.main' }} />
          <Typography variant="body2">已完成</Typography>
        </Stack>
      );
    }
    if (params.value === '失败') {
      return (
        <Stack direction="row" spacing={1} alignItems="center">
          <CancelRoundedIcon sx={{ color: 'error.main' }} />
          <Typography variant="body2">失败</Typography>
        </Stack>
      );
    }
    if (params.value === '待输入') {
      return (
        <Stack direction="row" spacing={1} alignItems="center">
          <RadioButtonUncheckedRoundedIcon sx={{ color: 'warning.main' }} />
          <Typography variant="body2">待输入</Typography>
        </Stack>
      );
    }
    return (
      <Stack direction="row" spacing={1} alignItems="center">
        <RadioButtonUncheckedRoundedIcon color="disabled" />
        <Typography variant="body2">{pendingLabel}</Typography>
      </Stack>
    );
  }, [runningStep]);

  const executingColumns = useMemo(() => ([
    { field: 'order', headerName: '#', width: 80 },
    { field: 'name', headerName: '步骤', flex: 1 },
    {
      field: 'state',
      headerName: '状态',
      width: 180,
      renderCell: (params) => renderStepStateCell(params, '待完成'),
    },
    { field: 'detail', headerName: '说明', flex: 1.6 },
  ]), [renderStepStateCell]);

  const failColumns = useMemo(() => ([
    { field: 'order', headerName: '#', width: 80 },
    { field: 'name', headerName: '步骤', flex: 1 },
    {
      field: 'state',
      headerName: '状态',
      width: 180,
      renderCell: (params) => renderStepStateCell(params, '未开始'),
    },
    { field: 'detail', headerName: '说明', flex: 1.6 },
  ]), [renderStepStateCell]);

  const handleInputChange = (key, value) => {
    const next = { ...formValues, [key]: value };
    if (key === 'dbType') {
      if (value === 'postgresql') {
        next.host = next.host || 'localhost';
        next.port = '5432';
        next.user = next.user || 'postgres';
        next.defaultPgsqlSchema = next.defaultPgsqlSchema || 'public';
      } else if (value === 'mysql') {
        next.host = next.host || 'localhost';
        next.port = '3306';
        next.user = next.user || 'root';
        next.defaultPgsqlSchema = '';
      }
    }
    setFormValues(next);
  };

  const getFieldDisplayValue = (field) => {
    const current = formValues[field.key];
    if ((current === undefined || current === null || current === '') && field.defaultValue !== undefined) {
      return field.defaultValue;
    }
    return current ?? '';
  };

  const getFieldInputId = (field) => `setup-${pausedStep || 'step'}-${field.key}`;

  const shouldShowUserspaceConflictPolicy = (field) => {
    if (field.key !== 'userspaceConflictPolicy') return true;
    // 默认路径场景：按后端返回的 showByDefault 控制；
    // 自定义路径场景：只看 blur 预检查结果，避免默认路径状态“串”到自定义路径。
    if (userspacePathEditable) {
      return Boolean(userspacePathExists);
    }
    return Boolean(field.showByDefault);
  };

  const handleUserspacePathBlur = async () => {
    if (pausedStep !== 'init_userspace') return;
    const schema = pausedStepDef?.requiredUserInputs || [];
    const hasConflictField = schema.some((field) => field.key === 'userspaceConflictPolicy');
    if (!hasConflictField) return;

    const pathField = schema.find((field) => field.key === 'userspaceTargetPath');
    const value = (formValues.userspaceTargetPath || pathField?.defaultValue || '').trim();
    if (!value) {
      setUserspacePathExists(false);
      return;
    }
    setCheckingUserspacePath(true);
    try {
      const result = await precheckUserspacePath({ userspaceTargetPath: value });
      setUserspacePathExists(Boolean(result.pathExists));
      if (!result.pathExists) {
        setFormValues((prev) => ({ ...prev, userspaceConflictPolicy: 'skip' }));
      }
    } catch (_error) {
      setUserspacePathExists(false);
    } finally {
      setCheckingUserspacePath(false);
    }
  };

  const handleStartSetup = async () => {
    if (!status || definition.length === 0) return;
    setFlowStage('executing');
    setErrorMessage('');
    setFailedStep('');
    setPausedStep('');
    setImportProgress(EMPTY_IMPORT_PROGRESS);
    setProgressText('准备执行安装步骤...');
    const result = await runningWithProgress((onProgress) => startSetupWorkflow(onProgress));
    consumePipelineResult(result, definition[0]?.id || DEFAULT_STEP_ID);
  };

  const handleSubmitInteractionStep = async (options = {}) => {
    const { confirmedOverwrite = false, confirmedDbRisk = false } = options;
    if (!status || !pausedStep) return;
    const schema = pausedStepDef?.requiredUserInputs || [];
    const policyField = schema.find((field) => field.key === 'userspaceConflictPolicy');
    const effectiveConflictPolicy = (
      formValues.userspaceConflictPolicy
      || policyField?.defaultValue
      || 'skip'
    );
    if (
      pausedStep === 'init_userspace'
      && effectiveConflictPolicy === 'overwrite'
      && !confirmedOverwrite
    ) {
      setOverwriteConfirmOpen(true);
      return;
    }
    const submitValues = { ...formValues };
    schema.forEach((field) => {
      const current = submitValues[field.key];
      if ((current === undefined || current === '') && field.defaultValue !== undefined) {
        submitValues[field.key] = field.defaultValue;
      }
    });
    if (pausedStep === 'init_userspace' && !userspacePathExists) {
      submitValues.userspaceConflictPolicy = 'skip';
    }
    if (pausedStep === 'db_connection' && !confirmedDbRisk) {
      const dbCheck = await precheckDbConnection(submitValues);
      if (dbCheck.dbExists) {
        setDbRiskContext({ dbType: dbCheck.dbType || '', database: dbCheck.database || '' });
        setDbRiskConfirmOpen(true);
        return;
      }
    }
    setFlowStage('executing');
    setProgressText('提交输入并继续执行...');
    setErrorMessage('');
    setFailedStep('');
    const result = await runningWithProgress((onProgress) => submitInteractiveStep(pausedStep, submitValues, onProgress));
    consumePipelineResult(result, pausedStep);
  };

  const handleRetryFailedStep = async () => {
    setFlowStage('executing');
    setProgressText('重试失败步骤并继续执行...');
    setErrorMessage('');
    const result = await runningWithProgress((onProgress) => retryFailedStep(onProgress));
    consumePipelineResult(result, failedStep || definition[0]?.id || DEFAULT_STEP_ID);
  };

  const handleRestartSetup = async () => {
    const nextStatus = await resetSetupStatus();
    setStatus(nextStatus);
    setFlowStage('input');
    setRunningStep('');
    setProgressText('等待开始');
    setErrorMessage('');
    setFailedStep('');
    setPausedStep('');
    setFormValues({});
    setUserspacePathEditable(false);
    setUserspacePathExists(false);
    setImportProgress(EMPTY_IMPORT_PROGRESS);
  };

  useEffect(() => {
    if (flowStage !== 'executing' || runningStep !== 'import_data') {
      return undefined;
    }
    let stopped = false;
    const tick = async () => {
      try {
        const next = await getImportDataProgress();
        if (!stopped) {
          setImportProgress(next);
        }
      } catch (_error) {
        // ignore temporary polling errors
      }
    };
    tick();
    const timerId = setInterval(() => {
      tick();
    }, 1000);
    return () => {
      stopped = true;
      clearInterval(timerId);
    };
  }, [flowStage, runningStep]);

  const completedCount = rows.filter((row) => row.state === '已完成').length;
  const progressPercent = definition.length > 0
    ? Math.round((completedCount / definition.length) * 100)
    : 0;
  const pausedStepDef = definition.find((step) => step.id === pausedStep);

  return (
    <>
      <Backdrop open={bootstrapping} sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Stack spacing={1.5} alignItems="center">
          <CircularProgress color="inherit" />
          <Typography variant="body2">正在加载安装状态...</Typography>
        </Stack>
      </Backdrop>
      <Container maxWidth="lg" sx={{ py: 5, visibility: bootstrapping ? 'hidden' : 'visible' }}>
      <Stack spacing={3}>
        <Box>
          <Typography variant="h4" fontWeight={700}>
            初始化向导
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 1 }}>
            系统未就绪时的初始化流程。该页面通过 BFF setup API 驱动步骤执行。
          </Typography>
        </Box>

        {flowStage !== 'input' && status?.isReady ? (
          <Alert severity="success">
            安装流程已完成。你现在可以进入主业务页面。
          </Alert>
        ) : (
          <Alert severity="warning">
            检测到必要配置缺失，业务页将继续重定向到 Setup。
          </Alert>
        )}

        <Card variant="outlined">
          <CardContent>
            <Stepper activeStep={activeStep < 0 ? definition.length : activeStep} sx={{ mb: 2 }}>
              {definition.map((step) => (
                <Step key={step.id} completed={rows.find((row) => row.stepId === step.id)?.state === '已完成'}>
                  <StepLabel>{step.name}</StepLabel>
                </Step>
              ))}
            </Stepper>
            <Typography variant="body2" color="text.secondary">
              总进度: {completedCount}/{definition.length} ({progressPercent}%)
            </Typography>
            <Box sx={{ mt: 1, height: 8, borderRadius: 1, bgcolor: 'grey.200', overflow: 'hidden' }}>
              <Box sx={{ width: `${progressPercent}%`, bgcolor: 'primary.main', height: '100%' }} />
            </Box>
          </CardContent>
        </Card>

        {flowStage === 'input' ? (
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                安装开始
              </Typography>
              <Typography color="text.secondary" sx={{ mb: 2 }}>
                点击开始后，系统会按 pipeline 顺序执行步骤；遇到需要交互的步骤会自动暂停并显示表单。
              </Typography>
              <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
                <Button variant="contained" onClick={handleStartSetup}>
                  开始安装
                </Button>
              </Stack>
            </CardContent>
          </Card>
        ) : null}

        {flowStage === 'interaction' ? (
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                需要用户输入：{pausedStepDef?.name || pausedStep}
              </Typography>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} useFlexGap flexWrap="wrap">
                {(pausedStepDef?.requiredUserInputs || []).map((field) => {
                  if (field.key === 'defaultPgsqlSchema' && formValues.dbType !== 'postgresql') return null;
                  if (!shouldShowUserspaceConflictPolicy(field)) return null;
                  if (field.type === 'select') {
                    return (
                      <TextField
                        key={field.key}
                        id={getFieldInputId(field)}
                        select
                        label={field.label}
                        value={formValues[field.key] ?? field.defaultValue ?? ''}
                        onChange={(e) => handleInputChange(field.key, e.target.value)}
                        sx={{ minWidth: 240, flex: 1 }}
                      >
                        {(field.options || []).map((opt) => (
                          <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                        ))}
                      </TextField>
                    );
                  }
                  return (
                    <Box key={field.key} sx={{ minWidth: 240, flex: 1 }}>
                      <TextField
                        id={getFieldInputId(field)}
                        label={field.label}
                        type={field.type === 'password' ? 'password' : 'text'}
                        value={getFieldDisplayValue(field)}
                        onChange={(e) => handleInputChange(field.key, e.target.value)}
                        onBlur={field.key === 'userspaceTargetPath' ? handleUserspacePathBlur : undefined}
                        placeholder={field.placeholder || ''}
                        helperText={
                          field.key === 'userspaceTargetPath'
                            ? (checkingUserspacePath ? '正在检查目标路径...' : (field.helperText || ''))
                            : (field.helperText || '')
                        }
                        disabled={field.editableByCheckbox ? !userspacePathEditable : false}
                        sx={{ width: '100%' }}
                      />
                      {field.editableByCheckbox ? (
                        <FormControlLabel
                          sx={{ mt: 0.5 }}
                          control={(
                            <Checkbox
                              checked={userspacePathEditable}
                              onChange={(e) => {
                                const nextChecked = e.target.checked;
                                setUserspacePathEditable(nextChecked);
                                if (!nextChecked) {
                                  setUserspacePathExists(false);
                                }
                              }}
                            />
                          )}
                          label={field.editableLabel || '允许修改该路径'}
                        />
                      ) : null}
                    </Box>
                  );
                })}
              </Stack>
              <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
                <Button variant="contained" onClick={() => handleSubmitInteractionStep({})}>
                  下一步
                </Button>
              </Stack>
            </CardContent>
          </Card>
        ) : null}

        <Dialog
          open={overwriteConfirmOpen}
          onClose={() => setOverwriteConfirmOpen(false)}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle>确认覆盖 userspace</DialogTitle>
          <DialogContent>
            <DialogContentText>
              你选择了“覆盖 userspace”。此操作会删除目标目录中的现有内容，并用初始化包重新解压，
              可能覆盖现有策略、标签和用户配置。确定继续吗？
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOverwriteConfirmOpen(false)} color="inherit">
              取消
            </Button>
            <Button
              color="error"
              variant="contained"
              onClick={() => {
                setOverwriteConfirmOpen(false);
                    handleSubmitInteractionStep({ confirmedOverwrite: true });
              }}
            >
              确认覆盖
            </Button>
          </DialogActions>
        </Dialog>

        <Dialog
          open={dbRiskConfirmOpen}
          onClose={() => setDbRiskConfirmOpen(false)}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle>确认数据库风险</DialogTitle>
          <DialogContent>
            <DialogContentText>
              系统检测到目标数据库
              {dbRiskContext.dbType || dbRiskContext.database
                ? `（${dbRiskContext.dbType || 'db'}:${dbRiskContext.database || '未命名'}）`
                : ''}已存在。
              继续执行后，初始化数据导入可能覆盖其中部分表数据。请确认你要继续覆盖初始化数据。
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDbRiskConfirmOpen(false)} color="inherit">
              返回检查
            </Button>
            <Button
              color="warning"
              variant="contained"
              onClick={() => {
                setDbRiskConfirmOpen(false);
                handleSubmitInteractionStep({ confirmedDbRisk: true });
              }}
            >
              我已确认，继续
            </Button>
          </DialogActions>
        </Dialog>

        {flowStage === 'executing' ? (
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" sx={{ mb: 1 }}>
                自动执行步骤
              </Typography>
              <Typography color="text.secondary" sx={{ mb: 2 }}>
                {progressText}
              </Typography>
              {runningStep === 'import_data' && importProgress.totalTables > 0 ? (
                <Alert severity="info" sx={{ mb: 2 }}>
                  导入进度：{importProgress.completedCount}/{importProgress.totalTables}
                  （{importProgress.percent}%）
                  {importProgress.currentTable ? `，当前表：${importProgress.currentTable}` : ''}
                </Alert>
              ) : null}
              <Box sx={{ height: 320 }}>
                <DataGrid
                  rows={rows}
                  columns={executingColumns}
                  disableRowSelectionOnClick
                  hideFooter
                />
              </Box>
            </CardContent>
          </Card>
        ) : null}

        {flowStage === 'success' ? (
          <Card variant="outlined">
            <CardContent>
              <Stack alignItems="center" spacing={1} sx={{ mb: 1 }}>
                <CheckCircleRoundedIcon
                  sx={{
                    fontSize: 72,
                    color: 'success.main',
                    animation: 'ySpinFast 0.3s ease',
                    '@keyframes ySpinFast': {
                      '0%': { transform: 'rotateY(0deg) scale(0.9)', opacity: 0.4 },
                      '100%': { transform: 'rotateY(360deg) scale(1)', opacity: 1 },
                    },
                  }}
                />
                <Typography variant="h6">成功</Typography>
              </Stack>
              <Typography color="text.secondary" sx={{ mt: 1, mb: 2 }}>
                安装流程已完成。你可以进入主业务页面。
              </Typography>
              <Stack direction="row" spacing={2}>
                <Button component={RouterLink} to="/workbench" variant="contained">
                  前往策略工作台
                </Button>
                <Button component={RouterLink} to="/settings" variant="outlined">
                  前往设置
                </Button>
                <Button color="warning" variant="outlined" onClick={handleRestartSetup}>
                  重新安装
                </Button>
              </Stack>
            </CardContent>
          </Card>
        ) : null}

        {flowStage === 'fail' ? (
          <Card variant="outlined">
            <CardContent>
              <Stack alignItems="center" spacing={1} sx={{ mb: 1 }}>
                <CancelRoundedIcon
                  sx={{
                    fontSize: 72,
                    color: 'error.main',
                    animation: 'ySpinFast 0.3s ease',
                    '@keyframes ySpinFast': {
                      '0%': { transform: 'rotateY(0deg) scale(0.9)', opacity: 0.5 },
                      '100%': { transform: 'rotateY(360deg) scale(1)', opacity: 1 },
                    },
                  }}
                />
                <Typography variant="h6">失败</Typography>
              </Stack>
              <Alert severity="error" sx={{ mt: 1, mb: 2 }}>
                {errorMessage}
              </Alert>
              {failedStep ? (
                <Alert severity="warning" sx={{ mb: 2 }}>
                  失败步骤: {definition.find((step) => step.id === failedStep)?.name || failedStep}
                </Alert>
              ) : null}
              <Box sx={{ height: 320, mb: 2 }}>
                <DataGrid
                  rows={rows}
                  columns={failColumns}
                  disableRowSelectionOnClick
                  hideFooter
                />
              </Box>
              <Stack direction="row" spacing={2}>
                <Button variant="contained" onClick={handleRetryFailedStep}>
                  重新开始安装
                </Button>
              </Stack>
            </CardContent>
          </Card>
        ) : null}
      </Stack>
      </Container>
    </>
  );
}

export default SetupPage;
