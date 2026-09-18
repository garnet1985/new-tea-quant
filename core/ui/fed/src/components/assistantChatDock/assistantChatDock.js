import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { IconButton } from '@mui/material';
import NtqIcon from 'components/ntqIcon/ntqIcon';
import LoadingBars from 'components/loadingBars/loadingBars';
import AssistantTypewriter from './assistantTypewriter';
import { chatWithAssistant, listAssistantProviders } from 'api/assistantApi';
import { isHttpStatusError } from 'services/request';
import { GLOBAL_HELPER_SESSION_EVENT } from 'components/globalHelper/helpTarget';
import './assistantChatDock.scss';

function errorMessage(err, fallback) {
  if (isHttpStatusError(err) && err.message) return err.message;
  return String(err?.message || fallback);
}

function nextId(idRef) {
  const value = idRef.current;
  idRef.current += 1;
  return value;
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

function AssistantChatDock() {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState('');
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);
  const [hint, setHint] = useState('');
  const [needsKey, setNeedsKey] = useState(false);
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
    listAssistantProviders()
      .then((items) => {
        if (cancelled) return;
        const ready = (Array.isArray(items) ? items : []).some(
          (item) => item.enabled && item.hasApiKey,
        );
        setNeedsKey(!ready);
        setHint(ready ? '' : '还没有可用的 AI 供应商。');
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

  const resizeDraft = useCallback((el) => {
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
  }, []);

  const send = useCallback(async () => {
    const content = draft.trim();
    if (!content || sending) return;
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
      const result = await chatWithAssistant({ content, history });
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
  }, [draft, messages, sending]);

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
        <IconButton
          className={['ntq-assistant-dock__fab', open ? 'is-open' : ''].filter(Boolean).join(' ')}
          onClick={toggleOpen}
          aria-label={open ? '关闭新茶' : '打开新茶'}
          aria-expanded={open}
          aria-controls="ntq-assistant-dialog"
          disableRipple
        >
          <span className="ntq-assistant-dock__fab-glow" aria-hidden />
          <span className="ntq-assistant-dock__fab-ring" aria-hidden />
          <span className="ntq-assistant-dock__fab-icon">
            {open ? (
              <NtqIcon name="cancel" size={22} />
            ) : (
              <span className="ntq-assistant-dock__fab-ai-wrap" aria-hidden>
                <span className="ntq-assistant-dock__fab-spark ntq-assistant-dock__fab-spark--a" />
                <span className="ntq-assistant-dock__fab-spark ntq-assistant-dock__fab-spark--b" />
                <span className="ntq-assistant-dock__fab-ai">AI</span>
              </span>
            )}
          </span>
        </IconButton>
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
                <p className="ntq-assistant-dock__subtitle">有什么问题都可以问新茶哦</p>
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
                {hint || '新茶在听。'}
                {needsKey ? (
                  <>
                    {' '}
                    <RouterLink
                      className="ntq-assistant-dock__settings-link"
                      to="/settings/assistant"
                      onClick={close}
                    >
                      去设置填写 API Key
                    </RouterLink>
                  </>
                ) : null}
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
                  <>
                    <p className="ntq-assistant-dock__bubble-text">{item.content}</p>
                    {item.error && /密钥|供应商/.test(item.content) ? (
                      <RouterLink
                        className="ntq-assistant-dock__settings-link"
                        to="/settings/assistant"
                        onClick={close}
                      >
                        去设置填写 API Key
                      </RouterLink>
                    ) : null}
                  </>
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
            <button
              type="submit"
              className="ntq-assistant-dock__send"
              disabled={sending || !draft.trim()}
            >
              发送
            </button>
          </form>
        </section>
      ) : null}
    </div>
  );
}

export default AssistantChatDock;
