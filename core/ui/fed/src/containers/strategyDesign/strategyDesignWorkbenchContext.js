import React, { createContext, useContext } from 'react';
import { useStrategyDesignWorkbench } from './hooks/useStrategyDesignWorkbench';

const StrategyDesignWorkbenchContext = createContext(null);

export function StrategyDesignWorkbenchProvider({ children }) {
  const value = useStrategyDesignWorkbench();
  return (
    <StrategyDesignWorkbenchContext.Provider value={value}>
      {children}
    </StrategyDesignWorkbenchContext.Provider>
  );
}

export function useStrategyDesignWorkbenchContext() {
  const ctx = useContext(StrategyDesignWorkbenchContext);
  if (!ctx) {
    throw new Error('useStrategyDesignWorkbenchContext must be used within StrategyDesignWorkbenchProvider');
  }
  return ctx;
}
