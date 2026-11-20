import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Block,
  Heading,
  Loading,
  Message,
  Button,
  Section,
  Tag,
  TextField as UiTextField,
} from 'ui';
import {
  fetchMembershipSettings,
} from '../../../api/settingsApi';
import { listAiProviders, saveAiProviderApiKey } from '../../../api/aiApi';

function NtqProxyCard({ configured }) {
  return (
    <Block
      className={[
        'settings-ai__card',
        configured ? 'settings-ai__card--ready' : '',
      ].filter(Boolean).join(' ')}
      surface={configured ? 'soft' : 'none'}
      bordered
      padding="md"
      gap="sm"
    >
      <div className="settings-ai__card-head">
        <strong>新茶量化（NTQ）AI</strong>
        <Tag
          status={configured ? 'success' : 'neutral'}
          variant={configured ? 'solid' : 'outline'}
        >
          {configured ? '已配置' : '未配置'}
        </Tag>
      </div>
      <p className="ntq-caption">官网代理 · 只读提示（会员凭证在「会员」页配置）</p>
      {configured ? (
        <p className="ntq-muted">
          NTQ AI 已配置，可直接使用。若想使用自己的模型，可在 AI 交互框中选择下方已配置的其他 AI。如果同时配置多个AI，可以在AI助手下方切换模型。
        </p>
      ) : (
        <p className="ntq-muted">
          尚未配置 NTQ AI。请先到
          {' '}
          <RouterLink className="ntq-link" to="/settings/membership">
            设置 → 会员
          </RouterLink>
          {' '}
          装载会员凭证；本页只做指引，不在这里填写凭证。
        </p>
      )}
    </Block>
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

  if (loading) {
    return <Loading variant="inline" message="正在加载 AI 供应商…" />;
  }

  return (
    <Section className="settings-ai" gap="lg">
      <Section className="settings-ai__ntq" gap="md">
        <Heading level="h3" gap="none">NTQ AI</Heading>
        <p className="ntq-muted">
          官网代理状态见下方卡片；凭证在「会员」页装载，本页不填写。
        </p>
        {loadError ? <Message status="error">{loadError}</Message> : null}
        {saveError ? <Message status="error">{saveError}</Message> : null}
        {saveOk ? <Message status="success">{saveOk}</Message> : null}
        <NtqProxyCard configured={membershipReady} />
      </Section>

      <Section className="settings-ai__providers" gap="md">
        <Heading level="h3" gap="none">使用自己的AI模型</Heading>
        <p className="ntq-muted">
          在此写入 API Key。页面不会显示明文密钥，只会显示是否已配置。
        </p>
        {sortedProviders.length === 0 ? (
          <Message status="info">
            还没有发现自己的AI模型。请先在扩展目录中放入AI模型包后再刷新本页。
          </Message>
        ) : (
          <div className="settings-ai__provider-list">
            {sortedProviders.map((item) => {
              const draft = drafts[item.providerId] || '';
              const busy = savingId === item.providerId;
              const configured = Boolean(item.hasApiKey);
              return (
                <Block
                  key={item.providerId}
                  className={[
                    'settings-ai__card',
                    configured ? 'settings-ai__card--ready' : '',
                  ].filter(Boolean).join(' ')}
                  surface={configured ? 'soft' : 'none'}
                  bordered
                  padding="md"
                  gap="sm"
                >
                  <div className="settings-ai__card-head">
                    <strong>{item.providerId}</strong>
                    <Tag
                      status={configured ? 'success' : 'neutral'}
                      variant={configured ? 'solid' : 'outline'}
                    >
                      {configured ? '已配置 API Key' : '尚未配置 API Key'}
                    </Tag>
                  </div>
                  <p className="ntq-caption">
                    {item.model}
                    {item.baseUrl ? ` · ${item.baseUrl}` : ''}
                    {item.enabled ? '' : ' · 已禁用'}
                  </p>
                  <UiTextField
                    type="password"
                    label="API Key"
                    value={draft}
                    onChange={handleDraftChange(item.providerId)}
                    autoComplete="off"
                    disabled={Boolean(savingId)}
                    placeholder={configured ? '输入新密钥可覆盖' : '粘贴 API Key'}
                  />
                  <div className="settings-ai__actions">
                    <Button
                      variant="primary"
                      disabled={!draft.trim() || Boolean(savingId)}
                      onClick={() => handleSave(item.providerId)}
                    >
                      {busy ? '保存中…' : '保存'}
                    </Button>
                  </div>
                </Block>
              );
            })}
          </div>
        )}
        <div className="settings-ai__actions">
          <Button
            variant="glass"
            icon="refresh"
            iconSize="sm"
            onClick={load}
            disabled={Boolean(savingId) || loading}
          >
            重新读取
          </Button>
        </div>
      </Section>
    </Section>
  );
}

