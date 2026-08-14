import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Button,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material';
import NtqIcon from '../ntqIcon/ntqIcon';
import './feedbackPromptOverlay.scss';

/**
 * Lightweight soft-feedback toast (bottom-right; not a consent gate).
 */
function FeedbackPromptOverlay({
  open,
  onSubmit,
  onLater,
  onNever,
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
    <Box
      className="feedback-prompt-overlay"
      role="dialog"
      aria-modal="false"
      aria-labelledby="feedback-prompt-title"
    >
      <Box
        className={`feedback-prompt-overlay__panel is-${phase}`}
        onAnimationEnd={() => {
          if (phase === 'leave') {
            setMounted(false);
          }
        }}
      >
        <Typography
          id="feedback-prompt-title"
          variant="h6"
          component="h2"
          className="feedback-prompt-overlay__title"
        >
          这次体验怎么样？
        </Typography>
        <Typography variant="body2" color="text.secondary" className="feedback-prompt-overlay__copy">
          可选：点一下并写一句（也可跳过）。发送不需要额外授权。
        </Typography>

        <ToggleButtonGroup
          exclusive
          size="small"
          value={rating || null}
          onChange={(_e, next) => {
            if (next) setRating(next);
          }}
          className="feedback-prompt-overlay__rating"
          aria-label="评价"
        >
          <ToggleButton value="up" aria-label="满意" className="feedback-prompt-overlay__rate-btn">
            <NtqIcon
              name="sentimentSatisfied"
              size={18}
              tone={rating === 'up' ? 'warning' : 'muted'}
              className="feedback-prompt-overlay__rate-icon"
            />
            <span>满意</span>
          </ToggleButton>
          <ToggleButton value="down" aria-label="不满意" className="feedback-prompt-overlay__rate-btn">
            <NtqIcon
              name="sentimentDissatisfied"
              size={18}
              tone={rating === 'down' ? 'warning' : 'muted'}
              className="feedback-prompt-overlay__rate-icon"
            />
            <span>不满意</span>
          </ToggleButton>
        </ToggleButtonGroup>

        <TextField
          label="想说的话（可选）"
          value={text}
          onChange={(e) => setText(e.target.value.slice(0, 2000))}
          multiline
          minRows={2}
          maxRows={5}
          fullWidth
          helperText={`${text.length}/2000`}
        />

        <Stack direction="row" spacing={1} className="feedback-prompt-overlay__actions" flexWrap="wrap">
          <Button variant="text" onClick={onNever}>
            不再询问
          </Button>
          <Box sx={{ flex: 1 }} />
          <Button variant="text" onClick={onLater}>
            以后再说
          </Button>
          <Button
            variant="contained"
            color="primary"
            disabled={!canSend}
            onClick={() => onSubmit({ rating, text })}
          >
            发送
          </Button>
        </Stack>
      </Box>
    </Box>
  );
}

FeedbackPromptOverlay.propTypes = {
  open: PropTypes.bool,
  onSubmit: PropTypes.func.isRequired,
  onLater: PropTypes.func.isRequired,
  onNever: PropTypes.func.isRequired,
};

FeedbackPromptOverlay.defaultProps = {
  open: false,
};

export default FeedbackPromptOverlay;
