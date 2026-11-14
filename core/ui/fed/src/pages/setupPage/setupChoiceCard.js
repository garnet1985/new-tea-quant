import React, { useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  CardActionArea,
  CardContent,
  Link,
  Stack,
  Typography,
} from '@mui/material';
import { FALLBACK_REGISTER_URL, fetchSiteUrls, resolveRegisterUrl } from 'api/siteApi';
import { SETUP_CHOICE_COPY } from './setup.helpers';

function SetupChoiceCard({
  stepId,
  errorMessage = '',
  submitting = false,
  packageHint = '',
  onConfirm,
  onSkip,
}) {
  const copy = SETUP_CHOICE_COPY[stepId] || {
    title: '继续？',
    layout: 'buttons',
    body: '',
    confirmLabel: '继续',
    skipLabel: '跳过',
  };
  const [registerUrl, setRegisterUrl] = useState(FALLBACK_REGISTER_URL);

  useEffect(() => {
    let cancelled = false;
    fetchSiteUrls()
      .then((urls) => {
        if (!cancelled) {
          setRegisterUrl(resolveRegisterUrl(urls.registerUrl));
        }
      })
      .catch(() => {
        if (!cancelled) {
          setRegisterUrl(FALLBACK_REGISTER_URL);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (copy.layout === 'cards' && Array.isArray(copy.choices) && copy.choices.length > 0) {
    return (
      <Card variant="outlined" className="setup-choice-card">
        <CardContent>
          <Typography variant="h6" sx={{ mb: 1.5 }}>
            {copy.title}
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 2.5, lineHeight: 1.7 }}>
            {copy.introBeforeLink}
            <Link
              href={registerUrl}
              target="_blank"
              rel="noopener noreferrer"
              underline="hover"
            >
              {copy.introLinkLabel}
            </Link>
            {copy.introAfterLink}
          </Typography>
          {packageHint ? (
            <Alert severity="info" sx={{ mb: 2 }}>{packageHint}</Alert>
          ) : null}
          {errorMessage ? (
            <Alert severity="error" sx={{ mb: 2 }}>{errorMessage}</Alert>
          ) : null}
          <Stack
            direction={{ xs: 'column', md: 'row' }}
            spacing={2}
            className="setup-choice-card__options"
          >
            {copy.choices.map((choice) => {
              const select = () => {
                if (choice.skip) {
                  onSkip();
                  return;
                }
                onConfirm();
              };
              return (
                <Card
                  key={choice.id}
                  variant="outlined"
                  className="setup-choice-card__option"
                  sx={{ flex: 1, minWidth: 0 }}
                >
                  <CardActionArea
                    disabled={submitting}
                    onClick={select}
                    sx={{ height: '100%', alignItems: 'stretch' }}
                  >
                    <CardContent sx={{ height: '100%' }}>
                      <Typography variant="h6" component="div" sx={{ mb: 1 }}>
                        {choice.title}
                      </Typography>
                      <Typography color="text.secondary" sx={{ lineHeight: 1.6 }}>
                        {choice.description}
                      </Typography>
                    </CardContent>
                  </CardActionArea>
                </Card>
              );
            })}
          </Stack>
        </CardContent>
      </Card>
    );
  }

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
