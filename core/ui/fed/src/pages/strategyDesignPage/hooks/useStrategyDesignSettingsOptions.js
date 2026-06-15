import { useEffect, useState } from 'react';
import {
  fetchCapitalAllocationModeConfig,
  fetchMarketProfileOptions,
  fetchSamplingStrategyConfig,
  fetchSimulationTemplateConfig,
  fetchSkipInvestmentWhenOptions,
} from '../../../api/apis/strategyApi';

/** 制定策略设置面板：下拉/模板等选项（与策略实验室同源）。 */
export function useStrategyDesignSettingsOptions() {
  const [allocationModeOptions, setAllocationModeOptions] = useState([]);
  const [samplingStrategyOptions, setSamplingStrategyOptions] = useState([]);
  const [simulationTemplateOptions, setSimulationTemplateOptions] = useState([]);
  const [simulationTemplateProfiles, setSimulationTemplateProfiles] = useState({});
  const [skipInvestmentWhenOptions, setSkipInvestmentWhenOptions] = useState([]);
  const [marketProfileOptions, setMarketProfileOptions] = useState([]);
  const [optionsError, setOptionsError] = useState('');

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetchCapitalAllocationModeConfig(),
      fetchSamplingStrategyConfig(),
      fetchSimulationTemplateConfig(),
      fetchSkipInvestmentWhenOptions(),
      fetchMarketProfileOptions(),
    ])
      .then(([allocationConfig, samplingConfig, simulationConfig, skipWhenOptions, marketProfiles]) => {
        if (cancelled) return;
        setAllocationModeOptions(allocationConfig?.options || []);
        setSamplingStrategyOptions(samplingConfig?.options || []);
        setSimulationTemplateOptions(simulationConfig?.options || []);
        setSimulationTemplateProfiles(simulationConfig?.profiles || {});
        setSkipInvestmentWhenOptions(skipWhenOptions || []);
        setMarketProfileOptions(Array.isArray(marketProfiles) ? marketProfiles : []);
        setOptionsError('');
      })
      .catch((err) => {
        if (cancelled) return;
        setOptionsError(err?.message || '读取设置选项失败');
        setAllocationModeOptions([]);
        setSamplingStrategyOptions([]);
        setSimulationTemplateOptions([]);
        setSimulationTemplateProfiles({});
        setSkipInvestmentWhenOptions([]);
        setMarketProfileOptions([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return {
    allocationModeOptions,
    samplingStrategyOptions,
    simulationTemplateOptions,
    simulationTemplateProfiles,
    skipInvestmentWhenOptions,
    marketProfileOptions,
    optionsError,
  };
}
