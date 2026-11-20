import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Button, Checkbox, DataGrid, Icon, Message, Select, TextField, Loading } from 'ui';
import { Link as RouterLink, useLocation, useNavigate } from 'react-router-dom';
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
} from '../../api/setupApi';
import {
  applyDbTypeDefaults,
  DEFAULT_STEP_ID,
  demoPackageHintFromStatus,
  EMPTY_IMPORT_PROGRESS,
  getFieldDisplayValue,
  getFieldInputId,
  isChoicePauseStep,
  setupStatusSignature,
  shouldShowDbConnectionField,
  shouldShowUserspaceConflictPolicy,
  STEP_STATUS,
  validateDbConnectionSubmit,
} from './setup.helpers';
import SetupChoiceCard from './setupChoiceCard';
import SetupDialogs from './setupDialogs';
import SetupExecutionPanel from './setupExecutionPanel';
import SetupProgressBar from './setupProgressBar';
import SetupStepper from './setupStepper';
import logClientError from '../../service/logClientError';
import './setupPage.scss';


/** 安装向导表单：统一走 ui TextField / Select */
const SETUP_FIELD_COMMON = {
  maxWidth: false,
  fullWidth: true,
};

function SetupPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [reinstallAutoStart] = useState(() => Boolean(location.state?.autoStart));
  const autoStartedRef = useRef(false);
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
  const [bootstrapError, setBootstrapError] = useState('');
  const [userspacePathExists, setUserspacePathExists] = useState(false);
  const [checkingUserspacePath, setCheckingUserspacePath] = useState(false);
  const [userspacePrecheckError, setUserspacePrecheckError] = useState('');
  const [importProgress, setImportProgress] = useState(EMPTY_IMPORT_PROGRESS);
  const [pollWarning, setPollWarning] = useState('');
  const [importPollWarning, setImportPollWarning] = useState('');
  const [restartError, setRestartError] = useState('');

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

  const loadBootstrap = useCallback(() => {
    setBootstrapping(true);
    setBootstrapError('');
    Promise.all([getSetupDefinition(), getSetupStatus()])
      .then(([defs, current]) => {
        if (reinstallAutoStart) {
          return resetSetupStatus()
            .then((fresh) => {
              setDefinition(defs);
              setStatus(fresh);
              restoreFlowStage(defs, fresh);
            });
        }

        setDefinition(defs);
        setStatus(current);
        if (current?.isReady) {
          navigate('/welcome', { replace: true });
          return undefined;
        }
        restoreFlowStage(defs, current);
        return undefined;
      })
      .catch((err) => {
        setBootstrapError(err?.message || '加载安装向导失败，请检查网络后重试。');
        setDefinition([]);
        setStatus(null);
      })
      .finally(() => {
        setBootstrapping(false);
      });
  }, [navigate, reinstallAutoStart]);

  useEffect(() => {
    loadBootstrap();
  }, [loadBootstrap]);

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

  const runningWithProgress = (runner) => {
    setPollWarning('');
    return runner(({ stepId, status: progressStatus, snapshot, pollWarning: warning }) => {
      if (warning) {
        setPollWarning(warning);
      }
      if (progressStatus === 'running' && stepId) {
        setRunningStep(stepId);
        const label = definition.find((step) => step.id === stepId)?.name || stepId;
        setProgressText(`正在执行: ${label}`);
      }
      if (snapshot) {
        setStatus((prev) => (
          setupStatusSignature(prev) === setupStatusSignature(snapshot) ? prev : snapshot
        ));
      }
    });
  };

  const consumePipelineResult = (result, defaultFailedStep = DEFAULT_STEP_ID) => {
    setRunningStep('');
    if (result.ok) {
      setStatus(result.status);
      setFlowStage('success');
      setProgressText('安装完成');
      setFailedStep('');
      setPausedStep('');
      navigate('/welcome', { replace: true });
      return;
    }
    if (result.kind === 'paused') {
      setStatus(result.status);
      setFlowStage('interaction');
      setPausedStep(result.pausedStepId || defaultFailedStep);
      const pausedId = result.pausedStepId || defaultFailedStep;
      const initialValues = result.status?.inputsByStep?.[pausedId] || {};
      let nextForm = { ...initialValues };
      if (pausedId === 'db_connection') {
        const dbType = nextForm.dbType || 'duckdb';
        nextForm = applyDbTypeDefaults({ ...nextForm, dbType }, 'dbType', dbType);
      }
      setFormValues(nextForm);
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
    const rowClass = 'setup-step-state';
    if (runningStep && params.row.id === runningStep) {
      return (
        <div className={rowClass}>
          <Icon name="refresh" size="md" spin />
          <span>执行中...</span>
        </div>
      );
    }
    if (params.value === '已完成') {
      return (
        <div className={rowClass}>
          <Icon name="success" size="md" tone="success" />
          <span>已完成</span>
        </div>
      );
    }
    if (params.value === '失败') {
      return (
        <div className={rowClass}>
          <Icon name="cancel" size="md" tone="error" />
          <span>失败</span>
        </div>
      );
    }
    if (params.value === '待输入') {
      return (
        <div className={rowClass}>
          <Icon name="radioUnchecked" size="md" tone="warning" />
          <span>待输入</span>
        </div>
      );
    }
    return (
      <div className={rowClass}>
        <Icon name="radioUnchecked" size="md" tone="disabled" />
        <span>{pendingLabel}</span>
      </div>
    );
  }, [runningStep]);

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
    const next = applyDbTypeDefaults(formValues, key, value);
    setFormValues(next);
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
    setUserspacePrecheckError('');
    try {
      const result = await precheckUserspacePath({ userspaceTargetPath: value });
      setUserspacePathExists(Boolean(result.pathExists));
      if (!result.pathExists) {
        setFormValues((prev) => ({ ...prev, userspaceConflictPolicy: 'skip' }));
      }
    } catch (error) {
      logClientError('setup.userspacePrecheck', error);
      setUserspacePathExists(false);
      setUserspacePrecheckError('路径检查失败，请检查网络后重试。');
    } finally {
      setCheckingUserspacePath(false);
    }
  };

  const handleStartSetup = async () => {
    if (!status || definition.length === 0) {
      setErrorMessage(
        bootstrapError || '安装步骤未加载，请点击下方「重新加载」或刷新页面后重试。',
      );
      return;
    }
    setFlowStage('executing');
    setErrorMessage('');
    setFailedStep('');
    setPausedStep('');
    setImportProgress(EMPTY_IMPORT_PROGRESS);
    setProgressText('准备执行安装步骤...');
    try {
      const result = await runningWithProgress((onProgress) => startSetupWorkflow(onProgress));
      consumePipelineResult(result, definition[0]?.id || DEFAULT_STEP_ID);
    } catch (err) {
      setRunningStep('');
      setFlowStage('fail');
      setFailedStep(definition[0]?.id || DEFAULT_STEP_ID);
      setErrorMessage(err?.message || '安装请求失败，请检查网络后重试。');
    }
  };

  useEffect(() => {
    if (!reinstallAutoStart || bootstrapping || autoStartedRef.current) return undefined;
    if (bootstrapError || flowStage !== 'input' || !status || definition.length === 0) return undefined;
    autoStartedRef.current = true;
    handleStartSetup();
    return undefined;
    // handleStartSetup 每次渲染都会新建；只在重置后的「开始安装」入口自动开跑一次。
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reinstallAutoStart, bootstrapping, bootstrapError, flowStage, status, definition.length]);

  const handleSubmitInteractionStep = async (options = {}) => {
    const { confirmedOverwrite = false, confirmedDbRisk = false, skip } = options;
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
    if (typeof skip === 'boolean') {
      submitValues.skip = skip;
    }
    if (pausedStep === 'db_connection') {
      const validationError = validateDbConnectionSubmit(submitValues);
      if (validationError) {
        setErrorMessage(validationError);
        return;
      }
      if (!confirmedDbRisk) {
        let dbCheck;
        try {
          dbCheck = await precheckDbConnection(submitValues);
        } catch (err) {
          setErrorMessage(err?.message || '数据库连接预检失败，请检查网络后重试。');
          return;
        }
        if (dbCheck.dbExists) {
          setDbRiskContext({
            dbType: dbCheck.dbType || '',
            database: dbCheck.database || '',
            isDuckdb: Boolean(dbCheck.isDuckdb) || dbCheck.dbType === 'duckdb',
          });
          setDbRiskConfirmOpen(true);
          return;
        }
      }
    }
    setFlowStage('executing');
    setProgressText('提交输入并继续执行...');
    setErrorMessage('');
    setFailedStep('');
    try {
      const result = await runningWithProgress(
        (onProgress) => submitInteractiveStep(pausedStep, submitValues, onProgress),
      );
      consumePipelineResult(result, pausedStep);
    } catch (err) {
      setRunningStep('');
      setFlowStage('fail');
      setFailedStep(pausedStep);
      setErrorMessage(err?.message || '提交失败，请检查网络后重试。');
    }
  };

  const handleRetryFailedStep = async () => {
    setFlowStage('executing');
    setProgressText('重试失败步骤并继续执行...');
    setErrorMessage('');
    const stepId = failedStep || definition[0]?.id || DEFAULT_STEP_ID;
    try {
      const result = await runningWithProgress((onProgress) => retryFailedStep(onProgress));
      consumePipelineResult(result, stepId);
    } catch (err) {
      setRunningStep('');
      setFlowStage('fail');
      setFailedStep(stepId);
      setErrorMessage(err?.message || '重试失败，请检查网络后重试。');
    }
  };

  const handleRestartSetup = async () => {
    setRestartError('');
    try {
      const nextStatus = await resetSetupStatus();
      setStatus(nextStatus);
      setRunningStep('');
      setErrorMessage('');
      setFailedStep('');
      setPausedStep('');
      setFormValues({});
      setUserspacePathEditable(false);
      setUserspacePathExists(false);
      setImportProgress(EMPTY_IMPORT_PROGRESS);
      setFlowStage('executing');
      setProgressText('准备执行安装步骤...');
      const result = await runningWithProgress((onProgress) => startSetupWorkflow(onProgress));
      consumePipelineResult(result, definition[0]?.id || DEFAULT_STEP_ID);
    } catch (err) {
      setRestartError(err?.message || '重置安装状态失败，请检查网络后重试。');
      setFlowStage('input');
    }
  };

  useEffect(() => {
    if (flowStage !== 'executing' || runningStep !== 'import_data') {
      return undefined;
    }

    setImportProgress(EMPTY_IMPORT_PROGRESS);
    let stopped = false;
    let failCount = 0;
    const tick = async () => {
      try {
        const next = await getImportDataProgress();
        failCount = 0;
        if (!stopped) {
          // 未开始跑时忽略残留的已完成快照。
          if (!next.running && next.totalTables > 0) {
            setImportProgress(EMPTY_IMPORT_PROGRESS);
          } else {
            setImportProgress(next);
          }
          setImportPollWarning('');
        }
      } catch (error) {
        logClientError('setup.importProgressPoll', error);
        failCount += 1;
        if (!stopped && failCount >= 3) {
          setImportPollWarning('导入进度暂时无法更新，安装可能仍在进行…');
        }
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
  const completedIds = useMemo(
    () => rows.filter((row) => row.state === '已完成').map((row) => row.stepId),
    [rows],
  );
  const runningProgressId = flowStage === 'executing'
    ? (runningStep || rows.find((row) => row.state !== '已完成')?.stepId || '')
    : '';
  const pausedStepDef = definition.find((step) => step.id === pausedStep);
  const isChoicePause = isChoicePauseStep(pausedStep);

  return (
    <>
      {bootstrapping ? (
        <div className="setup-page__backdrop">
          <Loading variant="inline" message="正在加载安装状态…" />
        </div>
      ) : null}
      <div
        className="setup-page__container"
        style={bootstrapping ? { visibility: 'hidden' } : undefined}
      >
        <div className="setup-page">
          <div className="setup-page__stack">
          {flowStage !== 'input' && status?.isReady ? (
            <Message status="success">
              安装流程已完成。你可以进入欢迎页开始使用。
            </Message>
          ) : (
            <Message status="warning">
              系统检测到您缺少必要运行配置，将在安装页面重新安装或者修复。
            </Message>
          )}

          <section className="setup-card">
            <div className="setup-card__content">
              <SetupStepper
                definition={definition}
                completedIds={completedIds}
                activeStep={activeStep}
              />
              <SetupProgressBar
                definition={definition}
                completedIds={completedIds}
                runningStepId={runningProgressId}
                flowStage={flowStage}
                importProgress={importProgress}
                completedCount={completedCount}
              />
            </div>
          </section>

          {flowStage === 'input' ? (
            <section className="setup-card">
              <div className="setup-card__content">
                <h3 className="setup-typo-title">安装开始</h3>
                <p className="ntq-muted setup-page__lead">
                  点击开始后，系统会按顺序完成必要配置。过程中你可以选择是否导入演示数据、是否安装机器学习插件；跳过的步骤会记为已完成，之后也可在设置里补做。
                </p>
                {bootstrapError ? (
                  <>
                    <Message status="error">{bootstrapError}</Message>
                    <Button variant="ghost" className="setup-page__reload" onClick={loadBootstrap}>
                      重新加载
                    </Button>
                  </>
                ) : null}
                {errorMessage && !bootstrapError ? (
                  <Message status="error">{errorMessage}</Message>
                ) : null}
                <div className="setup-page__actions">
                  <Button variant="primary" onClick={handleStartSetup} disabled={Boolean(bootstrapError)}>
                    开始安装
                  </Button>
                </div>
              </div>
            </section>
          ) : null}

          {flowStage === 'interaction' && isChoicePause ? (
            <SetupChoiceCard
              stepId={pausedStep}
              errorMessage={errorMessage}
              packageHint={
                pausedStep === 'import_data'
                  ? demoPackageHintFromStatus(status)
                  : ''
              }
              onConfirm={() => handleSubmitInteractionStep({ skip: false })}
              onSkip={() => handleSubmitInteractionStep({ skip: true })}
            />
          ) : null}

          {flowStage === 'interaction' && !isChoicePause ? (
            <section className="setup-card">
              <div className="setup-card__content">
                <h3 className="setup-typo-title">
                  请完成：{pausedStepDef?.name || pausedStep}
                </h3>
                {pausedStepDef?.description ? (
                  <p className="ntq-muted setup-page__lead">
                    {pausedStepDef.description}
                  </p>
                ) : null}
                {errorMessage ? (
                  <Message status="error">{errorMessage}</Message>
                ) : null}
                <form
                  className="setup-interaction-form"
                  noValidate
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleSubmitInteractionStep({});
                  }}
                >
                <div className="setup-interaction-form__fields">
                  {(pausedStepDef?.requiredUserInputs || []).map((field) => {
                    if (field.key === 'skip' || field.type === 'boolean') return null;
                    const dbType = formValues.dbType || 'duckdb';
                    if (!shouldShowDbConnectionField(field.key, dbType)) return null;
                    if (!shouldShowUserspaceConflictPolicy(field, userspacePathEditable, userspacePathExists)) return null;
                    if (field.type === 'select') {
                      const selectRequired = Boolean(field.required);
                      const selectValue = formValues[field.key]
                        ?? field.defaultValue
                        ?? (selectRequired ? field.options?.[0]?.value : '')
                        ?? '';
                      return (
                        <Select
                          key={field.key}
                          id={getFieldInputId(pausedStep, field)}
                          label={field.label}
                          value={selectValue}
                          onChange={(e) => handleInputChange(field.key, e.target.value)}
                          options={field.options || []}
                          required={selectRequired}
                          displayEmpty={!selectRequired}
                          className="setup-interaction-form__field"
                          {...SETUP_FIELD_COMMON}
                        />
                      );
                    }
                    return (
                      <div key={field.key} className="setup-interaction-form__field">
                        <TextField
                          id={getFieldInputId(pausedStep, field)}
                          label={field.label}
                          type={field.type === 'password' ? 'password' : 'text'}
                          value={getFieldDisplayValue(formValues, field)}
                          onChange={(e) => handleInputChange(field.key, e.target.value)}
                          onBlur={field.key === 'userspaceTargetPath' ? handleUserspacePathBlur : undefined}
                          autoComplete={
                            field.type === 'password'
                              ? 'new-password'
                              : (field.key === 'user' ? 'username' : undefined)
                          }
                          hint={
                            field.key === 'userspaceTargetPath'
                              ? (
                                checkingUserspacePath
                                  ? '正在检查目标路径...'
                                  : (userspacePrecheckError || field.helperText || '')
                              )
                              : (field.helperText || '')
                          }
                          disabled={field.editableByCheckbox ? !userspacePathEditable : false}
                          {...SETUP_FIELD_COMMON}
                        />
                        {field.editableByCheckbox ? (
                          <Checkbox
                            className="setup-interaction-form__editable"
                            checked={userspacePathEditable}
                            onChange={(e) => {
                              const nextChecked = e.target.checked;
                              setUserspacePathEditable(nextChecked);
                              if (!nextChecked) {
                                setUserspacePathExists(false);
                              }
                            }}
                            label={field.editableLabel || '允许修改该路径'}
                          />
                        ) : null}
                      </div>
                    );
                  })}
                </div>
                <div className="setup-page__actions">
                  <Button type="submit" variant="primary">
                    下一步
                  </Button>
                </div>
                </form>
              </div>
            </section>
          ) : null}

          <SetupDialogs
            overwriteConfirmOpen={overwriteConfirmOpen}
            setOverwriteConfirmOpen={setOverwriteConfirmOpen}
            dbRiskConfirmOpen={dbRiskConfirmOpen}
            setDbRiskConfirmOpen={setDbRiskConfirmOpen}
            dbRiskContext={dbRiskContext}
            onConfirmOverwrite={() => handleSubmitInteractionStep({ confirmedOverwrite: true })}
            onConfirmDbRisk={() => handleSubmitInteractionStep({ confirmedDbRisk: true })}
          />

          <SetupExecutionPanel
            flowStage={flowStage}
            progressText={progressText}
            runningStep={runningStep}
            importProgress={importProgress}
            pollWarning={pollWarning || importPollWarning}
            rows={rows}
          />

          {flowStage === 'success' ? (
            <section className="setup-card">
                <div className="setup-card__content">
                  <div className="setup-page__result-head">
                    <div className="setup-page__result-icon">
                      <Icon name="success" size="xxl" tone="success" />
                    </div>
                    <h3 className="setup-typo-title">安装完成</h3>
                  </div>
                  <p className="ntq-muted setup-page__lead">
                    环境已就绪。可以进入欢迎页开始使用，或前往设置继续调整。
                  </p>
                  {restartError ? (
                    <Message status="error">{restartError}</Message>
                  ) : null}
                  <div className="setup-page__actions">
                    <Button
                      component={RouterLink}
                      to="/welcome"
                      variant="primary"
                    >
                      进入欢迎页
                    </Button>
                    <Button component={RouterLink} to="/settings" variant="glass">
                      前往设置
                    </Button>
                    <Button variant="attention" onClick={handleRestartSetup}>
                      重新安装
                    </Button>
                  </div>
                </div>
              </section>
          ) : null}

          {flowStage === 'fail' ? (
            <section className="setup-card">
              <div className="setup-card__content">
                <div className="setup-page__result-head">
                  <div className="setup-page__result-icon">
                    <Icon name="cancel" size="xxl" tone="error" />
                  </div>
                  <h3 className="setup-typo-title">失败</h3>
                </div>
                <Message status="error">
                  {errorMessage}
                </Message>
                {failedStep ? (
                  <Message status="warning">
                    失败步骤: {definition.find((step) => step.id === failedStep)?.name || failedStep}
                  </Message>
                ) : null}
                <div className="setup-page__fail-grid">
                  <DataGrid
                    rows={rows}
                    columns={failColumns}
                    hideFooter
                  />
                </div>
                <div className="setup-page__actions">
                  <Button variant="primary" onClick={handleRetryFailedStep}>
                    重新开始安装
                  </Button>
                </div>
              </div>
            </section>
          ) : null}
          </div>
        </div>
      </div>
    </>
  );
}

export default SetupPage;
