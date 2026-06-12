import React, { useCallback, useMemo } from 'react';
import {
  Box,
  Button,
  Chip,
  ListSubheader,
  MenuItem,
  Select,
  Stack,
  Typography,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { getStrategyDesignPath } from '../../../api/apis/strategyApi';
import InlineLoadingState from 'components/inlineLoadingState/inlineLoadingState';
import StrategyDescriptionText from 'components/strategyDescriptionText/strategyDescriptionText';
import StrategyDesignSimulateButton from './strategyDesignSimulateButton';
import { STRATEGY_DESIGN_STEP_INTRO, STRATEGY_DESIGN_STEPS } from '../constants/strategyDesignSteps';
import { DESIGN_RESTORE_MORE_MENU_VALUE } from '../constants/strategyDesignMetaConstants';
import { useStrategyDesignWorkbenchContext } from '../strategyDesignWorkbenchContext';
import './strategyDesignMetaBar.scss';

function StrategyDesignMetaBar() {
  const navigate = useNavigate();
  const wb = useStrategyDesignWorkbenchContext();

  const stepIntro = useMemo(() => {
    const intro = STRATEGY_DESIGN_STEP_INTRO[wb.activeStep];
    if (!intro) return { title: '制定策略', summary: '' };
    return intro;
  }, [wb.activeStep]);

  const nextStep = useMemo(() => {
    const idx = STRATEGY_DESIGN_STEPS.findIndex((step) => step.key === wb.activeStep);
    if (idx < 0 || idx >= STRATEGY_DESIGN_STEPS.length - 1) return null;
    return STRATEGY_DESIGN_STEPS[idx + 1];
  }, [wb.activeStep]);

  const currentStepDone = wb.stepStatus?.[wb.activeStep] === 'done';

  const handleGoNextStep = useCallback(() => {
    if (!nextStep || !wb.strategyName || !currentStepDone) return;
    navigate(getStrategyDesignPath(wb.strategyName, nextStep.key));
  }, [currentStepDone, navigate, nextStep, wb.strategyName]);

  if (wb.isLoadingSettings) {
    return (
      <Box className="ntq-design-meta">
        <InlineLoadingState compact row message="正在加载策略与工作台快照…" />
      </Box>
    );
  }

  return (
    <Box className="ntq-design-meta">
      <Box className="ntq-design-meta__page-title">
        <Typography component="h2" className="ntq-design-meta__page-heading">
          <Box component="span" className="ntq-design-meta__page-heading-label">
            {stepIntro.title}
          </Box>
          {stepIntro.summary ? (
            <>
              <Box component="span" className="ntq-design-meta__page-heading-sep">：</Box>
              <Box component="span" className="ntq-design-meta__page-heading-summary">
                {stepIntro.summary}
              </Box>
            </>
          ) : null}
        </Typography>
      </Box>

      <Box className="ntq-design-meta__body">
        <Box className="ntq-design-meta__main">
        <Typography variant="h6" fontWeight={700} className="ntq-design-meta__strategy-name">
          {wb.strategyDisplayName || wb.strategyName}
        </Typography>

        <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap" className="ntq-design-meta__tags">
          <Chip
            size="small"
            color={wb.isEnabled ? 'success' : 'default'}
            label={wb.isEnabled ? '已启用' : '已禁用'}
          />
          <Chip
            size="small"
            variant="outlined"
            label={wb.marketProfileLabel}
            className="ntq-design-meta__chip"
          />
          {wb.hasPersistedSnapshot ? (
            <Chip
              size="small"
              variant="outlined"
              label={`版本 ${wb.currentVersionDisplay}`}
            />
          ) : null}
          {wb.hasPersistedSnapshot ? (
            wb.isAppliedSettings ? (
              <Chip size="small" color="success" label="无设置变化" />
            ) : (
              <Chip
                size="small"
                color="warning"
                label="设置已变更"
                className="ntq-design-meta__change-chip"
              />
            )
          ) : null}
        </Stack>

        <StrategyDescriptionText
          text={wb.strategyDescription}
          variant="body2"
          color="text.secondary"
          empty="暂无策略描述"
          maxLines={3}
          className="ntq-design-meta__description"
        />

        <Stack direction="row" spacing={0} alignItems="center" flexWrap="wrap" className="ntq-design-meta__admin">
          <Button
            variant="outlined"
            size="small"
            disabled={wb.disableMetaActions}
            onClick={() => {
              wb.setSaveError('');
              wb.setUserspaceApplyOk('');
              wb.setDeployConfirmOpen(true);
            }}
            className="ntq-design-meta__publish-btn"
          >
            应用当前工作台版本到策略
          </Button>
          {wb.hasOtherVersions ? (
            <>
              <Typography component="span" className="ntq-design-meta__admin-sep" aria-hidden>
                |
              </Typography>
              <Select
                size="small"
                displayEmpty
                value=""
                renderValue={() => '恢复到版本…'}
                onChange={wb.handleRestoreMenuChange}
                disabled={wb.disableMetaActions}
                sx={{ minWidth: 148 }}
                className="ntq-compact-dropdown ntq-design-meta__restore-select"
              >
                <ListSubheader disableSticky>恢复到版本…</ListSubheader>
                {wb.restoreDropdownVersions.map((version) => (
                  <MenuItem key={version.id} value={version.id}>{version.id}</MenuItem>
                ))}
                <MenuItem value={DESIGN_RESTORE_MORE_MENU_VALUE}>更多版本…</MenuItem>
              </Select>
            </>
          ) : null}
        </Stack>

        {wb.settingsError ? (
          <Typography variant="caption" color="error">{wb.settingsError}</Typography>
        ) : null}
        {wb.saveError ? (
          <Typography variant="caption" color="error">{wb.saveError}</Typography>
        ) : null}
        {wb.userspaceApplyOk ? (
          <Typography variant="caption" color="success.main">{wb.userspaceApplyOk}</Typography>
        ) : null}
        </Box>

        <Box className="ntq-design-meta__run-wrap">
          <StrategyDesignSimulateButton
            done={currentStepDone}
            disabled={wb.disableMetaActions || wb.executionBusy}
            onClick={wb.handleRunCurrentStep}
          />
          {nextStep ? (
            <Button
              type="button"
              variant="outlined"
              size="medium"
              className="ntq-design-meta__next-btn"
              disabled={!currentStepDone}
              onClick={handleGoNextStep}
            >
              下一步
            </Button>
          ) : null}
        </Box>
      </Box>
    </Box>
  );
}

export default StrategyDesignMetaBar;
