import React, { useCallback, useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { feedbackPromptAction, submitFeedback } from '../api/apis/feedbackApi';
import FeedbackPromptOverlay from './feedbackPromptOverlay';
import { subscribeFeedbackPrompt } from '../utils/feedbackPromptBus';

/**
 * Listens for soft-prompt requests after successful tasks.
 * Not a Trace consent gate — send needs no local permission.
 */
function FeedbackPromptGuard({ children }) {
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState('popup');

  useEffect(() => subscribeFeedbackPrompt((payload) => {
    setSource(String(payload?.source || 'popup'));
    setOpen(true);
  }), []);

  const close = useCallback(() => {
    setOpen(false);
  }, []);

  const onLater = useCallback(() => {
    close();
    feedbackPromptAction({ action: 'snooze', source }).catch(() => {});
  }, [close, source]);

  const onNever = useCallback(() => {
    close();
    feedbackPromptAction({ action: 'disable', source }).catch(() => {});
  }, [close, source]);

  const onSubmit = useCallback(({ rating, text }) => {
    // Always dismiss immediately; network result must not block UX.
    close();
    submitFeedback({ rating, text, source }).catch(() => {});
  }, [close, source]);

  return (
    <>
      {children}
      <FeedbackPromptOverlay
        open={open}
        onSubmit={onSubmit}
        onLater={onLater}
        onNever={onNever}
      />
    </>
  );
}

FeedbackPromptGuard.propTypes = {
  children: PropTypes.node,
};

FeedbackPromptGuard.defaultProps = {
  children: null,
};

export default FeedbackPromptGuard;
