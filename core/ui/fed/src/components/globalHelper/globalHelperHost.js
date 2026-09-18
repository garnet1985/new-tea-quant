import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { dismissUiHelper, fetchUiHelper } from 'api/uiHelperApi';
import { findHelpForPath, isHelpDismissed } from './catalog';
import {
  emitGlobalHelperSession,
  measureHole,
  placeCard,
  queryHelpTarget,
  resolveLiveSteps,
} from './helpTarget';
import GlobalHelperButton from './globalHelperButton';
import GlobalHelperOverlay from './globalHelperOverlay';
import './globalHelper.scss';

const CARD_FALLBACK = { width: 360, height: 220 };

function prefersReducedMotion() {
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch {
    return false;
  }
}

function GlobalHelperHost() {
  const location = useLocation();
  const help = useMemo(() => findHelpForPath(location.pathname), [location.pathname]);
  const [ledger, setLedger] = useState({ ready: false, ok: false, dismissed: {} });
  const [sessionDismissed, setSessionDismissed] = useState(() => new Set());
  const [open, setOpen] = useState(false);
  const [liveSteps, setLiveSteps] = useState([]);
  const [stepIndex, setStepIndex] = useState(0);
  const [pageIndex, setPageIndex] = useState(0);
  const [hole, setHole] = useState(null);
  const [holeReady, setHoleReady] = useState(false);
  const [cardSize, setCardSize] = useState(CARD_FALLBACK);
  const cardRef = useRef(null);
  const autoTriedRef = useRef('');
  const openRef = useRef(false);

  const step = liveSteps[stepIndex] || null;
  const pages = step?.pages || [];
  const page = pages[pageIndex] || pages[0] || null;
  const totalTicks = liveSteps.reduce((sum, item) => sum + Math.max(1, item.pages?.length || 1), 0);
  const currentTick = liveSteps.slice(0, stepIndex).reduce(
    (sum, item) => sum + Math.max(1, item.pages?.length || 1),
    0,
  ) + pageIndex + 1;
  const isFirst = stepIndex === 0 && pageIndex === 0;
  const isLast = stepIndex >= liveSteps.length - 1 && pageIndex >= pages.length - 1;

  useEffect(() => {
    openRef.current = open;
  }, [open]);

  useEffect(() => {
    let cancelled = false;
    fetchUiHelper()
      .then((data) => {
        if (!cancelled) setLedger({ ready: true, ok: true, dismissed: data.dismissed || {} });
      })
      .catch(() => {
        if (!cancelled) setLedger({ ready: true, ok: false, dismissed: {} });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const closeOverlay = useCallback((persistSource) => {
    const current = help;
    setOpen(false);
    setLiveSteps([]);
    setStepIndex(0);
    setPageIndex(0);
    setHole(null);
    emitGlobalHelperSession(false);
    if (!current || !persistSource) return;
    setSessionDismissed((prev) => {
      const next = new Set(prev);
      next.add(current.id);
      return next;
    });
    dismissUiHelper({
      helpId: current.id,
      version: current.version || 1,
      source: persistSource,
    }).catch(() => {});
  }, [help]);

  const startTour = useCallback((steps) => {
    if (!steps.length) return false;
    setLiveSteps(steps);
    setStepIndex(0);
    setPageIndex(0);
    setOpen(true);
    emitGlobalHelperSession(true);
    const el = queryHelpTarget(steps[0].target);
    el?.scrollIntoView({
      block: 'nearest',
      inline: 'nearest',
      behavior: prefersReducedMotion() ? 'auto' : 'smooth',
    });
    return true;
  }, []);

  const openTour = useCallback(async (waitMs) => {
    if (!help) return;
    const steps = await resolveLiveSteps(help.steps, waitMs);
    if (!steps.length) return;
    startTour(steps);
  }, [help, startTour]);

  useEffect(() => {
    if (!help) {
      autoTriedRef.current = '';
      if (openRef.current) {
        setOpen(false);
        setLiveSteps([]);
        emitGlobalHelperSession(false);
      }
      return undefined;
    }
    if (!ledger.ready || !ledger.ok) return undefined;
    if (sessionDismissed.has(help.id) || isHelpDismissed(help, ledger.dismissed)) return undefined;
    if (autoTriedRef.current === help.id) return undefined;
    autoTriedRef.current = help.id;
    let cancelled = false;
    resolveLiveSteps(help.steps, 1500).then((steps) => {
      if (cancelled || !steps.length) return;
      startTour(steps);
    });
    return () => {
      cancelled = true;
    };
  }, [help, ledger, sessionDismissed, startTour]);

  const targetId = step?.target || '';

  useEffect(() => {
    if (!open || !targetId) {
      setHole(null);
      setHoleReady(false);
      return undefined;
    }
    setHoleReady(false);
    const update = () => {
      const el = queryHelpTarget(targetId);
      setHole(el ? measureHole(el) : null);
      setHoleReady(true);
    };
    update();
    const el = queryHelpTarget(targetId);
    el?.scrollIntoView({
      block: 'nearest',
      inline: 'nearest',
      behavior: prefersReducedMotion() ? 'auto' : 'smooth',
    });
    window.addEventListener('resize', update);
    window.addEventListener('scroll', update, true);
    return () => {
      window.removeEventListener('resize', update);
      window.removeEventListener('scroll', update, true);
    };
  }, [open, targetId, stepIndex]);

  useEffect(() => {
    if (!open) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => {
      if (event.key === 'Escape') closeOverlay('skip');
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [closeOverlay, open]);

  useEffect(() => {
    if (!open || !holeReady || hole || !liveSteps.length) return;
    const next = liveSteps.findIndex((item, index) => (
      index > stepIndex && queryHelpTarget(item.target)
    ));
    if (next >= 0) {
      setStepIndex(next);
      setPageIndex(0);
      return;
    }
    setOpen(false);
    setLiveSteps([]);
    emitGlobalHelperSession(false);
  }, [hole, holeReady, liveSteps, open, stepIndex]);

  useLayoutEffect(() => {
    if (!open || !cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      setCardSize({ width: rect.width, height: rect.height });
    }
  }, [open, stepIndex, pageIndex, hole, page]);

  const cardPos = useMemo(
    () => placeCard(hole, cardSize, {
      width: typeof window === 'undefined' ? 1280 : window.innerWidth,
      height: typeof window === 'undefined' ? 800 : window.innerHeight,
    }),
    [cardSize, hole],
  );

  const goPrev = useCallback(() => {
    if (pageIndex > 0) {
      setPageIndex((value) => value - 1);
      return;
    }
    if (stepIndex <= 0) return;
    const prevPages = liveSteps[stepIndex - 1]?.pages || [];
    setStepIndex((value) => value - 1);
    setPageIndex(Math.max(0, prevPages.length - 1));
  }, [liveSteps, pageIndex, stepIndex]);

  const goNext = useCallback(() => {
    if (!isLast) {
      if (pageIndex < pages.length - 1) {
        setPageIndex((value) => value + 1);
        return;
      }
      setStepIndex((value) => value + 1);
      setPageIndex(0);
      return;
    }
    closeOverlay('ack');
  }, [closeOverlay, isLast, pageIndex, pages.length]);

  if (!help) return null;

  return (
    <>
      <GlobalHelperButton onClick={() => openTour(400)} />
      {open && page ? (
        <GlobalHelperOverlay
          hole={hole}
          cardRef={cardRef}
          cardStyle={{ left: `${cardPos.left}px`, top: `${cardPos.top}px` }}
          title={page.title || ''}
          body={page.body || ''}
          image={page.image || ''}
          stepLabel={totalTicks > 1 ? `${currentTick} / ${totalTicks}` : ''}
          isFirst={isFirst}
          isLast={isLast}
          onPrev={goPrev}
          onNext={goNext}
          onSkip={() => closeOverlay('skip')}
        />
      ) : null}
    </>
  );
}

export default GlobalHelperHost;
