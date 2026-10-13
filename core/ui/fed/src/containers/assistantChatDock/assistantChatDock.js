import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { IconButton } from '@mui/material';
import NtqIcon from 'views/ntqIcon';
import RainbowButton from 'views/rainbowButton';
import LoadingBars from 'views/loadingBars';
import AssistantTypewriter from './assistantTypewriter';
import { chatWithAssistant, fetchNtqQuota, listAssistantProviders } from 'api/assistantApi';
import { fetchMembershipSettings } from 'api/settingsApi';
import { fetchSiteUrls } from 'api/siteApi';
import { isHttpStatusError } from 'service/request';
import { GLOBAL_HELPER_SESSION_EVENT } from 'containers/globalHelper';
import './style.scss';

function errorMessage(err, fallback) {
  if (isHttpStatusError(err) && err.message) return err.message;
  return String(err?.message || fallback);
}

function nextId(idRef) {
  const value = idRef.current;
  idRef.current += 1;
  return value;
}

function settingsLinkFor(content) {
  const text = String(content || '');
  if (/凭证/.test(text)) {
    return { to: '/settings/membership', label: '去设置检查通用凭证' };
  }
  if (/自己的密钥|供应商|API Key/.test(text)) {
    return { to: '/settings/assistant', label: '去设置填写 API Key' };
  }
  return null;
}

function buildAiOptions(items, membership) {
  const options = [];
  if (membership?.configured) {
    options.push({ id: 'ntq', label: 'NTQ AI' });
  }
  (Array.isArray(items) ? items : []).forEach((item) => {
    if (item?.enabled && item?.hasApiKey && item.providerId) {
      options.push({ id: String(item.providerId), label: String(item.providerId) });
    }
  });
  return options;
}

function toHistory(messages) {
  return messages
    .filter((item) => (
      (item.role === 'user' || item.role === 'assistant')
      && item.content
      && !item.pending
      && !item.error
    ))
    .map((item) => ({ role: item.role, content: item.content }));
}

function BubbleBody({ item, onNavigate }) {
  const link = item.error ? settingsLinkFor(item.content) : null;
  return (
    <>
      <p className="ntq-assistant-dock__bubble-text">{item.content}</p>
      {link ? (
        <RouterLink
          className="ntq-assistant-dock__settings-link"
          to={link.to}
          onClick={onNavigate}
        >
          {link.label}
        </RouterLink>
      ) : null}
    </>
  );
}

function AssistantChatDock() {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState('');
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);
  const [hint, setHint] = useState('');
  const [needsKey, setNeedsKey] = useState(false);
  const [options, setOptions] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [ntqQuota, setNtqQuota] = useState(null);
  const [registerUrl, setRegisterUrl] = useState('');
  const listRef = useRef(null);
  const inputRef = useRef(null);
  const idRef = useRef(1);
  const typedIdsRef = useRef(new Set());

  const latestAssistantId = [...messages].reverse().find((item) => (
    item.role === 'assistant' && !item.error && !item.pending && item.content
  ))?.id ?? null;

  const markTyped = useCallback((id) => {
    if (id != null) typedIdsRef.current.add(id);
  }, []);

  const scrollToBottom = useCallback(() => {
    const el = listRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, []);

  const toggleOpen = useCallback(() => {
    setOpen((value) => !value);
  }, []);

  const close = useCallback(() => {
    setOpen(false);
  }, []);

  useEffect(() => {
    const onHelper = (event) => {
      if (event?.detail?.open) setOpen(false);
    };
    window.addEventListener(GLOBAL_HELPER_SESSION_EVENT, onHelper);
    return () => window.removeEventListener(GLOBAL_HELPER_SESSION_EVENT, onHelper);
  }, []);

  useEffect(() => {
    let alive = true;
    fetchSiteUrls()
      .then((urls) => {
        if (alive) setRegisterUrl(urls.registerUrl);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    const timer = window.setTimeout(() => {
      inputRef.current?.focus();
    }, 40);
    return () => window.clearTimeout(timer);
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => {
      if (event.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    scrollToBottom();
  }, [messages, open, scrollToBottom]);

  useEffect(() => {
    if (!open) return undefined;
    let cancelled = false;
    Promise.all([
      listAssistantProviders(),
      fetchMembershipSettings().catch(() => ({ configured: false })),
    ])
      .then(([items, membership]) => {
        if (cancelled) return;
        const nextOptions = buildAiOptions(items, membership);
        setOptions(nextOptions);
        setSelectedId((current) => (
          nextOptions.some((item) => item.id === current) ? current : (nextOptions[0]?.id || '')
        ));
        setNeedsKey(nextOptions.length === 0);
        setHint('');
      })
      .catch((err) => {
        if (!cancelled) {
          setNeedsKey(false);
          setHint(errorMessage(err, '无法连接助理服务。'));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  const refreshNtqQuota = useCallback(() => {
    fetchNtqQuota()
      .then((quota) => {
        setNtqQuota(quota?.available ? quota : null);
      })
      .catch(() => setNtqQuota(null));
  }, []);

  useEffect(() => {
    if (!open || selectedId !== 'ntq') return undefined;
    refreshNtqQuota();
    return undefined;
  }, [open, selectedId, refreshNtqQuota]);

  const resizeDraft = useCallback((el) => {
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
  }, []);

  const send = useCallback(async () => {
    const content = draft.trim();
    if (!content || sending || !selectedId) return;
    const history = toHistory(messages);
    const userId = nextId(idRef);
    const pendingId = nextId(idRef);
    setDraft('');
    if (inputRef.current) {
      inputRef.current.style.height = '';
    }
    setSending(true);
    setMessages((prev) => [
      ...prev,
      { id: userId, role: 'user', content },
      { id: pendingId, role: 'assistant', content: '', pending: true },
    ]);
    try {
      const result = await chatWithAssistant({
        content,
        history,
        providerId: selectedId,
      });
      if (selectedId === 'ntq') refreshNtqQuota();
      setMessages((prev) => prev.map((item) => (
        item.id === pendingId
          ? { ...item, pending: false, content: result.reply || '（空回复）' }
          : item
      )));
    } catch (err) {
      setMessages((prev) => prev.map((item) => (
        item.id === pendingId
          ? { ...item, pending: false, error: true, content: errorMessage(err, '对话失败') }
          : item
      )));
    } finally {
      setSending(false);
    }
  }, [draft, messages, refreshNtqQuota, selectedId, sending]);

  const onDraftKeyDown = (event) => {
    if (event.nativeEvent.isComposing || event.keyCode === 229) return;
    if (event.key !== 'Enter') return;
    if (!(event.metaKey || event.ctrlKey)) return;
    event.preventDefault();
    send();
  };

  return (
    <div className="ntq-assistant-dock">
      <div className="ntq-assistant-dock__fab-slot">
        <RainbowButton
          size="lg"
          glow
          quiet={open}
          mark={open ? '' : 'ai'}
          icon={open ? 'cancel' : ''}
          onClick={toggleOpen}
          aria-label={open ? '关闭新茶' : '打开新茶'}
          aria-expanded={open}
          aria-controls="ntq-assistant-dialog"
        />
      </div>

      {open ? (
        <section
          id="ntq-assistant-dialog"
          className="ntq-assistant-dock__panel"
          role="dialog"
          aria-modal="false"
          aria-label="新茶"
        >
          <header className="ntq-assistant-dock__head">
            <div className="ntq-assistant-dock__brand">
              <img
                className="ntq-assistant-dock__mascot"
                src="/logo.png"
                alt=""
              />
              <div className="ntq-assistant-dock__head-text">
                <p className="ntq-assistant-dock__title">您好，我是新茶，有什么可以帮到您？</p>
                <p className="ntq-assistant-dock__subtitle">我现在还只能帮助您回答一些基础问题，之后的版本喵星还会赋予我更强大的能力哦</p>
              </div>
            </div>
            <IconButton
              className="ntq-assistant-dock__close"
              onClick={close}
              aria-label="关闭新茶"
              size="small"
              disableRipple
            >
              <NtqIcon name="cancel" size={18} tone="muted" />
            </IconButton>
          </header>

          <div ref={listRef} className="ntq-assistant-dock__messages">
            {messages.length === 0 ? (
              <p className="ntq-assistant-dock__empty">
                {needsKey ? (
                  <>
                    还没有可用的 AI。可以在设置里填写自己的 API Key，或到官网注册会员，把通用凭证放进设置。
                    {' '}
                    <RouterLink
                      className="ntq-assistant-dock__settings-link"
                      to="/settings/assistant"
                      onClick={close}
                    >
                      自己配置 AI
                    </RouterLink>
                    {registerUrl ? (
                      <>
                        {' '}
                        <a
                          className="ntq-assistant-dock__settings-link"
                          href={registerUrl}
                          target="_blank"
                          rel="noreferrer"
                        >
                          去官网注册
                        </a>
                        {' '}
                      </>
                    ) : null}
                    <RouterLink
                      className="ntq-assistant-dock__settings-link"
                      to="/settings/membership"
                      onClick={close}
                    >
                      放入设置
                    </RouterLink>
                  </>
                ) : (hint || '新茶在听。')}
              </p>
            ) : null}
            {messages.map((item) => (
              <div
                key={item.id}
                className={[
                  'ntq-assistant-dock__bubble',
                  `is-${item.role}`,
                  item.error ? 'is-error' : '',
                  item.pending ? 'is-pending' : '',
                ].filter(Boolean).join(' ')}
              >
                {item.pending ? (
                  <div className="ntq-assistant-dock__waiting" role="status">
                    <LoadingBars barCount={4} className="ntq-loading-bars--sm" aria-label="正在联络喵星总部" />
                    <span>正在联络喵星总部…</span>
                  </div>
                ) : item.role === 'assistant' && !item.error ? (
                  <AssistantTypewriter
                    text={item.content}
                    animate={item.id === latestAssistantId && !typedIdsRef.current.has(item.id)}
                    onProgress={scrollToBottom}
                    onDone={() => markTyped(item.id)}
                  />
                ) : (
                  <BubbleBody item={item} onNavigate={close} />
                )}
              </div>
            ))}
          </div>

          <form
            className="ntq-assistant-dock__composer"
            onSubmit={(event) => {
              event.preventDefault();
              send();
            }}
          >
            <textarea
              ref={inputRef}
              className="ntq-assistant-dock__input"
              value={draft}
              onChange={(event) => {
                setDraft(event.target.value);
                resizeDraft(event.target);
              }}
              onKeyDown={onDraftKeyDown}
              placeholder="可以问任何 NTQ 问题，例如：我该怎么制定一个策略？"
              rows={2}
              disabled={sending}
              aria-label="给新茶的问题"
            />
            <div className="ntq-assistant-dock__actions">
              <span className="ntq-assistant-dock__quota">
                {selectedId === 'ntq' && ntqQuota ? `(${ntqQuota.remaining}/${ntqQuota.limit})` : ''}
              </span>
              <div className="ntq-assistant-dock__actions-end">
                {options.length > 0 ? (
                  <select
                    className="ntq-assistant-dock__picker"
                    value={selectedId}
                    onChange={(event) => setSelectedId(event.target.value)}
                    disabled={sending}
                    aria-label="选择 AI"
                  >
                    {options.map((item) => (
                      <option key={item.id} value={item.id}>{item.label}</option>
                    ))}
                  </select>
                ) : null}
                <button
                  type="submit"
                  className="ntq-assistant-dock__send"
                  disabled={sending || !draft.trim() || !selectedId}
                >
                  发送
                </button>
              </div>
            </div>
          </form>
        </section>
      ) : null}
    </div>
  );
}

export default AssistantChatDock;
