import React, { useCallback, useEffect, useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import {
  Dialog,
  Heading,
  Loading,
  Message,
  Button,
  ProgressBar,
  Section,
  Tag,
} from 'ui';
import {
  getImportDataPlan,
  getImportDataProgress,
  getMlExtrasStatus,
  importDemoData,
  installMlExtras,
  resetSetupStatus,
} from '../../../api/setupApi';
import { useFakeProgress } from 'service/progress/useFakeProgress';
import { subscribePipelineSnapshot } from 'service/jobPipelineBus';

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
  const [importSubmitting, setImportSubmitting] = useState(false);
  const [importRunning, setImportRunning] = useState(false);
  const [importError, setImportError] = useState('');
  const [importOk, setImportOk] = useState('');
  const [importProgress, setImportProgress] = useState(null);
  const [importPlan, setImportPlan] = useState(null);
  const fakePercent = useFakeProgress(installing, 8);
  const importing = importSubmitting || importRunning;

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

  const loadImportPlan = useCallback(() => {
    return getImportDataPlan()
      .then((next) => {
        setImportPlan(next);
      })
      .catch(() => {
        setImportPlan(null);
      });
  }, []);

  useEffect(() => {
    loadMlStatus();
    loadImportPlan();
  }, [loadMlStatus, loadImportPlan]);

  useEffect(() => {
    let stopped = false;
    let pipelineBusy = false;
    let progressRunning = false;
    let wasBusy = false;

    const isImportJob = (row) => String(row?.kind || '') === 'import_data'
      && ['running', 'pending', 'stale'].includes(String(row?.status || '').toLowerCase());

    const syncBusy = () => {
      const busy = pipelineBusy || progressRunning;
      setImportRunning(busy);
      if (wasBusy && !busy) {
        loadImportPlan();
      }
      wasBusy = busy;
    };

    const unsub = subscribePipelineSnapshot((snap) => {
      if (stopped) return;
      const jobs = Array.isArray(snap?.jobs) ? snap.jobs : [];
      pipelineBusy = Boolean(
        isImportJob(snap?.job)
        || jobs.some(isImportJob),
      );
      syncBusy();
    });

    const tick = () => {
      getImportDataProgress()
        .then((next) => {
          if (stopped) return;
          setImportProgress(next);
          progressRunning = Boolean(next?.running);
          syncBusy();
        })
        .catch(() => {});
    };
    tick();
    const timerId = setInterval(tick, 800);
    return () => {
      stopped = true;
      clearInterval(timerId);
      unsub();
    };
  }, [loadImportPlan]);

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
    setImportSubmitting(true);
    setImportError('');
    setImportOk('');
    setImportProgress(null);
    try {
      const result = await importDemoData();
      setImportOpen(false);
      // 一次任务内下载（若需）并导入，无需再点一次。
      setImportOk(
        result.message
          || (result.imported
            ? '数据已导入。'
            : '导入任务已提交（缺包时先下载再导入）。'),
      );
      if (result.running || result.queued || result.imported === false) {
        setImportRunning(true);
      }
      loadImportPlan();
    } catch (err) {
      setImportError(err?.message || '数据导入失败，请稍后重试。');
    } finally {
      setImportSubmitting(false);
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
  const importProgressText = !importProgress?.running
    ? (importSubmitting ? '正在提交导入任务…' : '正在导入数据…')
    : (importProgress.phase === 'downloading' || importProgress.phase === 'preparing')
      ? (importProgress.statusText
        || (importProgress.phase === 'downloading' ? '数据下载中…' : '准备导入…'))
      : importProgress.totalTables
        ? `正在导入 ${importProgress.completedCount}/${importProgress.totalTables}${
          importProgress.currentTable ? `：${importProgress.currentTable}` : ''
        }`
        : '正在导入数据…';
  const membershipConfigured = Boolean(importPlan?.membershipConfigured);
  const packLabel = importPlan?.packLabel || '约 300 只股票 × 三年（公开演示包）';
  const localHint = importPlan?.localHint || '';
  const membershipWarning = importPlan?.warning || '';
  const confirmTitle = importPlan?.confirmTitle || '导入数据？';
  const confirmBody = importPlan?.confirmBody
    || '数据包中的表会被清空后重写，可能覆盖已有行情。';
  const confirmActionLabel = importPlan?.confirmActionLabel || '开始导入';

  return (
    <Section className="settings-system" gap="lg">
      <Section className="settings-system__reinstall" gap="md">
        <Heading level="h3" gap="none">安装与修复</Heading>
        <p className="ntq-muted">
          如果您的程序运行出现了任何严重问题，您可以尝试点击下面的按钮进行安装与修复。
        </p>
        {reinstallError ? <Message status="error">{reinstallError}</Message> : null}
        <div className="settings-system__actions">
          <Button
            variant="danger"
            disabled={importBusy}
            onClick={() => {
              setReinstallError('');
              setReinstallOpen(true);
            }}
          >
            安装与修复
          </Button>
        </div>
        <Dialog
          open={reinstallOpen}
          onClose={() => !reinstalling && setReinstallOpen(false)}
          title="确认重新安装？"
          size="md"
          actions={(
            <>
              <Button
                variant="ghost"
                onClick={() => setReinstallOpen(false)}
                disabled={reinstalling}
              >
                取消
              </Button>
              <Button
                variant="danger"
                onClick={handleConfirmReinstall}
                disabled={reinstalling}
              >
                {reinstalling ? '正在进入安装…' : '确认，重新安装'}
              </Button>
            </>
          )}
        >
          <div className="settings-system__dialog-body">
            <p className="ntq-muted">重新安装即将执行。请您先了解这些可能的风险：</p>
            <ul className="settings-system__risk-list ntq-muted">
              <li>如果您在重新安装过程中选择覆盖用户空间，您的所有用户数据包括策略会丢失，如果需要，请您事先备份。</li>
              <li>如果您使用不同的数据库，需要重新导入数据。</li>
              <li>如果您使用相同数据库重新导入数据，会覆盖现有的数据。</li>
            </ul>
          </div>
        </Dialog>
      </Section>

      <Section className="settings-system__import" gap="md">
        <Heading level="h3" gap="none">导入数据</Heading>
        <p className="ntq-muted">
          根据不同登录信息，可能有以下不同情况：
          <ul>
            <li>如果您没有注册会员，您仍然可以导入300只股票的3年的演示数据。</li>
            <li>如果您是会员，您可以导入全市场接近6000只股票的3年数据。</li>
            <li>如果您使用自己的外部数据，您可以忽略任何的数据导入。</li>
          </ul>
        </p>
        {importPlan && !membershipConfigured ? (
          <Message status="info">
            如果您是会员，需要先前往会员设置里从官网粘贴您的会员凭证，再回来导入全市场数据。
          </Message>
        ) : null}
        {importPlan && membershipWarning ? (
          <Message status="warning">
            {membershipWarning}
            {' '}
            <RouterLink className="ntq-link" to="/settings/membership">
              前往会员设置
            </RouterLink>
          </Message>
        ) : null}
        {importPlan ? (
          <div className="settings-system__status">
            <p className="ntq-muted">
              当前将可用的导入数据包为：
              {packLabel}
            </p>
            <Tag
              status={membershipConfigured ? 'success' : 'neutral'}
              variant={membershipConfigured ? 'solid' : 'outline'}
            >
              {membershipConfigured ? '会员凭证已装载' : '会员凭证未装载'}
            </Tag>
          </div>
        ) : null}
        {localHint ? <p className="ntq-muted">{localHint}</p> : null}
        {importError ? <Message status="error">{importError}</Message> : null}
        {importOk ? <Message status="success">{importOk}</Message> : null}
        {importing ? <p className="ntq-muted">{importProgressText}</p> : null}
        <div className="settings-system__actions">
          <Button
            variant="primary"
            disabled={importBusy}
            onClick={() => {
              setImportError('');
              setImportOk('');
              loadImportPlan().finally(() => setImportOpen(true));
            }}
          >
            {importRunning ? '正在导入…' : '导入数据'}
          </Button>
        </div>
        <Dialog
          open={importOpen}
          onClose={() => !importing && setImportOpen(false)}
          title={confirmTitle}
          size="md"
          actions={(
            <>
              <Button
                variant="ghost"
                onClick={() => setImportOpen(false)}
                disabled={importing}
              >
                取消
              </Button>
              <Button
                variant="primary"
                onClick={handleConfirmImport}
                disabled={importing}
              >
                {importing ? '正在导入…' : confirmActionLabel}
              </Button>
            </>
          )}
        >
          <div className="settings-system__dialog-body">
            <p className="ntq-muted">{confirmBody}</p>
            {localHint ? <p className="ntq-muted">{localHint}</p> : null}
            {!membershipConfigured ? (
              <Message status="warning">
                若您是会员，请先取消并到
                {' '}
                <RouterLink className="ntq-link" to="/settings/membership">
                  设置 → 会员
                </RouterLink>
                {' '}
                装载凭证，再回来导入全市场数据。
              </Message>
            ) : null}
            {importError ? <Message status="error">{importError}</Message> : null}
            {importing ? <p className="ntq-muted">{importProgressText}</p> : null}
          </div>
        </Dialog>
      </Section>

      <Section className="settings-system__ml" gap="md">
        <Heading level="h3" gap="none">机器学习组件</Heading>
        <p className="ntq-muted">
          分析库的统计 / ML 原语会用到这些依赖（XGBoost / SHAP）。跳过安装向导后可在这里补装，可能需要几分钟。
        </p>
        {mlLoadError ? <Message status="error">{mlLoadError}</Message> : null}
        {mlOk ? <Message status="success">{mlOk}</Message> : null}
        {mlStatus == null && !mlLoadError ? (
          <Loading variant="inline" message="正在检查机器学习依赖…" />
        ) : (
          <div className="settings-system__status">
            <Tag
              status={mlInstalled ? 'success' : 'neutral'}
              variant={mlInstalled ? 'solid' : 'outline'}
            >
              {mlInstalled ? '已安装' : '尚未安装'}
            </Tag>
            <p className="ntq-muted">
              {mlInstalled
                ? `${mlStatus?.shap ? '含 SHAP' : 'XGBoost'}。`
                : '分析库的机器学习阶段在未安装时会跳过。'}
            </p>
          </div>
        )}
        {installing ? (
          <ProgressBar
            value={fakePercent}
            size="md"
            label="正在安装…"
            showPercent
          />
        ) : null}
        <div className="settings-system__actions">
          <Button
            variant="primary"
            disabled={mlInstalled || installing}
            onClick={handleInstallMl}
          >
            {mlInstalled ? '已安装' : '安装机器学习依赖'}
          </Button>
        </div>
      </Section>
    </Section>
  );
}
