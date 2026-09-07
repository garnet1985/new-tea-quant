import React from 'react';
import {
  Alert,
  Button,
  Card,
  CardContent,
  Stack,
  Typography,
} from '@mui/material';
import { SETUP_CHOICE_COPY } from './setup.helpers';

function SetupChoiceCard({
  stepId,
  errorMessage = '',
  submitting = false,
  onConfirm,
  onSkip,
}) {
  const copy = SETUP_CHOICE_COPY[stepId] || {
    title: '继续？',
    body: '',
    confirmLabel: '继续',
    skipLabel: '跳过',
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="h6" sx={{ mb: 1 }}>
          {copy.title}
        </Typography>
        {copy.body ? (
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            {copy.body}
          </Typography>
        ) : null}
        {errorMessage ? (
          <Alert severity="error" sx={{ mb: 2 }}>{errorMessage}</Alert>
        ) : null}
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
          <Button
            variant="contained"
            disabled={submitting}
            onClick={onConfirm}
          >
            {copy.confirmLabel}
          </Button>
          <Button
            variant="outlined"
            disabled={submitting}
            onClick={onSkip}
          >
            {copy.skipLabel}
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}

export default SetupChoiceCard;
