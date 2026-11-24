import React, { useCallback, useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import AssistantTypewriter from './assistantTypewriter';
import { REPLY_DISCLAIMER } from './splitAssistantReply';

function formatSpentLabel(spent) {
  if (spent == null || spent === '' || Number.isNaN(Number(spent))) return null;
  const n = Number(spent);
  if (n < 0) return null;
  return `本次消耗猫粮 ${n.toFixed(2)}`;
}

/**
 * 按序流式展示：正文 → 免责 → 猫粮 → 下一步 chips。
 * 后段不在前段打完前出现。
 */
function AssistantReplyStream({
  body = '',
  spent = null,
  suggestions = [],
  showDisclaimer = true,
  animate = false,
  sending = false,
  onProgress,
  onComplete,
  onPickNext,
}) {
  const spentLabel = formatSpentLabel(spent);
  const chips = Array.isArray(suggestions) ? suggestions.filter(Boolean).slice(0, 2) : [];
  const [phase, setPhase] = useState(() => (animate ? 'body' : 'done'));
  const phaseRef = useRef(phase);
  const completedRef = useRef(false);
  const streamKey = `${body}\0${spentLabel || ''}\0${showDisclaimer}\0${chips.join('\u0001')}`;

  phaseRef.current = phase;

  useEffect(() => {
    completedRef.current = false;
    setPhase(animate ? 'body' : 'done');
  }, [streamKey, animate]);

  const finish = useCallback(() => {
    if (completedRef.current) return;
    completedRef.current = true;
    setPhase('done');
    onComplete?.();
  }, [onComplete]);

  const onBodyDone = useCallback(() => {
    if (phaseRef.current !== 'body') return;
    if (showDisclaimer) setPhase('disclaimer');
    else if (spentLabel) setPhase('spent');
    else if (chips.length) {
      setPhase('chips');
      finish();
    } else finish();
  }, [showDisclaimer, spentLabel, chips.length, finish]);

  const onDisclaimerDone = useCallback(() => {
    if (phaseRef.current !== 'disclaimer') return;
    if (spentLabel) setPhase('spent');
    else if (chips.length) {
      setPhase('chips');
      finish();
    } else finish();
  }, [spentLabel, chips.length, finish]);

  const onSpentDone = useCallback(() => {
    if (phaseRef.current !== 'spent') return;
    if (chips.length) {
      setPhase('chips');
      finish();
    } else finish();
  }, [chips.length, finish]);

  // 非动画：直接完成回调一次（刷新猫粮等）
  useEffect(() => {
    if (animate) return undefined;
    finish();
    return undefined;
  }, [animate, streamKey, finish]);

  const showDisc = phase === 'disclaimer' || phase === 'spent' || phase === 'chips' || phase === 'done';
  const showSpent = phase === 'spent' || phase === 'chips' || phase === 'done';
  const showChips = phase === 'chips' || phase === 'done';

  return (
    <div className="ntq-assistant-dock__reply-stream">
      <AssistantTypewriter
        text={body}
        animate={animate && phase === 'body'}
        onProgress={onProgress}
        onDone={onBodyDone}
      />

      {showDisclaimer && showDisc ? (
        <div className="ntq-assistant-dock__reply-disclaimer" role="note">
          <AssistantTypewriter
            text={REPLY_DISCLAIMER}
            animate={animate && phase === 'disclaimer'}
            onProgress={onProgress}
            onDone={onDisclaimerDone}
          />
        </div>
      ) : null}

      {spentLabel && showSpent ? (
        <div className="ntq-assistant-dock__reply-spent">
          <AssistantTypewriter
            text={spentLabel}
            animate={animate && phase === 'spent'}
            onProgress={onProgress}
            onDone={onSpentDone}
          />
        </div>
      ) : null}

      {showChips && chips.length ? (
        <div className="ntq-assistant-dock__next-steps" role="group" aria-label="建议的下一步">
          {chips.map((text) => (
            <button
              key={text}
              type="button"
              className="ntq-assistant-dock__next-step"
              disabled={sending}
              onClick={() => onPickNext?.(text)}
            >
              <span className="ntq-assistant-dock__next-step-text">{text}</span>
              <span className="ntq-assistant-dock__next-step-arrow" aria-hidden="true">→</span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

AssistantReplyStream.propTypes = {
  body: PropTypes.string,
  spent: PropTypes.number,
  suggestions: PropTypes.arrayOf(PropTypes.string),
  showDisclaimer: PropTypes.bool,
  animate: PropTypes.bool,
  sending: PropTypes.bool,
  onProgress: PropTypes.func,
  onComplete: PropTypes.func,
  onPickNext: PropTypes.func,
};

export default AssistantReplyStream;
