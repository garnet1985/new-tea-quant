import React, { useCallback, useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { submitFeedback } from 'api/feedbackApi';
import FeedbackPromptOverlay from 'views/feedbackPromptOverlay';
import { subscribeFeedbackPrompt } from 'service/feedbackPromptBus';

/**
 * Listens for soft-prompt requests after successful tasks.
 * Not a Trace consent gate — send needs no local permission.
 */
function FeedbackPromptGuard({ children = null }) {
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
  }, [close]);

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
      />
    </>
  );
}

FeedbackPromptGuard.propTypes = {
  children: PropTypes.node,
};

export default FeedbackPromptGuard;
