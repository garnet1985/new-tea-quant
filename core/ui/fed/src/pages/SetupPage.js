import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Container,
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
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import {
  getSetupDefinition,
  getSetupStatus,
  resetSetupStatus,
  retryFailedStep,
  startSetupWorkflow,
  STEP_STATUS,
  submitInteractiveStep,
} from '../mock/setupApi';

function SetupPage() {
  const navigate = useNavigate();
  const [definition, setDefinition] = useState([]);
  const [status, setStatus] = useState(null);
  const [flowStage, setFlowStage] = useState('input');
  const [runningStep, setRunningStep] = useState('');
  const [progressText, setProgressText] = useState('等待开始');
  const [errorMessage, setErrorMessage] = useState('');
  const [failedStep, setFailedStep] = useState('');
  const [pausedStep, setPausedStep] = useState('');
  const [formValues, setFormValues] = useState({});

  useEffect(() => {
    Promise.all([getSetupDefinition(), getSetupStatus()]).then(([defs, current]) => {
      setDefinition(defs);
      setStatus(current);
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
      errorMessage: state?.errorMessage || '',
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

  const consumePipelineResult = (result, defaultFailedStep = 'db_config') => {
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

  const handleStartSetup = async () => {
    if (!status || definition.length === 0) return;
    setFlowStage('executing');
    setErrorMessage('');
    setFailedStep('');
    setPausedStep('');
    setProgressText('准备执行安装步骤...');
    const result = await runningWithProgress((onProgress) => startSetupWorkflow(onProgress));
    consumePipelineResult(result, definition[0]?.id || 'db_connection');
  };

  const handleSubmitInteractionStep = async () => {
    if (!status || !pausedStep) return;
    setFlowStage('executing');
    setProgressText('提交输入并继续执行...');
    setErrorMessage('');
    setFailedStep('');
    const result = await runningWithProgress((onProgress) => submitInteractiveStep(pausedStep, formValues, onProgress));
    consumePipelineResult(result, pausedStep);
  };

  const handleRetryFailedStep = async () => {
    setFlowStage('executing');
    setProgressText('重试失败步骤并继续执行...');
    setErrorMessage('');
    const result = await runningWithProgress((onProgress) => retryFailedStep(onProgress));
    consumePipelineResult(result, failedStep || definition[0]?.id || 'db_connection');
  };

  const handleReset = async () => {
    const nextStatus = await resetSetupStatus();
    setStatus(nextStatus);
    setFlowStage('input');
    setProgressText('等待开始');
    setErrorMessage('');
    setRunningStep('');
    setFailedStep('');
    setPausedStep('');
  };

  const completedCount = rows.filter((row) => row.state === '已完成').length;
  const progressPercent = definition.length > 0
    ? Math.round((completedCount / definition.length) * 100)
    : 0;
  const pausedStepDef = definition.find((step) => step.id === pausedStep);

  return (
    <Container maxWidth="lg" sx={{ py: 5 }}>
      <Stack spacing={3}>
        <Box>
          <Typography variant="h4" fontWeight={700}>
            Setup Wizard
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 1 }}>
            系统未就绪时的初始化流程。此页为 mock 版本，用于验证路由守卫与交互框架。
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
                <Button variant="text" color="inherit" onClick={handleReset}>
                  重置 Mock 状态
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
                  if (field.type === 'select') {
                    return (
                      <TextField
                        key={field.key}
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
                    <TextField
                      key={field.key}
                      label={field.label}
                      type={field.type === 'password' ? 'password' : 'text'}
                      value={formValues[field.key] ?? field.defaultValue ?? ''}
                      onChange={(e) => handleInputChange(field.key, e.target.value)}
                      sx={{ minWidth: 240, flex: 1 }}
                    />
                  );
                })}
              </Stack>
              <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
                <Button variant="contained" onClick={handleSubmitInteractionStep}>
                  下一步
                </Button>
              </Stack>
            </CardContent>
          </Card>
        ) : null}

        {flowStage === 'executing' ? (
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" sx={{ mb: 1 }}>
                Step 2 - Execute Steps（自动执行）
              </Typography>
              <Typography color="text.secondary" sx={{ mb: 2 }}>
                {progressText}
              </Typography>
              <Box sx={{ height: 320 }}>
                <DataGrid
                  rows={rows}
                  columns={[
                    { field: 'order', headerName: '#', width: 80 },
                    { field: 'name', headerName: '步骤', flex: 1 },
                    {
                      field: 'state',
                      headerName: '状态',
                      width: 180,
                      renderCell: (params) => {
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
                            <Typography variant="body2">待完成</Typography>
                          </Stack>
                        );
                      },
                    },
                    { field: 'detail', headerName: '说明', flex: 1.6 },
                  ]}
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
                <Typography variant="h6">Success</Typography>
              </Stack>
              <Typography color="text.secondary" sx={{ mt: 1, mb: 2 }}>
                安装流程已完成。你可以进入主业务页面。
              </Typography>
              <Stack direction="row" spacing={2}>
                <Button component={RouterLink} to="/workbench" variant="contained" onClick={() => navigate('/workbench')}>
                  前往策略工作台
                </Button>
                <Button component={RouterLink} to="/settings" variant="outlined">
                  前往设置
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
                <Typography variant="h6">Fail</Typography>
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
                  columns={[
                    { field: 'order', headerName: '#', width: 80 },
                    { field: 'name', headerName: '步骤', flex: 1 },
                    {
                      field: 'state',
                      headerName: '状态',
                      width: 180,
                      renderCell: (params) => {
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
                              <RadioButtonUncheckedRoundedIcon color="warning" />
                              <Typography variant="body2">待输入</Typography>
                            </Stack>
                          );
                        }
                        return (
                          <Stack direction="row" spacing={1} alignItems="center">
                            <RadioButtonUncheckedRoundedIcon color="disabled" />
                            <Typography variant="body2">未开始</Typography>
                          </Stack>
                        );
                      },
                    },
                    { field: 'detail', headerName: '说明', flex: 1.6 },
                  ]}
                  disableRowSelectionOnClick
                  hideFooter
                />
              </Box>
              <Stack direction="row" spacing={2}>
                <Button variant="contained" onClick={handleRetryFailedStep}>
                  重试
                </Button>
              </Stack>
            </CardContent>
          </Card>
        ) : null}
      </Stack>
    </Container>
  );
}

export default SetupPage;
