import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { Button, Icon, TextArea } from 'ui';
import './style.scss';

/**
 * Lightweight soft-feedback toast (bottom-right; not a consent gate).
 */
function FeedbackPromptOverlay({
  open = false,
  onSubmit,
  onLater,
}) {
  const [rating, setRating] = useState('');
  const [text, setText] = useState('');
  const [mounted, setMounted] = useState(false);
  const [phase, setPhase] = useState('enter'); // enter | leave

  useEffect(() => {
    if (open) {
      setRating('');
      setText('');
      setMounted(true);
      setPhase('enter');
      return undefined;
    }
    if (!mounted) return undefined;
    setPhase('leave');
    return undefined;
  }, [open, mounted]);

  if (!mounted) return null;

  const canSend = rating === 'up' || rating === 'down';

  return (
    <div
      className="feedback-prompt-overlay"
      role="dialog"
      aria-modal="false"
      aria-labelledby="feedback-prompt-title"
    >
      <div
        className={`feedback-prompt-overlay__panel is-${phase}`}
        onAnimationEnd={() => {
          if (phase === 'leave') {
            setMounted(false);
          }
        }}
      >
        <h2
          id="feedback-prompt-title"
          className="feedback-prompt-overlay__title"
        >
          这次体验怎么样？
        </h2>
        <p className="feedback-prompt-overlay__copy">
          可选：点一下并写一句（也可跳过）。发送不需要额外授权。
        </p>

        <div
          className="feedback-prompt-overlay__rating"
          role="group"
          aria-label="评价"
        >
          <button
            type="button"
            aria-label="满意"
            aria-pressed={rating === 'up'}
            className={[
              'feedback-prompt-overlay__rate-btn',
              rating === 'up' ? 'is-active' : '',
            ].filter(Boolean).join(' ')}
            onClick={() => setRating('up')}
          >
            <Icon
              name="sentimentSatisfied"
              size={18}
              tone={rating === 'up' ? 'warning' : 'muted'}
              className="feedback-prompt-overlay__rate-icon"
            />
            <span>满意</span>
          </button>
          <button
            type="button"
            aria-label="不满意"
            aria-pressed={rating === 'down'}
            className={[
              'feedback-prompt-overlay__rate-btn',
              rating === 'down' ? 'is-active' : '',
            ].filter(Boolean).join(' ')}
            onClick={() => setRating('down')}
          >
            <Icon
              name="sentimentDissatisfied"
              size={18}
              tone={rating === 'down' ? 'warning' : 'muted'}
              className="feedback-prompt-overlay__rate-icon"
            />
            <span>不满意</span>
          </button>
        </div>

        <TextArea
          label="想说的话（可选）"
          value={text}
          onChange={(e) => setText(e.target.value.slice(0, 2000))}
          rows={2}
          maxWidth={false}
          hint={`${text.length}/2000`}
        />

        <div className="feedback-prompt-overlay__actions">
          <Button variant="ghost" onClick={onLater}>
            以后再说
          </Button>
          <Button
            variant="primary"
            disabled={!canSend}
            onClick={() => onSubmit({ rating, text })}
          >
            发送
          </Button>
        </div>
      </div>
    </div>
  );
}

FeedbackPromptOverlay.propTypes = {
  open: PropTypes.bool,
  onSubmit: PropTypes.func.isRequired,
  onLater: PropTypes.func.isRequired,
};

export default FeedbackPromptOverlay;
