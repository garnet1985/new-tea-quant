import React, { useEffect, useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Accordion } from 'ui';
import {
  fetchStrategyList,
  getStrategyDesignPath,
  getStrategyDisplayLabel,
} from '../../../api/strategyApi';
import { getStrategyListPath, listPeerStrategies } from 'containers/strategyCategory';
import { buildStrategyDesignNavState } from '../strategyDesignSessionState';
import { useStrategyDesignWorkbenchContext } from '../strategyDesignWorkbenchContext';
import {
  STRATEGY_DESIGN_SETTINGS_PEERS_TITLE,
  STRATEGY_DESIGN_SETTINGS_PEERS_TOOLTIP,
} from '../constants/strategyDesignSettingsLayout';
import './style.scss';

function StrategyDesignPeerStrategies() {
  const wb = useStrategyDesignWorkbenchContext();
  const [rows, setRows] = useState([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchStrategyList()
      .then((res) => {
        if (!cancelled) setRows(res.data || []);
      })
      .catch(() => {
        if (!cancelled) setRows([]);
      })
      .finally(() => {
        if (!cancelled) setReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const listed = useMemo(
    () => listPeerStrategies(rows, {
      name: wb.strategyName,
      key: wb.strategyKey,
    }),
    [rows, wb.strategyName, wb.strategyKey],
  );

  if (!ready || listed.peers.length === 0) return null;

  const moreTo = getStrategyListPath('/strategy-design', {
    categoryQuery: listed.queryValue,
  });

  return (
    <Accordion
      className="ntq-design-peer-strategies"
      title={STRATEGY_DESIGN_SETTINGS_PEERS_TITLE}
      tooltip={STRATEGY_DESIGN_SETTINGS_PEERS_TOOLTIP}
      shine
      defaultExpanded={false}
    >
      <div className="ntq-design-peer-strategies__list">
        {listed.peers.map((row) => {
          const label = getStrategyDisplayLabel(row);
          return (
            <RouterLink
              key={row.id || row.name}
              to={getStrategyDesignPath(row.name, wb.activeStep)}
              state={buildStrategyDesignNavState(row)}
              className="ntq-link ntq-design-peer-strategies__item"
              title={label}
            >
              <span className="ntq-design-peer-strategies__name">{label}</span>
              {row.is_enabled ? null : (
                <span className="ntq-muted ntq-design-peer-strategies__badge">未启用</span>
              )}
            </RouterLink>
          );
        })}
        {listed.hasMore ? (
          <RouterLink
            to={moreTo}
            className="ntq-link ntq-design-peer-strategies__more"
          >
            更多{listed.categoryLabel ? ` · ${listed.categoryLabel}` : ''}
          </RouterLink>
        ) : null}
      </div>
    </Accordion>
  );
}

export default StrategyDesignPeerStrategies;
