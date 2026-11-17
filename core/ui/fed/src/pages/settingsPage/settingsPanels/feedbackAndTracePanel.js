import React, { useCallback, useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Heading,
  Loading,
  Message,
  Button,
  Section,
  Switch as UiSwitch,
} from 'ui';
import { formatDateTime } from '../../../service/format/formatDateTime';
import {
  fetchTraceSettings,
  saveTraceSettings,
} from '../../../api/settingsApi';
import { fetchFeedbackSettings, saveFeedbackSettings } from '../../../api/feedbackApi';
import { useAsyncAction } from 'service/useAsyncAction';

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

  if (loading) {
    return <Loading variant="inline" message="正在加载反馈与统计设置…" />;
  }

  return (
    <Section className="settings-feedback" gap="lg">
      <Section className="settings-feedback__prompts" gap="md">
        <Heading level="h3" gap="none">反馈</Heading>
        <p className="ntq-muted">
          任务成功后会弹出简短反馈，每个半天（0 点到 12 点、12 点到 24 点）最多一次。关闭询问只在本页。一旦你主动发送，不会再要求任何本地授权。更长的问题请走官网联系页。
        </p>
        {loadError ? <Message status="error">{loadError}</Message> : null}
        {feedbackSave.error ? <Message status="error">{feedbackSave.error}</Message> : null}
        {feedbackSaveOk ? <Message status="success">{feedbackSaveOk}</Message> : null}
        <UiSwitch
          label={promptsDisabled ? '已关闭应用内反馈询问' : '允许应用内反馈询问'}
          checked={!promptsDisabled}
          onChange={handleFeedbackToggle}
          disabled={busy}
          inputProps={{ 'aria-label': '开启应用内反馈询问' }}
        />
        {contactUrl ? (
          <div className="settings-feedback__actions">
            <Button
              variant="glass"
              href={contactUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              打开官网联系页
            </Button>
          </div>
        ) : null}
      </Section>

      <Section className="settings-feedback__trace" gap="md">
        <Heading level="h3" gap="none">使用统计</Heading>
        <p className="ntq-muted">
          可选的匿名使用数据，用于改进 New Tea Quant。不包含策略代码、回测结果、账户或个人身份信息。详见
          {' '}
          <RouterLink className="ntq-link" to="/what-we-will-track">
            我们收集哪些信息
          </RouterLink>
          。
        </p>
        {traceSave.error ? <Message status="error">{traceSave.error}</Message> : null}
        {traceSaveOk ? <Message status="success">{traceSaveOk}</Message> : null}
        {!traceDecided ? (
          <Message status="info">
            尚未选择偏好。打开开关即表示同意；关闭表示不同意。之后可随时在此更改。
          </Message>
        ) : null}
        <UiSwitch
          label={traceEnabled ? '已开启匿名使用统计' : '未开启匿名使用统计'}
          checked={traceEnabled}
          onChange={handleTraceToggle}
          disabled={busy}
          inputProps={{ 'aria-label': '开启匿名使用统计' }}
        />
        {traceDecided && traceDecidedAt ? (
          <p className="ntq-muted settings-feedback__meta">
            最近决定时间：
            {traceDecidedAt}
          </p>
        ) : null}
      </Section>

      <Section className="settings-feedback__form-actions" gap="md">
        <div className="settings-feedback__actions">
          <Button variant="ghost" onClick={load} disabled={busy}>
            重新读取
          </Button>
        </div>
      </Section>
    </Section>
  );
}
