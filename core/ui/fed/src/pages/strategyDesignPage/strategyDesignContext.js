import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { STRATEGY_DESIGN_DEFAULT_STEP } from './constants/strategyDesignSteps';
import {
  createEmptyStrategyDesignSession,
  readCachedStrategyDesignStep,
  writeCachedStrategyDesignStep,
} from './strategyDesignSessionState';

const StrategyDesignContext = createContext(null);

const VALID_STEPS = new Set(['enum', 'price', 'capital']);

export function StrategyDesignProvider({ strategyName, initialStep = '', children }) {
  const [session, setSession] = useState(() => {
    const step = String(initialStep || '').trim()
      || readCachedStrategyDesignStep(strategyName)
      || STRATEGY_DESIGN_DEFAULT_STEP;
    return createEmptyStrategyDesignSession(strategyName, step);
  });

  useEffect(() => {
    const step = readCachedStrategyDesignStep(strategyName) || STRATEGY_DESIGN_DEFAULT_STEP;
    setSession(createEmptyStrategyDesignSession(strategyName, step));
  }, [strategyName]);

  useEffect(() => {
    const step = String(initialStep || '').trim();
    if (!VALID_STEPS.has(step)) return;
    writeCachedStrategyDesignStep(strategyName, step);
    setSession((prev) => {
      if (prev.strategyName !== strategyName) return prev;
      if (prev.activeStep === step) return prev;
      return {
        ...prev,
        activeStep: step,
        lastUpdatedAt: Date.now(),
      };
    });
  }, [strategyName, initialStep]);

  const setActiveStep = useCallback((step) => {
    const next = String(step || '').trim();
    if (!VALID_STEPS.has(next)) return;
    writeCachedStrategyDesignStep(strategyName, next);
    setSession((prev) => ({
      ...prev,
      activeStep: next,
      lastUpdatedAt: Date.now(),
    }));
  }, [strategyName]);

  const patchSession = useCallback((patch) => {
    if (!patch || typeof patch !== 'object') return;
    setSession((prev) => ({
      ...prev,
      ...patch,
      lastUpdatedAt: Date.now(),
    }));
  }, []);

  const resetSessionForDraftChange = useCallback(() => {
    setSession((prev) => ({
      ...createEmptyStrategyDesignSession(strategyName, prev.activeStep),
      draftSettings: prev.draftSettings,
      appliedSettings: prev.appliedSettings,
      panelsResetEpoch: prev.panelsResetEpoch + 1,
    }));
  }, [strategyName]);

  const value = useMemo(() => ({
    strategyName,
    session,
    setSession,
    patchSession,
    setActiveStep,
    resetSessionForDraftChange,
  }), [
    strategyName,
    session,
    patchSession,
    setActiveStep,
    resetSessionForDraftChange,
  ]);

  return (
    <StrategyDesignContext.Provider value={value}>
      {children}
    </StrategyDesignContext.Provider>
  );
}

export function useStrategyDesignSession() {
  const ctx = useContext(StrategyDesignContext);
  if (!ctx) {
    throw new Error('useStrategyDesignSession must be used within StrategyDesignProvider');
  }
  return ctx;
}
