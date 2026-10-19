import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { IconButton } from '@mui/material';
import NtqIcon from 'views/ntqIcon';
import RainbowButton from 'views/rainbowButton';
import AssistantTypewriter from './assistantTypewriter';
import PendingStream from './pendingStream';
import {
  runAgent,
  clearAgentSession,
  fetchAgentSessionHistory,
  fetchAgentQuota,
} from 'api/agentApi';
import { listAiProviders } from 'api/aiApi';
import { fetchMembershipSettings, notifyMembershipChanged } from 'api/settingsApi';
import { fetchSiteUrls } from 'api/siteApi';
import { isHttpStatusError } from 'service/request';
import { GLOBAL_HELPER_SESSION_EVENT } from 'containers/globalHelper';
import {
  clearDockChat,
  hydrateMessages,
  isHeavyContext,
  loadDockStore,
  persistDockChat,
  persistDockSelectedId,
  readDockChat,
} from './dockChatStore';
import './style.scss';

function formatCatfoodSpent(value) {
  if (value == null || Number.isNaN(Number(value))) return null;
  return Number(value).toFixed(2);
}

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
    return { to: '/settings/ai', label: '去设置填写 API Key' };
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

function SpentLine({ spent }) {
  const text = formatCatfoodSpent(spent);
  if (text == null) return null;
  return (
    <p className="ntq-assistant-dock__spent">
      本次消耗猫粮
      {' '}
      <span>{text}</span>
    </p>
  );
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
      {!item.error ? <SpentLine spent={item.catfoodSpent} /> : null}
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
  const [selectedId, setSelectedId] = useState(() => loadDockStore().selectedId || '');
  const [ntqQuota, setNtqQuota] = useState(null);
  const [registerUrl, setRegisterUrl] = useState('');
  const [contextTipDismissed, setContextTipDismissed] = useState(false);
  const listRef = useRef(null);
  const inputRef = useRef(null);
  const idRef = useRef(1);
  const typedIdsRef = useRef(new Set());
  const messagesRef = useRef(messages);
  const messagesOwnerRef = useRef('');
  const prevSelectedRef = useRef('');

  messagesRef.current = messages;

  const latestAssistantId = [...messages].reverse().find((item) => (
    item.role === 'assistant' && !item.error && !item.pending && item.content
  ))?.id ?? null;

  const showContextTip = !contextTipDismissed && isHeavyContext(messages);

  const markTyped = useCallback((id) => {
    if (id != null) typedIdsRef.current.add(id);
  }, []);

  const applyMessages = useCallback((rows, { markAllTyped = true } = {}) => {
    const hydrated = hydrateMessages(rows, { idRef });
    setMessages(hydrated);
    if (markAllTyped) {
      typedIdsRef.current = new Set(hydrated.map((item) => item.id));
    }
    setContextTipDismissed(false);
    return hydrated;
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
      listAiProviders(),
      fetchMembershipSettings().catch(() => ({ configured: false })),
    ])
      .then(([items, membership]) => {
        if (cancelled) return;
        const nextOptions = buildAiOptions(items, membership);
        setOptions(nextOptions);
        const storedId = loadDockStore().selectedId;
        setSelectedId((current) => {
          if (nextOptions.some((item) => item.id === current)) return current;
          if (storedId && nextOptions.some((item) => item.id === storedId)) return storedId;
          return nextOptions[0]?.id || '';
        });
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

  // SPA 内 dock 挂在 AppShell，切页不丢；刷新则从 localStorage / 本机 transcript 恢复。
  useEffect(() => {
    if (!selectedId) return undefined;
    let cancelled = false;
    const prev = prevSelectedRef.current;

    if (prev && prev !== selectedId && messagesOwnerRef.current === prev) {
      persistDockChat(prev, messagesRef.current);
    }
    if (prev === selectedId) return undefined;

    prevSelectedRef.current = selectedId;
    persistDockSelectedId(selectedId);

    const local = readDockChat(selectedId);
    if (local.length) {
      messagesOwnerRef.current = selectedId;
      applyMessages(local);
      return undefined;
    }

    messagesOwnerRef.current = selectedId;
    setMessages([]);
    typedIdsRef.current = new Set();
    setContextTipDismissed(false);

    if (selectedId !== 'ntq') return undefined;

    fetchAgentSessionHistory({ limit: 20 })
      .then((result) => {
        if (cancelled || prevSelectedRef.current !== 'ntq') return;
        if (!result.messages.length) return;
        messagesOwnerRef.current = 'ntq';
        const hydrated = applyMessages(result.messages);
        persistDockChat('ntq', hydrated);
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, [selectedId, applyMessages]);

  useEffect(() => {
    if (!selectedId || sending) return undefined;
    if (messagesOwnerRef.current !== selectedId) return undefined;
    const timer = window.setTimeout(() => {
      persistDockChat(selectedId, messagesRef.current);
    }, 200);
    return () => window.clearTimeout(timer);
  }, [messages, selectedId, sending]);

  useEffect(() => {
    const onUnload = () => {
      if (selectedId && messagesOwnerRef.current === selectedId) {
        persistDockChat(selectedId, messagesRef.current);
      }
    };
    window.addEventListener('beforeunload', onUnload);
    return () => window.removeEventListener('beforeunload', onUnload);
  }, [selectedId]);

  const refreshNtqQuota = useCallback(() => {
    fetchAgentQuota()
      .then((quota) => {
        setNtqQuota(quota?.available ? quota : null);
        if (quota?.available && quota.balance != null) {
          notifyMembershipChanged({ catfood: quota.balance });
        }
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

  const clearChat = useCallback(async () => {
    if (sending) return;
    try {
      if (selectedId === 'ntq') {
        await clearAgentSession();
      }
      clearDockChat(selectedId);
      messagesOwnerRef.current = selectedId;
      setMessages([]);
      typedIdsRef.current = new Set();
      setHint('');
      setContextTipDismissed(false);
      if (selectedId === 'ntq') refreshNtqQuota();
    } catch (err) {
      setHint(errorMessage(err, '清空会话失败'));
    }
  }, [refreshNtqQuota, selectedId, sending]);

  const send = useCallback(async () => {
    const content = draft.trim();
    if (!content || sending || !selectedId) return;
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
      {
        id: pendingId,
        role: 'assistant',
        content: '',
        pending: true,
        pendingKind: selectedId === 'ntq' ? 'work' : 'ask',
        pendingUserText: content,
      },
    ]);
    try {
      const result = await runAgent({
        content,
        providerId: selectedId === 'ntq' ? 'ntq' : selectedId,
      });
      const spent = selectedId === 'ntq' ? result.catfoodSpent : null;
      const balance = selectedId === 'ntq' ? result.balance : null;
      if (selectedId === 'ntq') {
        if (balance != null) {
          setNtqQuota((prev) => (
            prev
              ? { ...prev, balance, remaining: balance }
              : {
                available: true,
                balance,
                remaining: balance,
                currency: '猫粮',
              }
          ));
          notifyMembershipChanged({ catfood: balance });
        }
        refreshNtqQuota();
      }
      setMessages((prev) => prev.map((item) => (
        item.id === pendingId
          ? {
            ...item,
            pending: false,
            content: result.reply || '（空回复）',
            mode: result.mode || (selectedId === 'ntq' ? 'ask' : undefined),
            catfoodSpent: spent,
          }
          : item
      )));
    } catch (err) {
      setMessages((prev) => prev.map((item) => (
        item.id === pendingId
          ? {
            ...item,
            pending: false,
            error: true,
            content: errorMessage(err, '对话失败'),
          }
          : item
      )));
    } finally {
      setSending(false);
    }
  }, [draft, refreshNtqQuota, selectedId, sending]);

  const onDraftKeyDown = (event) => {
    if (event.nativeEvent.isComposing || event.keyCode === 229) return;
    if (event.key !== 'Enter') return;
    if (event.shiftKey) return;
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
                <p className="ntq-assistant-dock__subtitle">
                  {selectedId === 'ntq'
                    ? '可以问策略、回测和扫描；我会在本机执行工具（走 NTQ 会员额度）。'
                    : '可以问策略、回测和扫描；我会在本机执行工具（走您自己的 API Key，不计 NTQ 猫粮）。'}
                </p>
              </div>
            </div>
            <div className="ntq-assistant-dock__head-actions">
              <button
                type="button"
                className="ntq-assistant-dock__clear"
                onClick={clearChat}
                disabled={sending || messages.length === 0}
              >
                清空会话
              </button>
              <IconButton
                className="ntq-assistant-dock__close"
                onClick={close}
                aria-label="关闭新茶"
                size="small"
                disableRipple
              >
                <NtqIcon name="cancel" size={18} tone="muted" />
              </IconButton>
            </div>
          </header>

          <div ref={listRef} className="ntq-assistant-dock__messages">
            {showContextTip ? (
              <div className="ntq-assistant-dock__context-tip" role="status">
                <p className="ntq-assistant-dock__context-tip-text">
                  对话已经比较长，继续追问会多耗猫粮。策略与回测结果在本机，可放心开新会话。
                </p>
                <div className="ntq-assistant-dock__context-tip-actions">
                  <button
                    type="button"
                    className="ntq-assistant-dock__context-tip-btn"
                    onClick={clearChat}
                    disabled={sending}
                  >
                    新开会话
                  </button>
                  <button
                    type="button"
                    className="ntq-assistant-dock__context-tip-dismiss"
                    onClick={() => setContextTipDismissed(true)}
                  >
                    知道了
                  </button>
                </div>
              </div>
            ) : null}
            {messages.length === 0 ? (
              <p className="ntq-assistant-dock__empty">
                {needsKey ? (
                  <>
                    还没有可用的 AI。可以在设置里填写自己的 API Key，或到官网注册会员，把通用凭证放进设置。
                    {' '}
                    <RouterLink
                      className="ntq-assistant-dock__settings-link"
                      to="/settings/ai"
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
                  <PendingStream
                    kind={item.pendingKind === 'ask' ? 'ask' : 'work'}
                    userText={item.pendingUserText || ''}
                    onTick={scrollToBottom}
                  />
                ) : item.role === 'assistant' && !item.error ? (
                  <>
                    <AssistantTypewriter
                      text={item.content}
                      animate={item.id === latestAssistantId && !typedIdsRef.current.has(item.id)}
                      onProgress={scrollToBottom}
                      onDone={() => markTyped(item.id)}
                    />
                    <SpentLine spent={item.catfoodSpent} />
                  </>
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
            <p className="ntq-assistant-dock__composer-hint">
              Enter 发送 · Shift+Enter 换行
            </p>
            <textarea
              ref={inputRef}
              className="ntq-assistant-dock__input"
              value={draft}
              onChange={(event) => {
                setDraft(event.target.value);
                resizeDraft(event.target);
              }}
              onKeyDown={onDraftKeyDown}
              placeholder={selectedId === 'ntq'
                ? '例如：帮我建一个双均线策略并回测'
                : '可以问任何 NTQ 问题，例如：我该怎么制定一个策略？'}
              rows={2}
              disabled={sending}
              aria-label="给新茶的问题"
            />
            <div className="ntq-assistant-dock__actions">
              <span className="ntq-assistant-dock__quota" aria-live="polite">
                {sending && selectedId === 'ntq'
                  ? '进行中…'
                  : selectedId === 'ntq' && ntqQuota
                    ? `${Number(ntqQuota.balance ?? ntqQuota.remaining).toFixed(2)} ${ntqQuota.currency || '猫粮'}`
                    : ''}
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
