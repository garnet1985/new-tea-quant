import React, { useMemo } from 'react';
import {
  Box,
  Button,
  ListSubheader,
  MenuItem,
  Select,
  Stack,
  Typography,
} from '@mui/material';
import InlineLoadingState from 'components/inlineLoadingState/inlineLoadingState';
import NtqIcon from 'components/ntqIcon/ntqIcon';
import StrategyDescriptionText from 'components/strategyDescriptionText/strategyDescriptionText';
import { STRATEGY_DESIGN_STEP_INTRO } from '../constants/strategyDesignSteps';
import { DESIGN_RESTORE_MORE_MENU_VALUE } from '../constants/strategyDesignMetaConstants';
import { useStrategyDesignWorkbenchContext } from '../strategyDesignWorkbenchContext';
import StrategyDesignStepper from './strategyDesignStepper';
import './strategyDesignMetaBar.scss';

function StrategyDesignMetaBar() {
  const wb = useStrategyDesignWorkbenchContext();

  const stepIntro = useMemo(() => {
    const intro = STRATEGY_DESIGN_STEP_INTRO[wb.activeStep];
    if (!intro) return { title: '制定策略', summary: '' };
    return intro;
  }, [wb.activeStep]);

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
        <Box className="ntq-design-meta__page-title-stepper">
          <StrategyDesignStepper />
        </Box>
      </Box>

      <Box className="ntq-design-meta__body">
        <Box className="ntq-design-meta__info">
          <Box className="ntq-design-meta__title-row">
            <Typography variant="h6" fontWeight={700} className="ntq-design-meta__strategy-name">
              {wb.strategyDisplayName || wb.strategyName}
            </Typography>
            {wb.hasPersistedSnapshot ? (
              <Box
                className={[
                  'ntq-design-meta__version-capsule',
                  wb.isAppliedSettings
                    ? 'ntq-design-meta__version-capsule--clean'
                    : 'ntq-design-meta__version-capsule--changed',
                ].join(' ')}
              >
                <Box component="span" className="ntq-design-meta__version-capsule-part ntq-design-meta__version-capsule-part--version">
                  {wb.currentVersionDisplay}
                </Box>
                <Box component="span" className="ntq-design-meta__version-capsule-sep" aria-hidden />
                <Box component="span" className="ntq-design-meta__version-capsule-part ntq-design-meta__version-capsule-part--status">
                  {wb.isAppliedSettings ? '无设置变化' : '设置已变更'}
                </Box>
              </Box>
            ) : null}
          </Box>

          <Stack direction="row" spacing={0} alignItems="center" flexWrap="nowrap" className="ntq-design-meta__admin">
            <Button
              variant="outlined"
              size="small"
              disabled={wb.disableMetaActions}
              onClick={() => {
                wb.setSaveError('');
                wb.setUserspaceApplyOk('');
                wb.setDeployConfirmOpen(true);
              }}
              className="ntq-design-meta__admin-action ntq-design-meta__publish-btn"
              title="将当前工作台版本发布到策略 settings.py"
            >
              发布策略
            </Button>
            {wb.hasPersistedSnapshot ? (
              <>
                <Typography component="span" className="ntq-design-meta__admin-sep" aria-hidden>
                  |
                </Typography>
                <Select
                  size="small"
                  displayEmpty
                  value=""
                  renderValue={() => '恢复到历史版本'}
                  onChange={wb.handleRestoreMenuChange}
                  disabled={wb.disableMetaActions || !wb.hasOtherVersions}
                  className="ntq-compact-dropdown ntq-design-meta__admin-action ntq-design-meta__version-select"
                >
                  <ListSubheader disableSticky>恢复到历史版本</ListSubheader>
                  {wb.restoreDropdownVersions.map((version) => (
                    <MenuItem key={version.id} value={version.id}>{version.id}</MenuItem>
                  ))}
                  <MenuItem value={DESIGN_RESTORE_MORE_MENU_VALUE}>更多版本…</MenuItem>
                </Select>
              </>
            ) : null}
            {wb.strategyName ? (
              <>
                <Typography component="span" className="ntq-design-meta__admin-sep" aria-hidden>
                  |
                </Typography>
                <Button
                  variant="outlined"
                  size="small"
                  disabled={wb.packageExporting}
                  onClick={wb.handleExportStrategyPackage}
                  className="ntq-design-meta__admin-action ntq-design-meta__export-btn"
                  startIcon={<NtqIcon name="download" size={16} tone="muted" />}
                >
                  {wb.packageExporting ? '导出中…' : '导出策略'}
                </Button>
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
          {wb.packageExportError ? (
            <Typography variant="caption" color="error">{wb.packageExportError}</Typography>
          ) : null}
        </Box>

        <Box className="ntq-design-meta__description-col">
          <StrategyDescriptionText
            text={wb.strategyDescription}
            variant="body2"
            color="text.secondary"
            empty="暂无策略描述"
            maxLines={6}
            className="ntq-design-meta__description"
          />
        </Box>
      </Box>
    </Box>
  );
}

export default StrategyDesignMetaBar;
