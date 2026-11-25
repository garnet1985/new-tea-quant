import React, { useEffect, useState } from 'react';
import { Button, Message } from 'ui';
import { FALLBACK_REGISTER_URL, fetchSiteUrls, resolveRegisterUrl } from 'api/siteApi';
import { SETUP_CHOICE_COPY } from './setup.helpers';
import './setupChoiceCard.scss';

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
      <section className="setup-choice-card">
        <h3 className="setup-choice-card__title">{copy.title}</h3>
        <p className="setup-choice-card__intro ntq-muted">
          {copy.introBeforeLink}
          <a
            className="ntq-link"
            href={registerUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            {copy.introLinkLabel}
          </a>
          {copy.introAfterLink}
        </p>
        {packageHint ? (
          <Message status="info">{packageHint}</Message>
        ) : null}
        {errorMessage ? (
          <Message status="error">{errorMessage}</Message>
        ) : null}
        <div className="setup-choice-card__options">
          {copy.choices.map((choice) => {
            const select = () => {
              if (choice.skip) {
                onSkip();
                return;
              }
              onConfirm();
            };
            return (
              <button
                key={choice.id}
                type="button"
                className="setup-choice-card__option"
                disabled={submitting}
                onClick={select}
              >
                <span className="setup-choice-card__option-title">{choice.title}</span>
                <span className="setup-choice-card__option-desc ntq-muted">
                  {choice.description}
                </span>
              </button>
            );
          })}
        </div>
      </section>
    );
  }

  return (
    <section className="setup-choice-card setup-choice-card--simple">
      <h3 className="setup-choice-card__title">{copy.title}</h3>
      {copy.body ? (
        <p className="setup-choice-card__body ntq-muted">{copy.body}</p>
      ) : null}
      {errorMessage ? (
        <Message status="error">{errorMessage}</Message>
      ) : null}
      <div className="setup-choice-card__actions">
        <Button
          variant="primary"
          disabled={submitting}
          onClick={onConfirm}
        >
          {copy.confirmLabel}
        </Button>
        <Button
          variant="glass"
          disabled={submitting}
          onClick={onSkip}
        >
          {copy.skipLabel}
        </Button>
      </div>
    </section>
  );
}

export default SetupChoiceCard;
