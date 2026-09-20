import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { dismissUiHelper, fetchUiHelper } from 'api/uiHelperApi';
import {
  findHelpsForPath,
  helpTrigger,
  isHelpDismissed,
  pickHelpForManualOpen,
} from './catalog';
import {
  emitGlobalHelperSession,
  liveStepsNow,
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
  const matchingHelps = useMemo(
    () => findHelpsForPath(location.pathname),
    [location.pathname],
  );
  const [ledger, setLedger] = useState({ ready: false, ok: false, dismissed: {} });
  const [sessionDismissed, setSessionDismissed] = useState(() => new Set());
  const [activeHelp, setActiveHelp] = useState(null);
  const [open, setOpen] = useState(false);
  const [liveSteps, setLiveSteps] = useState([]);
  const [stepIndex, setStepIndex] = useState(0);
  const [pageIndex, setPageIndex] = useState(0);
  const [hole, setHole] = useState(null);
  const [holeReady, setHoleReady] = useState(false);
  const [cardSize, setCardSize] = useState(CARD_FALLBACK);
  const cardRef = useRef(null);
  const autoTriedRef = useRef(new Set());
  const openRef = useRef(false);
  const activeHelpRef = useRef(null);
  const [enterSettled, setEnterSettled] = useState(false);

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
  const buttonHelp = pickHelpForManualOpen(matchingHelps);

  const isDismissed = useCallback((help) => (
    Boolean(help) && (
      sessionDismissed.has(help.id)
      || (ledger.ok && isHelpDismissed(help, ledger.dismissed))
    )
  ), [ledger.dismissed, ledger.ok, sessionDismissed]);

  useEffect(() => {
    openRef.current = open;
  }, [open]);

  useEffect(() => {
    activeHelpRef.current = activeHelp;
  }, [activeHelp]);

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
    const current = activeHelpRef.current;
    setOpen(false);
    setActiveHelp(null);
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
  }, []);

  const startTour = useCallback((help, steps) => {
    if (!help || !steps.length || openRef.current) return false;
    autoTriedRef.current.add(help.id);
    setActiveHelp(help);
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

  const openTour = useCallback(async (help, waitMs) => {
    if (!help) return;
    const steps = await resolveLiveSteps(help.steps, waitMs);
    if (!steps.length) return;
    startTour(help, steps);
  }, [startTour]);

  useEffect(() => {
    autoTriedRef.current = new Set();
    setEnterSettled(!matchingHelps.some((help) => helpTrigger(help) === 'enter'));
    if (openRef.current) {
      setOpen(false);
      setActiveHelp(null);
      setLiveSteps([]);
      emitGlobalHelperSession(false);
    }
  }, [matchingHelps]);

  useEffect(() => {
    if (!ledger.ready || !ledger.ok) return undefined;
    const pending = matchingHelps.filter((help) => (
      helpTrigger(help) === 'enter'
      && !isDismissed(help)
      && !autoTriedRef.current.has(help.id)
    ));
    if (!pending.length) {
      setEnterSettled(true);
      return undefined;
    }
    let cancelled = false;
    Promise.all(pending.map((help) => {
      autoTriedRef.current.add(help.id);
      return resolveLiveSteps(help.steps, 1500).then((steps) => {
        if (cancelled || !steps.length) return;
        startTour(help, steps);
      });
    })).finally(() => {
      if (!cancelled) setEnterSettled(true);
    });
    return () => {
      cancelled = true;
    };
  }, [isDismissed, ledger, matchingHelps, startTour]);

  useEffect(() => {
    if (!ledger.ready || !ledger.ok || open || !enterSettled) return undefined;
    const pending = matchingHelps.filter((help) => (
      helpTrigger(help) === 'appear'
      && !isDismissed(help)
      && !autoTriedRef.current.has(help.id)
    ));
    if (!pending.length) return undefined;

    const tryFire = () => {
      if (openRef.current) return;
      pending.forEach((help) => {
        if (autoTriedRef.current.has(help.id) || isDismissed(help)) return;
        const steps = liveStepsNow(help.steps);
        if (!steps.length) return;
        startTour(help, steps);
      });
    };

    tryFire();
    let frame = 0;
    const kick = () => {
      if (frame) return;
      frame = window.requestAnimationFrame(() => {
        frame = 0;
        tryFire();
      });
    };
    const observer = new MutationObserver(kick);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => {
      observer.disconnect();
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, [enterSettled, isDismissed, ledger, matchingHelps, open, startTour]);

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
    setActiveHelp(null);
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

  if (!matchingHelps.length) return null;

  return (
    <>
      <GlobalHelperButton onClick={() => openTour(buttonHelp, 400)} />
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
