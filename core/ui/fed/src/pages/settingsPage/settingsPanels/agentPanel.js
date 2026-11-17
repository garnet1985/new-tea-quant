import React, { useCallback, useEffect, useState } from 'react';
import {
  Heading,
  Loading,
  Message,
  Button,
  Section,
  Select as UiSelect,
  TextArea as UiTextArea,
  TextField as UiTextField,
} from 'ui';
import {
  fetchMembershipSettings,
} from '../../../api/settingsApi';
import { listAiProviders } from '../../../api/aiApi';
import {
  clearAgentSession,
  fetchAgentSettings,
  saveAgentSettings,
} from '../../../api/agentApi';
import { persistDockSelectedId } from '../../../containers/assistantChatDock/dockChatStore';

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

  if (loading) {
    return <Loading variant="inline" message="正在加载 Agent 设置…" />;
  }

  const selectValue = providerOptions.some((item) => item.id === defaultProviderId)
    ? defaultProviderId
    : (providerOptions[0]?.id || 'ntq');

  const selectOptions = providerOptions.map((item) => ({
    value: item.id,
    label: item.label,
  }));

  return (
    <Section className="settings-agent" gap="lg">
      <Section className="settings-agent__channel" gap="md">
        <Heading level="h3" gap="none">默认 AI 通道</Heading>
        <p className="ntq-muted">
          管理助理的默认通道、跨会话偏好与补充说明。密钥仍在「AI 配置」；会员凭证在「会员」。
          打开聊天框且尚未手动切换时使用本通道；可随时在聊天框里改选。
        </p>
        {loadError ? <Message status="error">{loadError}</Message> : null}
        {saveError ? <Message status="error">{saveError}</Message> : null}
        {saveOk ? <Message status="success">{saveOk}</Message> : null}
        {clearError ? <Message status="error">{clearError}</Message> : null}
        {clearOk ? <Message status="success">{clearOk}</Message> : null}
        <UiSelect
          label="默认通道"
          value={selectValue}
          onChange={(e) => setDefaultProviderId(e.target.value)}
          options={selectOptions}
        />
      </Section>

      <Section className="settings-agent__prefs" gap="md">
        <Heading level="h3" gap="none">跨会话偏好</Heading>
        <p className="ntq-muted">
          每条会长期带入对话（最多
          {preferenceMaxRules}
          条，每条
          {preferenceMaxChars}
          字）。清空会话不会删这些。
        </p>
        {preferences.length === 0 ? (
          <p className="ntq-muted">还没有偏好。</p>
        ) : (
          <ul className="settings-agent__pref-list">
            {preferences.map((rule) => (
              <li key={rule} className="settings-agent__pref-row">
                <span className="settings-agent__pref-text">{rule}</span>
                <Button
                  variant="ghost"
                  onClick={() => handleRemovePreference(rule)}
                >
                  删除
                </Button>
              </li>
            ))}
          </ul>
        )}
        <div className="settings-agent__pref-add">
          <UiTextField
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
            hint={`${draftRule.length}/${preferenceMaxChars}`}
          />
          <Button
            variant="primary"
            disabled={!draftRule.trim() || preferences.length >= preferenceMaxRules}
            onClick={handleAddPreference}
          >
            添加
          </Button>
        </div>
      </Section>

      <Section className="settings-agent__context" gap="md">
        <Heading level="h3" gap="none">补充说明</Heading>
        <p className="ntq-muted">
          追加到助理上下文（不会覆盖产品红线）。适合写风格或常用约定，最多
          {' '}
          {contextPromptMaxChars}
          {' '}
          字。
        </p>
        <UiTextArea
          label="补充说明"
          labelPlacement="none"
          rows={4}
          value={contextPrompt}
          onChange={(e) => setContextPrompt(e.target.value.slice(0, contextPromptMaxChars))}
          placeholder="例如：优先用中文解释；涉及回测先确认区间。"
          hint={`${contextPrompt.length}/${contextPromptMaxChars}`}
          aria-label="补充说明"
        />
      </Section>

      <Section className="settings-agent__session" gap="md">
        <Heading level="h3" gap="none">会话</Heading>
        <p className="ntq-muted">
          清空本机当前会话的对话记录与局部任务状态。不会删除跨会话偏好、策略代码或回测报告。
        </p>
        <div className="settings-agent__actions">
          <Button
            variant="danger"
            disabled={clearBusy || saving}
            onClick={handleClearSession}
          >
            {clearBusy ? '清空中…' : '清空本机会话'}
          </Button>
        </div>
      </Section>

      <Section className="settings-agent__form-actions" gap="md">
        <div className="settings-agent__actions">
          <Button variant="primary" onClick={handleSave} disabled={saving}>
            {saving ? '保存中…' : '保存 Agent 设置'}
          </Button>
          <Button
            variant="glass"
            icon="refresh"
            iconSize="sm"
            onClick={load}
            disabled={saving || clearBusy}
          >
            重新读取
          </Button>
        </div>
      </Section>
    </Section>
  );
}
