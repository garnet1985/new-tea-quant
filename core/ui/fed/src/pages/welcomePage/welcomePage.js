import React, { useCallback, useMemo, useRef, useState } from 'react';
import { Box, Typography } from '@mui/material';
import PageLayout from '../../components/pageLayout/pageLayout';
import WelcomeIntroCanvas from './welcomeIntroCanvas';
import './welcomePage.scss';

const LOGO_SRC = '/logo.png';

function prefersReducedMotion() {
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch {
    return false;
  }
}

function WelcomePage() {
  const logoRef = useRef(null);
  const skipIntro = prefersReducedMotion();
  const [introOn, setIntroOn] = useState(() => !skipIntro);
  const [pageReady, setPageReady] = useState(() => skipIntro);

  const pageClass = [
    'welcome-page',
    pageReady ? 'is-ready' : '',
    introOn ? 'is-intro-playing' : 'is-intro-done',
  ].filter(Boolean).join(' ');

  const revealPage = useCallback(() => {
    setPageReady(true);
  }, []);

  const finishIntro = useCallback(() => {
    setIntroOn(false);
    setPageReady(true);
  }, []);

  const lowerSlots = useMemo(() => ([
    { id: 'intro', title: '关于 NTQ', hint: '简介将放在这里' },
    { id: 'shortcuts', title: '快捷入口', hint: '常用操作将放在这里' },
  ]), []);

  return (
    <PageLayout
      className={pageClass}
      showBreadcrumbs={false}
      showBanner={false}
    >
      <Box className="welcome-page__stack">
        <Box className="welcome-hero">
          <Box
            component="img"
            ref={logoRef}
            src={LOGO_SRC}
            alt="New Tea Quant"
            className="welcome-hero__logo"
          />
          <Typography className="welcome-hero__title" component="h1">
            <span className="welcome-hero__en">Welcome</span>
            <span className="welcome-hero__sep" aria-hidden>|</span>
            <span className="welcome-hero__zh">欢迎使用</span>
          </Typography>
        </Box>

        <Box className="welcome-lower">
          {lowerSlots.map((slot) => (
            <Box key={slot.id} className="welcome-lower__slot">
              <Typography className="welcome-lower__slot-title" variant="subtitle1">
                {slot.title}
              </Typography>
              <Typography className="welcome-lower__slot-hint" variant="body2" color="text.secondary">
                {slot.hint}
              </Typography>
            </Box>
          ))}
        </Box>
      </Box>

      {introOn ? (
        <WelcomeIntroCanvas
          logoRef={logoRef}
          onPageReveal={revealPage}
          onDone={finishIntro}
        />
      ) : null}
    </PageLayout>
  );
}

export default WelcomePage;
