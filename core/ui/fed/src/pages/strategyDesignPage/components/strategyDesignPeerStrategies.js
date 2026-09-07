import React, { useEffect, useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Link,
  Stack,
  Typography,
} from '@mui/material';
import NtqIcon from 'components/ntqIcon/ntqIcon';
import SettingsAccordionTitle from 'components/settingsAccordionTitle/settingsAccordionTitle';
import {
  fetchStrategyList,
  getStrategyDesignPath,
  getStrategyDisplayLabel,
  getStrategyListPath,
  listPeerStrategies,
} from '../../../api/strategyApi';
import { buildStrategyDesignNavState } from '../strategyDesignSessionState';
import { useStrategyDesignWorkbenchContext } from '../strategyDesignWorkbenchContext';
import {
  STRATEGY_DESIGN_SETTINGS_PEERS_TITLE,
  STRATEGY_DESIGN_SETTINGS_PEERS_TOOLTIP,
} from '../constants/strategyDesignSettingsLayout';
import './strategyDesignPeerStrategies.scss';

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
      defaultExpanded={false}
      disableGutters
      TransitionProps={{ timeout: 0, unmountOnExit: false }}
    >
      <AccordionSummary expandIcon={<NtqIcon name="expandMore" size={24} />}>
        <SettingsAccordionTitle
          title={STRATEGY_DESIGN_SETTINGS_PEERS_TITLE}
          tooltip={STRATEGY_DESIGN_SETTINGS_PEERS_TOOLTIP}
          context={{ defaultTooltipShine: true }}
        />
      </AccordionSummary>
      <AccordionDetails>
        <Stack spacing={0.5} className="ntq-design-peer-strategies__list">
          {listed.peers.map((row) => {
            const label = getStrategyDisplayLabel(row);
            return (
              <Link
                key={row.id || row.name}
                component={RouterLink}
                to={getStrategyDesignPath(row.name, wb.activeStep)}
                state={buildStrategyDesignNavState(row)}
                underline="hover"
                className="ntq-design-peer-strategies__item"
                title={label}
              >
                <Typography component="span" className="ntq-design-peer-strategies__name">
                  {label}
                </Typography>
                {row.is_enabled ? null : (
                  <Typography
                    component="span"
                    variant="caption"
                    color="text.secondary"
                    className="ntq-design-peer-strategies__badge"
                  >
                    未启用
                  </Typography>
                )}
              </Link>
            );
          })}
          {listed.hasMore ? (
            <Link
              component={RouterLink}
              to={moreTo}
              underline="hover"
              className="ntq-design-peer-strategies__more"
            >
              更多{listed.categoryLabel ? ` · ${listed.categoryLabel}` : ''}
            </Link>
          ) : null}
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
}

export default StrategyDesignPeerStrategies;
